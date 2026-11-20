"""Creator Matching. Deterministic and explainable: every point in the score comes from stored data.

Weights (out of 100): niche 25, location 20, price fit 20, TrustScore 15,
measured engagement 10, language 5, availability 5. A factor with no data is
left out and the score is scaled over the factors we could measure, so a
missing number never counts for or against a creator. `coverage` says how much
of the 100 points the score is based on.
"""
from __future__ import annotations

from typing import Optional

from ..trust import creator_trust

WEIGHTS = {"niche": 25, "location": 20, "price": 20, "trust": 15, "engagement": 10, "language": 5, "availability": 5}
IN_FLIGHT = ["requested", "accepted", "payment_pending", "paid", "in_progress", "link_submitted", "link_verified"]
TRUST_MIN_COMPLETED = 3


def _parts(location: str) -> tuple[str, str]:
    bits = [b.strip().lower() for b in (location or "").split(",") if b.strip()]
    if not bits:
        return "", ""
    return bits[0], bits[-1]


def _norm(xs) -> set[str]:
    return {str(x).strip().lower() for x in (xs or []) if str(x).strip()}


def niche_factor(creator: dict, niches: list[str]):
    wanted = _norm(niches)
    if not wanted:
        return None, "No target niche was set, so niche was not scored."
    primary = (creator.get("niche") or "").strip().lower()
    others = _norm(creator.get("niches")) | ({primary} if primary else set())
    if primary in wanted:
        return 1.0, f"Main niche is {creator.get('niche')}, which you're looking for."
    hit = others & wanted
    if hit:
        return 0.7, f"Also creates {', '.join(sorted(hit))} content."
    return 0.0, f"Main niche is {creator.get('niche') or 'not set'}, outside your target."


def location_factor(creator: dict, location: str):
    area, city = _parts(location)
    if not city:
        return None, "Your location isn't set, so distance was not scored."
    c_area, c_city = _parts(creator.get("location", ""))
    if not c_city:
        return None, "Creator hasn't set a location."
    if area and c_area == area:
        return 1.0, f"Based in {creator.get('location')}, your own area."
    if c_city == city or c_area == city:
        return 0.7, f"Based in {creator.get('location')}, same city."
    return 0.0, f"Based in {creator.get('location')}, a different city."


def price_factor(creator: dict, campaign_type: str, budget_per_creator: Optional[float]):
    if campaign_type != "paid":
        if creator.get("barterEnabled", True):
            return 1.0, "Open to barter collaborations."
        return 0.0, "Doesn't take barter collaborations."
    if not creator.get("paidCollabsEnabled", True):
        return 0.0, "Isn't taking paid collaborations right now."
    price = creator.get("reelPrice") or 0
    if not price:
        return None, "Hasn't set a reel price."
    if not budget_per_creator:
        return None, "No budget per creator was set, so price was not scored."
    if price <= budget_per_creator:
        return 1.0, f"Reel price ₹{price:,.0f} fits the ₹{budget_per_creator:,.0f} budget."
    if price <= budget_per_creator * 1.25:
        return 0.5, f"Reel price ₹{price:,.0f} is slightly over the ₹{budget_per_creator:,.0f} budget."
    return 0.0, f"Reel price ₹{price:,.0f} is well over the ₹{budget_per_creator:,.0f} budget."


def trust_factor(creator: dict, completed: int, trust_score: Optional[int] = None):
    if trust_score is None:
        return None, f"New on Orange ({completed} completed), so there's no TrustScore yet."
    return trust_score / 100, f"TrustScore {trust_score} from {completed} completed collaborations."


def engagement_factor(creator: dict):
    if not creator.get("engagementMeasured") or creator.get("engagementRate") is None:
        return None, "Engagement hasn't been measured yet."
    rate = float(creator["engagementRate"])
    return min(rate / 6.0, 1.0), f"Measured engagement {rate:.1f}%."


def language_factor(creator: dict, language: Optional[str]):
    if not language:
        return None, "No content language was set."
    if (creator.get("language") or "").strip().lower() == language.strip().lower():
        return 1.0, f"Creates in {creator.get('language')}."
    return 0.0, f"Creates in {creator.get('language') or 'an unknown language'}, not {language}."


def availability_factor(active: int):
    if active <= 1:
        return 1.0, "Has room for new work."
    if active <= 3:
        return 0.5, f"Already has {active} collaborations in progress."
    return 0.2, f"Busy with {active} collaborations in progress."


def score_creator(creator: dict, brief: dict, *, completed: int = 0, active: int = 0, trust_score: Optional[int] = None) -> dict:
    factors = {
        "niche": niche_factor(creator, brief.get("niches") or []),
        "location": location_factor(creator, brief.get("location") or ""),
        "price": price_factor(creator, brief.get("campaignType") or "paid", brief.get("budgetPerCreator")),
        "trust": trust_factor(creator, completed, trust_score),
        "engagement": engagement_factor(creator),
        "language": language_factor(creator, brief.get("language")),
        "availability": availability_factor(active),
    }
    known = {k: v for k, (v, _) in factors.items() if v is not None}
    weight = sum(WEIGHTS[k] for k in known)
    score = round(100 * sum(WEIGHTS[k] * v for k, v in known.items()) / weight) if weight else 0
    breakdown = [
        {"factor": k, "weight": WEIGHTS[k], "value": v, "points": None if v is None else round(WEIGHTS[k] * v, 1), "reason": reason}
        for k, (v, reason) in factors.items()
    ]
    return {"score": score, "coverage": weight, "breakdown": breakdown}


async def rank_creators(db, brief: dict, *, limit: int = 8) -> list[dict]:
    """Rank visible, verified creators for a brief. Hard filters: not blacklisted, visible, verified."""
    q = {"instagramVerified": True, "isBlacklisted": {"$ne": True}, "isVisible": {"$ne": False}}
    creators = await db.creator_profiles.find(q, {"_id": 0}).to_list(500)
    results = []
    for c in creators:
        uid = c["userId"]
        party = {"$or": [{"senderUserId": uid}, {"receiverUserId": uid}]}
        completed = await db.campaigns.count_documents({**party, "status": "completed"})
        active = await db.campaigns.count_documents({**party, "status": {"$in": IN_FLIGHT}})
        ts = (await creator_trust(db, uid))["score"] if completed >= TRUST_MIN_COMPLETED else None
        s = score_creator(c, brief, completed=completed, active=active, trust_score=ts)
        niche_value = next(b["value"] for b in s["breakdown"] if b["factor"] == "niche")
        if niche_value == 0.0:
            continue  # wrong niche entirely: never recommend
        results.append({
            "creatorId": c["id"],
            "name": c.get("name", ""),
            "instagramUsername": c.get("instagramUsername"),
            "niche": c.get("niche", ""),
            "location": c.get("location", ""),
            "language": c.get("language", ""),
            "reelPrice": c.get("reelPrice", 0),
            "followersCount": c.get("followersCount"),
            "engagementRate": c.get("engagementRate") if c.get("engagementMeasured") else None,
            "completedCollabs": completed,
            **s,
        })
    results.sort(key=lambda r: (-r["score"], -r["coverage"], r["reelPrice"] or 0))
    return results[:limit]
