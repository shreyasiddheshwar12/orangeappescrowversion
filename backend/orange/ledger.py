"""Append-only money ledger. Every movement of a collaboration's funds gets one entry."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

ENTRY_TYPES = {"funded", "commission", "barter_fee", "payout_released", "payout_pending", "refund"}


async def record(db, *, campaign_id: str, entry_type: str, amount: float, provider: str, payment_id: str | None = None, meta: dict | None = None) -> dict:
    if entry_type not in ENTRY_TYPES:
        raise ValueError(f"Unknown ledger entry type {entry_type}")
    doc = {
        "id": str(uuid.uuid4()),
        "campaignId": campaign_id,
        "type": entry_type,
        "amount": round(float(amount), 2),
        "currency": "INR",
        "provider": provider,
        "simulated": provider == "simulated",
        "paymentId": payment_id,
        "meta": meta or {},
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    await db.ledger_entries.insert_one(doc)
    doc.pop("_id", None)
    return doc
