"""Attribution for each collaboration: a coupon code, a tracking link and a QR code.

Counts come only from real events: a click on the link, or the business
entering a code at the counter. Nothing is estimated.
"""
from __future__ import annotations

import io
import re
import secrets
import uuid
from datetime import datetime, timezone

TRACKABLE = ["accepted", "payment_pending", "paid", "in_progress", "link_submitted", "link_verified", "completed"]
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I/L, easy to read aloud


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token(n: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def _stem(name: str) -> str:
    word = re.sub(r"[^A-Za-z]", "", (name or "").split(" ")[0]).upper()
    return word[:6] or "ORANGE"


async def ensure(db, campaign: dict, creator_name: str) -> dict:
    existing = await db.tracking_links.find_one({"campaignId": campaign["id"]}, {"_id": 0})
    if existing:
        return existing
    for _ in range(10):
        code = f"{_stem(creator_name)}-{_token(4)}"
        if not await db.tracking_links.find_one({"couponCode": code}, {"_id": 1}):
            break
    doc = {
        "id": str(uuid.uuid4()), "campaignId": campaign["id"], "slug": _token(8).lower(), "couponCode": code,
        "brandUserId": campaign["brandUserId"], "creatorUserId": campaign["creatorUserId"], "offer": "", "createdAt": now(),
    }
    await db.tracking_links.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def stats(db, tracking_id: str) -> dict:
    clicks = await db.attribution_events.count_documents({"trackingId": tracking_id, "type": "click"})
    reds = await db.attribution_events.find({"trackingId": tracking_id, "type": "redeem"}, {"_id": 0}).to_list(1000)
    return {"clicks": clicks, "redemptions": len(reds), "redeemedValue": round(sum(r.get("amount") or 0 for r in reds), 2)}


async def record(db, tracking: dict, kind: str, amount: float | None = None, meta: dict | None = None) -> dict:
    doc = {"id": str(uuid.uuid4()), "trackingId": tracking["id"], "campaignId": tracking["campaignId"], "type": kind, "amount": amount, "meta": meta or {}, "createdAt": now()}
    await db.attribution_events.insert_one(doc)
    doc.pop("_id", None)
    return doc


def qr_svg(url: str) -> bytes:
    import qrcode
    import qrcode.image.svg

    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue()
