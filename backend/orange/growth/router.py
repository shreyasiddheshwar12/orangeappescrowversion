"""HTTP routes for the Growth Assistant, mounted under /api/growth."""
from __future__ import annotations

from typing import Awaitable, Callable, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import llm, orchestrator


class RunCreate(BaseModel):
    goal: str = Field(min_length=5, max_length=1000)
    budget: Optional[float] = Field(default=None, ge=0)
    campaignType: Optional[Literal["paid", "barter_product"]] = None
    language: Optional[str] = None


class Approve(BaseModel):
    creatorIds: List[str] = Field(min_length=1, max_length=6)
    budgetPerCreator: Optional[float] = Field(default=None, gt=0)
    deliverables: Optional[str] = None
    timeline: Optional[str] = None


def build_router(get_db: Callable, get_current_user: Callable, create_request: Callable[[dict, dict], Awaitable[dict]]) -> APIRouter:
    router = APIRouter(prefix="/growth")

    async def business(user=Depends(get_current_user)):
        if user.get("role") != "business":
            raise HTTPException(status_code=403, detail="The Growth Assistant is for businesses")
        brand = await get_db().brand_profiles.find_one({"userId": user["id"]}, {"_id": 0})
        if not brand:
            raise HTTPException(status_code=400, detail="Complete your business profile first")
        return user, brand

    async def own_run(run_id: str, user_id: str) -> dict:
        run = await get_db().agent_runs.find_one({"id": run_id, "brandUserId": user_id}, {"_id": 0})
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run

    async def with_steps(run: dict) -> dict:
        steps = await get_db().agent_steps.find({"runId": run["id"]}, {"_id": 0}).sort("order", 1).to_list(20)
        return {**run, "steps": steps}

    @router.get("/status")
    async def status(user=Depends(get_current_user)):
        return {"aiConfigured": llm.configured(), "engine": llm.model_name() if llm.configured() else "rules"}

    @router.post("/runs", status_code=201)
    async def create_run(body: RunCreate, ctx=Depends(business)):
        user, brand = ctx
        busy = await get_db().agent_runs.find_one({"brandUserId": user["id"], "status": {"$in": ["running", "launching"]}}, {"_id": 0, "id": 1})
        if busy:
            raise HTTPException(status_code=409, detail="The assistant is already working on a plan for you")
        run = await orchestrator.start_run(get_db(), user, brand, body.goal, body.budget, body.campaignType, body.language)
        return await with_steps(run)

    @router.get("/runs")
    async def list_runs(ctx=Depends(business)):
        user, _ = ctx
        runs = await get_db().agent_runs.find({"brandUserId": user["id"]}, {"_id": 0, "outputs": 0}).sort("createdAt", -1).to_list(20)
        return runs

    @router.get("/runs/{run_id}")
    async def get_run(run_id: str, ctx=Depends(business)):
        user, _ = ctx
        return await with_steps(await own_run(run_id, user["id"]))

    @router.post("/runs/{run_id}/approve")
    async def approve(run_id: str, body: Approve, ctx=Depends(business)):
        user, brand = ctx
        run = await own_run(run_id, user["id"])
        if run["status"] != "awaiting_approval":
            raise HTTPException(status_code=400, detail="This plan isn't waiting for approval")
        shortlist = {c["creatorId"] for c in run["outputs"].get("creator_matching", {}).get("creators", [])}
        if not set(body.creatorIds) <= shortlist:
            raise HTTPException(status_code=400, detail="Pick creators from the shortlist")
        edits = {"budgetPerCreator": body.budgetPerCreator, "deliverables": body.deliverables, "timeline": body.timeline}
        await orchestrator.approve(get_db(), run, user, brand, body.creatorIds, edits, create_request)
        return await with_steps(await own_run(run_id, user["id"]))

    @router.post("/runs/{run_id}/cancel")
    async def cancel(run_id: str, ctx=Depends(business)):
        user, _ = ctx
        run = await own_run(run_id, user["id"])
        if run["status"] not in ("awaiting_approval", "failed"):
            raise HTTPException(status_code=400, detail="Only a plan waiting for approval can be dismissed")
        await get_db().agent_runs.update_one({"id": run_id}, {"$set": {"status": "cancelled", "updatedAt": orchestrator.now()}})
        return await with_steps(await own_run(run_id, user["id"]))

    return router
