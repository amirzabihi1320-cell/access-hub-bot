from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaymentQuote:
    payment_id: str
    amount_toman: int
    asset: str
    asset_amount: Decimal
    payment_url: str | None = None
    provider_reference: str | None = None
    expires_at: str | None = None
    raw: dict | None = None


@dataclass(frozen=True)
class PaymentStatus:
    payment_id: str
    paid: bool
    status: str
    user_paid_toman: int | None = None
    asset_amount: Decimal | None = None
    transaction_id: str | None = None
    raw: dict | None = None


class PaymentProviderError(Exception):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class BasePaymentProvider(ABC):
    provider_type: str

    @abstractmethod
    async def create_payment(
        self,
        *,
        payment_id: str,
        amount_toman: int,
        callback_url: str,
    ) -> PaymentQuote:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, provider_reference: str) -> PaymentStatus:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, raw_body: bytes, signature: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def get_trx_price_toman(self) -> Decimal:
        raise NotImplementedError

    async def close(self) -> None:
        return None
