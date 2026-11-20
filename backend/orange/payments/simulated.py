"""Simulated provider for development and demos. Moves no money."""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid

from .base import PaymentError, PaymentProvider


class SimulatedProvider(PaymentProvider):
    name = "simulated"
    checkout = "simulated"

    def __init__(self, db):
        self.db = db
        self.secret = os.environ.get("SIMULATED_PAYMENT_SECRET") or os.environ.get("JWT_SECRET", "simulated")

    def sign(self, order_id: str, payment_id: str) -> str:
        return hmac.new(self.secret.encode(), f"sim|{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()

    async def create_order(self, amount_paise, receipt, notes):
        order_id = f"sim_order_{uuid.uuid4().hex[:16]}"
        await self.db.simulated_orders.insert_one({"id": order_id, "amount": amount_paise, "receipt": receipt, "notes": notes, "status": "created"})
        return {"id": order_id, "amount": amount_paise, "currency": "INR"}

    async def settle_order(self, order_id: str) -> dict:
        """Stand-in for the customer completing checkout."""
        order = await self.db.simulated_orders.find_one({"id": order_id}, {"_id": 0})
        if not order:
            raise PaymentError("Unknown simulated order", status_code=404)
        payment_id = f"sim_pay_{uuid.uuid4().hex[:16]}"
        await self.db.simulated_orders.update_one({"id": order_id}, {"$set": {"status": "paid", "paymentId": payment_id}})
        await self.db.simulated_payments.insert_one({"id": payment_id, "order_id": order_id, "amount": order["amount"], "status": "captured"})
        return {"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": self.sign(order_id, payment_id)}

    def verify_signature(self, order_id, payment_id, signature):
        return hmac.compare_digest(self.sign(order_id, payment_id), signature or "")

    async def fetch_payment(self, payment_id):
        p = await self.db.simulated_payments.find_one({"id": payment_id}, {"_id": 0})
        if not p:
            raise PaymentError("Unknown simulated payment", status_code=404)
        return p

    async def capture(self, payment_id, amount_paise):
        await self.db.simulated_payments.update_one({"id": payment_id}, {"$set": {"status": "captured"}})
        return await self.fetch_payment(payment_id)

    async def transfer_to_creator(self, payment_id, account_id, amount_paise, notes):
        return {"id": f"sim_trf_{uuid.uuid4().hex[:16]}"}

    async def refund(self, payment_id, amount_paise, notes):
        await self.db.simulated_payments.update_one({"id": payment_id}, {"$set": {"status": "refunded"}})
        return {"id": f"sim_rfnd_{uuid.uuid4().hex[:16]}", "amount": amount_paise}
