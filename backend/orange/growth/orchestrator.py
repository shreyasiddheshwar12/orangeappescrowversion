"""Runs the Growth Assistant: a fixed pipeline of capabilities with one approval gate.

Run statuses: running -> awaiting_approval -> launching -> completed, or failed / cancelled.
Every step is stored in `agent_steps` so the UI can show a live timeline.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from . import capabilities as caps
from . import llm

logger = logging.getLogger(__name__)

AGENTS = {
    "business_intelligence": ("Business Intelligence", "Reading your business profile"),
    "performance_analyst": ("Performance Analyst", "Looking at your past collaborations"),
    "marketing_planner": ("Marketing Planner", "Turning your goal into a plan"),
    "creator_matching": ("Creator Matching", "Ranking creators for this plan"),
    "campaign_assistant": ("Campaign Assistant", "Writing briefs and sending requests"),
}
PLAN_STEPS = ["business_intelligence", "performance_analyst", "marketing_planner", "creator_matching"]

_tasks: dict[str, asyncio.Task] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _spawn(run_id: str, coro: Awaitable) -> None:
    task = asyncio.ensure_future(coro)
    _tasks[run_id] = task
    task.add_done_callback(lambda t: _tasks.pop(run_id, None) if _tasks.get(run_id) is t else None)


async def wait_for(run_id: str) -> None:
    """Test helper: wait for a run's background work."""
    task = _tasks.get(run_id)
    if task:
        await task


async def _new_step(db, run_id: str, order: int, agent: str) -> dict:
    name, title = AGENTS[agent]
    step = {"id": str(uuid.uuid4()), "runId": run_id, "order": order, "agent": agent, "agentName": name, "title": title, "status": "pending", "engine": None, "summary": None, "error": None, "startedAt": None, "finishedAt": None}
    await db.agent_steps.insert_one(step)
    step.pop("_id", None)
    return step


async def _set_step(db, step_id: str, **fields) -> None:
    await db.agent_steps.update_one({"id": step_id}, {"$set": fields})


async def _set_run(db, run_id: str, **fields) -> None:
    fields["updatedAt"] = now()
    await db.agent_runs.update_one({"id": run_id}, {"$set": fields})


def _summary(agent: str, out: dict) -> str:
    if agent == "business_intelligence":
        return out.get("summary") or "Profile read."
    if agent == "performance_analyst":
        return (out.get("insights") or ["No history yet."])[0]
    if agent == "marketing_planner":
        money = f"₹{out['budgetPerCreator']:,.0f} each" if out.get("campaignType") == "paid" else f"barter worth ₹{out['budgetPerCreator']:,.0f} each"
        return f"{out['creatorCount']} creators, {money}, {out.get('deliverables')}."
    if agent == "creator_matching":
        cs = out.get("creators") or []
        if not cs:
            return "No creators match this plan yet. Try another niche or a larger budget."
        return f"Ranked {len(cs)} creators. Best fit: {cs[0]['name']} ({cs[0]['score']}% match)."
    if agent == "campaign_assistant":
        sent = len(out.get("sent") or [])
        failed = len(out.get("failed") or [])
        return f"Sent {sent} request{'s' if sent != 1 else ''}." + (f" {failed} could not be sent." if failed else "")
    return ""


async def start_run(db, user: dict, brand: dict, goal: str, budget: Optional[float], campaign_type: Optional[str], language: Optional[str]) -> dict:
    run = {
        "id": str(uuid.uuid4()), "brandUserId": user["id"], "brandProfileId": brand["id"], "goal": goal.strip(),
        "inputs": {"budget": budget, "campaignType": campaign_type, "language": language},
        "status": "running", "aiEngine": llm.model_name() if llm.configured() else "rules",
        "outputs": {}, "approval": None, "growthCampaignId": None, "error": None, "createdAt": now(), "updatedAt": now(),
    }
    await db.agent_runs.insert_one(run)
    run.pop("_id", None)
    steps = [await _new_step(db, run["id"], i, a) for i, a in enumerate(PLAN_STEPS)]
    _spawn(run["id"], _execute_plan(db, run, brand, steps))
    return run


async def _run_step(db, run_id: str, step: dict, fn: Callable[[], Awaitable[dict]]) -> dict:
    await _set_step(db, step["id"], status="running", startedAt=now())
    try:
        out = await fn()
    except Exception as exc:  # noqa: BLE001 - record any failure on the timeline
        logger.exception("Growth step %s failed", step["agent"])
        msg = str(exc) if isinstance(exc, llm.LLMError) else "Something went wrong in this step."
        await _set_step(db, step["id"], status="failed", error=msg, finishedAt=now())
        raise
    await _set_step(db, step["id"], status="done", engine=out.get("engine"), summary=_summary(step["agent"], out), finishedAt=now())
    await db.agent_runs.update_one({"id": run_id}, {"$set": {f"outputs.{step['agent']}": out, "updatedAt": now()}})
    return out


async def _execute_plan(db, run: dict, brand: dict, steps: list[dict]) -> None:
    rid = run["id"]
    inputs = run["inputs"]
    try:
        niches = sorted({n for n in await db.creator_profiles.distinct("niche") if n})
        business = await _run_step(db, rid, steps[0], lambda: caps.business_intelligence(brand, niches))
        performance = await _run_step(db, rid, steps[1], lambda: caps.performance_analyst(db, run["brandUserId"]))
        budget = inputs.get("budget") or brand.get("monthlyBudget")
        plan = await _run_step(db, rid, steps[2], lambda: caps.marketing_planner(run["goal"], brand, business, performance, budget, inputs.get("campaignType"), niches))
        await _run_step(db, rid, steps[3], lambda: caps.creator_matching(db, plan, brand, inputs.get("language")))
        await _set_run(db, rid, status="awaiting_approval")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc) if isinstance(exc, llm.LLMError) else "The assistant stopped because a step failed."
        await db.agent_steps.update_many({"runId": rid, "status": "pending"}, {"$set": {"status": "skipped"}})
        await _set_run(db, rid, status="failed", error=msg)


async def approve(db, run: dict, user: dict, brand: dict, creator_ids: list[str], edits: dict, create_request: Callable[[dict, dict], Awaitable[dict]]) -> dict:
    plan = {**run["outputs"]["marketing_planner"], **{k: v for k, v in edits.items() if v not in (None, "")}}
    shortlist = {c["creatorId"]: c for c in run["outputs"]["creator_matching"]["creators"]}
    chosen = [shortlist[i] for i in creator_ids if i in shortlist]
    approval = {"creatorIds": [c["creatorId"] for c in chosen], "plan": plan, "approvedAt": now()}
    await _set_run(db, run["id"], status="launching", approval=approval)
    step = await _new_step(db, run["id"], len(PLAN_STEPS), "campaign_assistant")
    _spawn(run["id"], _execute_launch(db, run, user, brand, plan, chosen, step, create_request))
    return approval


async def _execute_launch(db, run, user, brand, plan, chosen, step, create_request) -> None:
    rid = run["id"]
    growth_id = str(uuid.uuid4())

    async def launch() -> dict:
        drafted = await caps.campaign_assistant(plan, brand, chosen)
        sent, failed = [], []
        for c in chosen:
            payload = {
                "receiverId": c["creatorId"], "receiverType": "creator", "campaignType": plan["campaignType"],
                "deliverables": plan.get("deliverables") or "", "timeline": plan.get("timeline") or "", "brief": drafted["briefs"][c["creatorId"]],
                "budget": plan["budgetPerCreator"] if plan["campaignType"] == "paid" else 0,
                "productValue": plan["budgetPerCreator"] if plan["campaignType"] != "paid" else 0,
            }
            try:
                created = await create_request(payload, user)
            except Exception as exc:  # noqa: BLE001 - one creator failing shouldn't stop the rest
                failed.append({"creatorId": c["creatorId"], "name": c["name"], "reason": getattr(exc, "detail", None) or "Could not send"})
                continue
            await db.campaigns.update_one({"id": created["id"]}, {"$set": {"growthCampaignId": growth_id}})
            sent.append({"creatorId": c["creatorId"], "name": c["name"], "campaignId": created["id"]})
        await db.growth_campaigns.insert_one({
            "id": growth_id, "brandUserId": run["brandUserId"], "runId": rid, "name": plan.get("campaignName"), "objective": plan.get("objective"),
            "plan": plan, "campaignIds": [s["campaignId"] for s in sent], "createdAt": now(),
        })
        return {"engine": drafted["engine"], "briefs": drafted["briefs"], "sent": sent, "failed": failed}

    try:
        await _run_step(db, rid, step, launch)
        await _set_run(db, rid, status="completed", growthCampaignId=growth_id)
    except Exception as exc:  # noqa: BLE001
        await _set_run(db, rid, status="failed", error=str(exc) if isinstance(exc, llm.LLMError) else "Requests could not be sent.")
