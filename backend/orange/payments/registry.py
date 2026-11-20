"""Pick the active payment provider.

PAYMENT_PROVIDER=razorpay|simulated chooses explicitly. Unset, Orange uses
Razorpay when keys exist and the simulated provider otherwise, unless
APP_ENV=production, where simulation is refused.
"""
from __future__ import annotations

import os

from .base import ProviderNotConfigured
from .razorpay import RazorpayProvider
from .simulated import SimulatedProvider


def _production() -> bool:
    return os.environ.get("APP_ENV", "").lower() == "production"


def get_provider(db, provider_name: str | None = None):
    choice = (provider_name or os.environ.get("PAYMENT_PROVIDER", "")).lower()
    razorpay = RazorpayProvider()
    if choice == "razorpay" or (not choice and razorpay.configured):
        return razorpay
    if choice in ("", "simulated"):
        if _production():
            raise ProviderNotConfigured("Payments are not configured. Simulated payments are disabled in production.")
        return SimulatedProvider(db)
    raise ProviderNotConfigured(f"Unknown payment provider '{choice}'.")


def provider_status(db) -> dict:
    try:
        p = get_provider(db)
        return {"provider": p.name, "simulated": p.name == "simulated", "configured": True}
    except ProviderNotConfigured as exc:
        return {"provider": None, "simulated": False, "configured": False, "detail": str(exc)}
