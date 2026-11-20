"""TrustScore: a 0-100 reputation built from completed work on Orange.

Only measured factors count, and the score is scaled over them, like matching.
Profiles show "New" until 3 collaborations are completed.

Creator: on-time delivery 30, rating 25, completion 20, response 15, repeat brands 10.
Business: payment reliability 35, approval turnaround 25, rating from creators 25, completion 15.
On-time delivery and approval turnaround need state timestamps, which Orange
records from this release (`statusHistory`). Older collaborations aren't counted for them.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

MIN_COMPLETED = 3
CREATOR_WEIGHTS = {"onTime": 30, "rating": 25, "completion": 20, "response": 15, "repeat": 10}
BUSINESS_WEIGHTS = {"payment": 35, "turnaround": 25, "rating": 25, "completion": 15}
ON_TIME_DAYS = 14   # content submitted within 14 days of payment
TURNAROUND_DAYS = 3  # content approved within 3 days of submission


def _ts(c: dict, status: str) -> Optional[datetime]:
    for h in c.get("statusHistory") or []:
        if h.get("status") == status:
            return datetime.fromisoformat(h["at"])
    return None


def _ratio(n: int, d: int) -> Optional[float]:
    return n / d if d else None


def _combine(factors: dict, weights: dict, completed: int) -> dict:
    known = {k: v for k, (v, _) in factors.items() if v is not None}
    weight = sum(weights[k] for k in known)
    score = round(100 * sum(weights[k] * v for k, v in known.items()) / weight) if weight else None
    return {
        "score": score if completed >= MIN_COMPLETED else None,
        "isNew": completed < MIN_COMPLETED,
        "completed": completed,
        "coverage": weight,
        "factors": [{"factor": k, "weight": weights[k], "value": v, "detail": d} for k, (v, d) in factors.items()],
    }


async def _ratings_for(db, user_id: str) -> list:
    return await db.ratings.find({"targetId": user_id}, {"_id": 0, "rating": 1}).to_list(1000)


async def creator_trust(db, user_id: str) -> dict:
    cs = await db.campaigns.find({"$or": [{"senderUserId": user_id}, {"receiverUserId": user_id}]}, {"_id": 0}).to_list(1000)
    completed = [c for c in cs if c["status"] == "completed"]
    started = [c for c in cs if c["status"] in ("completed", "disputed") or (c["status"] == "cancelled" and c.get("paymentStatus") == "paid")]
    incoming = [c for c in cs if c.get("receiverUserId") == user_id]
    answered = [c for c in incoming if c["status"] != "requested"]
    timed = [(_ts(c, "paid"), _ts(c, "link_submitted")) for c in completed]
    timed = [(a, b) for a, b in timed if a and b]
    on_time = sum(1 for a, b in timed if (b - a).days <= ON_TIME_DAYS)
    brands = [c["senderUserId"] if c.get("senderType") == "business" else c["receiverUserId"] for c in completed]
    repeat_brands = sum(1 for b in set(brands) if brands.count(b) > 1)
    rs = await _ratings_for(db, user_id)
    avg = sum(r["rating"] for r in rs) / len(rs) if rs else None
    factors = {
        "onTime": (_ratio(on_time, len(timed)), f"{on_time} of {len(timed)} delivered within {ON_TIME_DAYS} days of payment" if timed else "Not measured yet"),
        "rating": ((avg - 1) / 4 if avg is not None else None, f"Average {avg:.1f}/5 from {len(rs)} reviews" if rs else "No reviews yet"),
        "completion": (_ratio(len(completed), len(started)), f"{len(completed)} of {len(started)} paid collaborations completed" if started else "No paid collaborations yet"),
        "response": (_ratio(len(answered), len(incoming)), f"Answered {len(answered)} of {len(incoming)} requests" if incoming else "No requests yet"),
        "repeat": (_ratio(repeat_brands, len(set(brands))) if brands else None, f"{repeat_brands} of {len(set(brands))} brands came back" if brands else "No brands yet"),
    }
    return _combine(factors, CREATOR_WEIGHTS, len(completed))


async def business_trust(db, user_id: str) -> dict:
    cs = await db.campaigns.find({"$or": [{"senderUserId": user_id}, {"receiverUserId": user_id}]}, {"_id": 0}).to_list(1000)
    completed = [c for c in cs if c["status"] == "completed"]
    accepted = [c for c in cs if c["status"] not in ("requested",) and not (c["status"] == "cancelled" and c.get("paymentStatus") != "paid")]
    paid = [c for c in accepted if c.get("paymentStatus") == "paid" or c["status"] == "completed"]
    started = [c for c in cs if c["status"] in ("completed", "disputed") or (c["status"] == "cancelled" and c.get("paymentStatus") == "paid")]
    timed = [(_ts(c, "link_submitted"), _ts(c, "link_verified")) for c in completed]
    timed = [(a, b) for a, b in timed if a and b]
    quick = sum(1 for a, b in timed if (b - a).days <= TURNAROUND_DAYS)
    rs = await _ratings_for(db, user_id)
    avg = sum(r["rating"] for r in rs) / len(rs) if rs else None
    factors = {
        "payment": (_ratio(len(paid), len(accepted)), f"Paid {len(paid)} of {len(accepted)} accepted collaborations" if accepted else "No accepted collaborations yet"),
        "turnaround": (_ratio(quick, len(timed)), f"{quick} of {len(timed)} approved within {TURNAROUND_DAYS} days" if timed else "Not measured yet"),
        "rating": ((avg - 1) / 4 if avg is not None else None, f"Average {avg:.1f}/5 from {len(rs)} creators" if rs else "No reviews yet"),
        "completion": (_ratio(len(completed), len(started)), f"{len(completed)} of {len(started)} paid collaborations completed" if started else "No paid collaborations yet"),
    }
    return _combine(factors, BUSINESS_WEIGHTS, len(completed))
