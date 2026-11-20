"""Payment provider interface.

Orange never moves money itself. A provider (Razorpay Route today, possibly
Cashfree later) does. The simulated provider exists so the full collaboration
lifecycle can be developed and demoed without live keys; every record it
creates is marked ``mode: simulated``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class PaymentError(Exception):
    """Provider rejected a request. ``status_code`` maps to the HTTP response."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class ProviderNotConfigured(PaymentError):
    def __init__(self, message: str):
        super().__init__(message, status_code=503)


class PaymentProvider(ABC):
    name: str = "base"
    # Checkout handled by the browser: "razorpay" opens Razorpay Checkout,
    # "simulated" asks the backend to settle the order.
    checkout: str = "none"

    @property
    def public_key(self) -> Optional[str]:
        return None

    @abstractmethod
    async def create_order(self, amount_paise: int, receipt: str, notes: dict) -> dict:
        """Return at least ``{"id": order_id, "amount": amount_paise}``."""

    @abstractmethod
    def verify_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        ...

    @abstractmethod
    async def fetch_payment(self, payment_id: str) -> dict:
        """Return ``{"order_id", "amount", "status"}`` with status in authorized/captured/failed."""

    @abstractmethod
    async def capture(self, payment_id: str, amount_paise: int) -> dict:
        ...

    @abstractmethod
    async def transfer_to_creator(self, payment_id: str, account_id: str, amount_paise: int, notes: dict) -> dict:
        """Release funds to a creator's linked account. Return ``{"id": transfer_id}``."""

    @abstractmethod
    async def refund(self, payment_id: str, amount_paise: int, notes: dict) -> dict:
        ...
