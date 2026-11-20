"""The five Growth Assistant capabilities.

Each one works on real Orange data. Where Claude is available it writes the
language parts; without it, a rules engine restates only what the business has
told us. Every result records which engine produced it.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from . import llm
from .matching import rank_creators

SYSTEM = (
    "You are part of Orange, a platform that helps small local businesses in India run "
    "influencer campaigns with local creators. Work only from the facts you are given. "
    "Never invent numbers, customers, results or creator details. If something is unknown, "
    "say so plainly. Write in short, plain sentences a busy shop owner can act on. "
    "Amounts are Indian rupees."
)


def _facts(brand: dict) -> str:
    rows = [
        ("Business name", brand.get("brandName")),
        ("Industry", brand.get("industry")),
        ("Location", brand.get("location")),
        ("About", brand.get("bio")),
        ("Products or services", brand.get("products")),
        ("Target audience", brand.get("targetAudience")),
        ("Goals", ", ".join(brand.get("objectives") or [])),
        ("Monthly marketing budget", f"₹{brand['monthlyBudget']:,.0f}" if brand.get("monthlyBudget") else None),
        ("Brand personality", ", ".join(brand.get("brandVoice") or [])),
        ("Preferred creator niches", ", ".join(brand.get("preferredNiches") or [])),
        ("Open to barter", "yes" if brand.get("barterEnabled") else "no"),
    ]
    return "\n".join(f"- {k}: {v}" for k, v in rows if v)


# 1. Business Intelligence --------------------------------------------------

class BusinessRead(BaseModel):
    summary: str = Field(description="Two or three sentences on what the business is and who it serves.")
    audience: str = Field(description="Who the campaign should reach, from the facts given.")
    sellingPoints: List[str] = Field(description="Up to 4 things worth showing in creator content.")
    gaps: List[str] = Field(description="Missing information that would make the plan better.")
    suggestedNiches: List[str] = Field(description="Creator niches to target, chosen only from the allowed list.")


async def business_intelligence(brand: dict, niches_available: List[str]) -> dict:
    missing = [label for key, label in [("targetAudience", "target audience"), ("products", "products or services"), ("monthlyBudget", "monthly budget"), ("objectives", "goals"), ("location", "location")] if not brand.get(key)]
    allowed = {n.lower(): n for n in niches_available}
    if llm.configured():
        read = await llm.structured(
            SYSTEM,
            f"Read this business profile and summarise it for campaign planning.\n\n{_facts(brand)}\n\n"
            f"Allowed creator niches: {', '.join(niches_available) or 'none'}.\n"
            f"Fields the owner left empty: {', '.join(missing) or 'none'}.",
            BusinessRead,
            effort="low",
        )
        out = read.model_dump()
        out["suggestedNiches"] = [allowed[n.lower()] for n in out["suggestedNiches"] if n.lower() in allowed]
        return {"engine": "claude", **out}
    preferred = [allowed[n.lower()] for n in (brand.get("preferredNiches") or []) if n.lower() in allowed]
    if not preferred and (brand.get("industry") or "").lower() in allowed:
        preferred = [allowed[brand["industry"].lower()]]
    summary = f"{brand.get('brandName') or 'Your business'}"
    if brand.get("industry"):
        summary += f" is a {brand['industry'].lower()} business"
    if brand.get("location"):
        summary += f" in {brand['location']}"
    summary += "."
    if brand.get("products"):
        summary += f" It offers {brand['products']}."
    return {
        "engine": "rules",
        "summary": summary,
        "audience": brand.get("targetAudience") or "Not set yet.",
        "sellingPoints": [],
        "gaps": [f"Add your {m} in your profile." for m in missing],
        "suggestedNiches": preferred,
    }


# 2. Performance Analyst ----------------------------------------------------

class PerformanceRead(BaseModel):
    insights: List[str] = Field(description="Up to 3 observations drawn strictly from the numbers given.")
    nextMove: str = Field(description="One concrete suggestion for the next campaign.")


async def performance_analyst(db, brand_user_id: str) -> dict:
    party = {"$or": [{"senderUserId": brand_user_id}, {"receiverUserId": brand_user_id}]}
    campaigns = await db.campaigns.find(party, {"_id": 0}).to_list(500)
    completed = [c for c in campaigns if c.get("status") == "completed"]
    cancelled = [c for c in campaigns if c.get("status") == "cancelled"]
    active = [c for c in campaigns if c.get("status") not in ("completed", "cancelled", "disputed")]
    ids = [c["id"] for c in campaigns]
    funded = await db.ledger_entries.find({"campaignId": {"$in": ids}, "type": "funded"}, {"_id": 0, "amount": 1}).to_list(1000) if ids else []
    spent = round(sum(e["amount"] for e in funded), 2)
    given = await db.ratings.find({"raterId": brand_user_id}, {"_id": 0, "rating": 1, "campaignId": 1}).to_list(500)
    by_campaign = {r["campaignId"]: r["rating"] for r in given}
    past = []
    for c in completed:
        creator_name = c["receiverName"] if c.get("receiverType") == "creator" else c.get("senderName")
        creator_id = c["receiverId"] if c.get("receiverType") == "creator" else c.get("senderId")
        past.append({"campaignId": c["id"], "creatorId": creator_id, "creatorName": creator_name, "type": c.get("campaignType"), "budget": c.get("budget") or c.get("productValue") or 0, "yourRating": by_campaign.get(c["id"])})
    metrics = {"total": len(campaigns), "completed": len(completed), "active": len(active), "cancelled": len(cancelled), "spent": spent, "pastCreators": past}
    if not completed:
        return {"engine": "rules", "metrics": metrics, "insights": ["No completed collaborations yet, so there are no results to learn from."], "nextMove": "Start with two or three creators to build a baseline."}
    if llm.configured():
        lines = "\n".join(f"- {p['creatorName']}: {p['type']}, ₹{p['budget']:,.0f}, your rating {p['yourRating'] or 'not given'}" for p in past)
        read = await llm.structured(
            SYSTEM,
            f"Here is this business's collaboration history on Orange.\n"
            f"Total {metrics['total']}, completed {metrics['completed']}, active {metrics['active']}, cancelled {metrics['cancelled']}, "
            f"money funded ₹{spent:,.0f}.\nCompleted collaborations:\n{lines}\n\n"
            "We do not yet have sales or redemption data, so do not claim anything about revenue or footfall.",
            PerformanceRead,
            effort="low",
        )
        return {"engine": "claude", "metrics": metrics, **read.model_dump()}
    top = sorted([p for p in past if p["yourRating"]], key=lambda p: -p["yourRating"])
    insights = [f"{len(completed)} completed of {len(campaigns)} collaborations."]
    if top:
        insights.append(f"You rated {top[0]['creatorName']} highest ({top[0]['yourRating']}/5).")
    return {"engine": "rules", "metrics": metrics, "insights": insights, "nextMove": f"Consider rebooking {top[0]['creatorName']}." if top else "Rate past creators so Orange can recommend who to rebook."}


# 3. Marketing Planner ------------------------------------------------------

class Plan(BaseModel):
    campaignName: str
    objective: str = Field(description="One sentence: what this campaign should achieve.")
    approach: str = Field(description="Two or three sentences on how creators will achieve it.")
    campaignType: str = Field(description="Either 'paid' or 'barter_product'.")
    creatorCount: int = Field(description="Number of creators, 1 to 6.")
    budgetPerCreator: float = Field(description="Rupees per creator for paid campaigns, or product value for barter.")
    deliverables: str = Field(description="What each creator posts, e.g. '1 reel + 2 stories'.")
    timeline: str = Field(description="When content should go live.")
    contentIdeas: List[str] = Field(description="Up to 4 short content ideas.")
    kpis: List[str] = Field(description="Up to 3 things to measure. Prefer coupon redemptions and link visits.")
    niches: List[str] = Field(description="Creator niches to target, chosen only from the allowed list.")


def _clean_plan(p: dict, budget: Optional[float], niches_available: List[str], fallback_niches: List[str]) -> dict:
    allowed = {n.lower(): n for n in niches_available}
    p["campaignType"] = "barter_product" if p.get("campaignType") == "barter_product" else "paid"
    p["creatorCount"] = max(1, min(6, int(p.get("creatorCount") or 3)))
    p["niches"] = [allowed[n.lower()] for n in (p.get("niches") or []) if n.lower() in allowed] or fallback_niches
    per = float(p.get("budgetPerCreator") or 0)
    if budget:
        cap = round(budget * 0.9 / p["creatorCount"], -2) or round(budget * 0.9 / p["creatorCount"])
        per = min(per, cap) if per else cap
    p["budgetPerCreator"] = round(per)
    p["budgetTotal"] = budget
    p["reserve"] = round(budget - per * p["creatorCount"]) if budget else None
    return p


async def marketing_planner(goal: str, brand: dict, business: dict, performance: dict, budget: Optional[float], campaign_type: Optional[str], niches_available: List[str]) -> dict:
    fallback = business.get("suggestedNiches") or []
    if llm.configured():
        plan = await llm.structured(
            SYSTEM,
            f"Plan one creator campaign for this business.\n\nOwner's goal, in their words: {goal}\n\n"
            f"Business facts:\n{_facts(brand)}\n\nBusiness summary: {business.get('summary')}\n"
            f"Past results: {'; '.join(performance.get('insights') or [])}\n"
            f"Budget for this campaign: {'₹%s' % f'{budget:,.0f}' if budget else 'not given'}. Keep at least 10% in reserve.\n"
            f"Campaign type requested: {campaign_type or 'choose paid or barter_product'}.\n"
            f"Allowed creator niches: {', '.join(niches_available)}.",
            Plan,
        )
        out = _clean_plan(plan.model_dump(), budget, niches_available, fallback)
        if campaign_type:
            out["campaignType"] = campaign_type
        return {"engine": "claude", **out}
    count = 3 if (budget or 0) >= 6000 or not budget else max(1, int(budget // 2000))
    out = _clean_plan({
        "campaignName": f"{brand.get('brandName') or 'Local'} creator campaign",
        "objective": goal,
        "approach": "Local creators post about your business to their followers, each with a code you can track.",
        "campaignType": campaign_type or ("paid" if budget else "barter_product"),
        "creatorCount": count,
        "budgetPerCreator": 0,
        "deliverables": "1 reel + 2 stories",
        "timeline": "Within 2 weeks of acceptance",
        "contentIdeas": [],
        "kpis": ["Coupon redemptions", "Link visits"],
        "niches": fallback,
    }, budget, niches_available, fallback)
    return {"engine": "rules", **out}


# 4. Creator Matching -------------------------------------------------------

async def creator_matching(db, plan: dict, brand: dict, language: Optional[str] = None) -> dict:
    brief = {"niches": plan.get("niches") or [], "location": brand.get("location") or "", "campaignType": plan.get("campaignType"), "budgetPerCreator": plan.get("budgetPerCreator") if plan.get("campaignType") == "paid" else None, "language": language}
    ranked = await rank_creators(db, brief, limit=max(6, plan.get("creatorCount", 3) * 2))
    return {"engine": "rules", "brief": brief, "creators": ranked}


# 5. Campaign Assistant -----------------------------------------------------

class CreatorBrief(BaseModel):
    creatorId: str
    brief: str = Field(description="A short, friendly brief for this creator: what to make, key message, do's and don'ts.")


class Briefs(BaseModel):
    items: List[CreatorBrief]


def _rules_brief(plan: dict, brand: dict) -> str:
    parts = [plan.get("objective") or "", f"Deliverables: {plan.get('deliverables')}.", f"Timeline: {plan.get('timeline')}."]
    if brand.get("products"):
        parts.append(f"Feature: {brand['products']}.")
    if plan.get("contentIdeas"):
        parts.append("Ideas: " + "; ".join(plan["contentIdeas"]) + ".")
    return " ".join(p for p in parts if p)


async def campaign_assistant(plan: dict, brand: dict, creators: List[dict]) -> dict:
    if llm.configured():
        roster = "\n".join(f"- id {c['creatorId']}: {c.get('niche')} creator in {c.get('location')}, creates in {c.get('language')}" for c in creators)
        out = await llm.structured(
            SYSTEM,
            f"Write one brief per creator for this campaign.\n\nPlan: {plan.get('objective')} {plan.get('approach')}\n"
            f"Deliverables: {plan.get('deliverables')}. Timeline: {plan.get('timeline')}.\n"
            f"Content ideas: {'; '.join(plan.get('contentIdeas') or [])}\n\nBusiness facts:\n{_facts(brand)}\n\n"
            f"Creators (use these ids exactly):\n{roster}\n\nDo not put phone numbers, emails or social handles in the briefs.",
            Briefs,
            effort="low",
        )
        by_id = {b.creatorId: b.brief for b in out.items}
        return {"engine": "claude", "briefs": {c["creatorId"]: by_id.get(c["creatorId"]) or _rules_brief(plan, brand) for c in creators}}
    text = _rules_brief(plan, brand)
    return {"engine": "rules", "briefs": {c["creatorId"]: text for c in creators}}
