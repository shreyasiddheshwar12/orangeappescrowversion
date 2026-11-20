from __future__ import annotations

import asyncio
import hashlib
import hmac
import os

import requests

from .base import PaymentError, PaymentProvider, ProviderNotConfigured

API_BASE = "https://api.razorpay.com/v1"


class RazorpayProvider(PaymentProvider):
    name = "razorpay"
    checkout = "razorpay"

    def __init__(self, key_id: str | None = None, key_secret: str | None = None):
        self.key_id = key_id if key_id is not None else os.environ.get("RAZORPAY_KEY_ID", "")
        self.key_secret = key_secret if key_secret is not None else os.environ.get("RAZORPAY_KEY_SECRET", "")

    @property
    def configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    @property
    def public_key(self):
        return self.key_id

    def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self.configured:
            raise ProviderNotConfigured("Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to backend/.env.")
        response = requests.request(method, f"{API_BASE}{path}", auth=(self.key_id, self.key_secret), timeout=20, **kwargs)
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("description", "Razorpay API error")
            except Exception:
                detail = "Razorpay API error"
            raise PaymentError(detail)
        return response.json()

    async def _call(self, method: str, path: str, **kwargs) -> dict:
        return await asyncio.to_thread(self._request, method, path, **kwargs)

    async def create_order(self, amount_paise, receipt, notes):
        return await self._call("POST", "/orders", json={"amount": amount_paise, "currency": "INR", "receipt": receipt[:40], "notes": notes})

    def verify_signature(self, order_id, payment_id, signature):
        if not self.key_secret:
            return False
        expected = hmac.new(self.key_secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature or "")

    async def fetch_payment(self, payment_id):
        return await self._call("GET", f"/payments/{payment_id}")

    async def capture(self, payment_id, amount_paise):
        return await self._call("POST", f"/payments/{payment_id}/capture", json={"amount": amount_paise, "currency": "INR"})

    async def transfer_to_creator(self, payment_id, account_id, amount_paise, notes):
        result = await self._call("POST", f"/payments/{payment_id}/transfers", json={"transfers": [{
            "account": account_id, "amount": amount_paise, "currency": "INR", "on_hold": False, "notes": notes,
        }]})
        items = result.get("items", [])
        return {"id": items[0].get("id") if items else result.get("id")}

    async def refund(self, payment_id, amount_paise, notes):
        return await self._call("POST", f"/payments/{payment_id}/refund", json={"amount": amount_paise, "notes": notes})
