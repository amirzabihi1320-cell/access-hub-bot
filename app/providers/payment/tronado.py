from __future__ import annotations

import hashlib
import hmac
import json
from decimal import Decimal, InvalidOperation

import httpx

from app.providers.payment.base import (
    BasePaymentProvider,
    PaymentProviderError,
    PaymentQuote,
    PaymentStatus,
)


class TronadoProvider(BasePaymentProvider):
    """Adapter for Tronado Public API v5.

    The Telegram bot @tronadorobot is not automated by pretending to be a
    user/bot. This adapter uses Tronado's documented server API instead.
    """

    provider_type = "TRONADO"

    def __init__(
        self,
        *,
        api_key: str,
        ipn_signing_key: str,
        wallet_address: str,
        base_url: str = "https://bot.tronado.cloud",
        timeout: float = 30.0,
        wage_from_business_percentage: int = 0,
    ) -> None:
        if not api_key:
            raise ValueError("Tronado API key is required")
        if not wallet_address:
            raise ValueError("Tronado destination TRON wallet is required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.ipn_signing_key = ipn_signing_key
        self.wallet_address = wallet_address
        self.wage_from_business_percentage = max(0, min(100, int(wage_from_business_percentage)))
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"x-api-key": self.api_key, "accept": "application/json"},
        )

    async def _post(self, path: str, payload: dict) -> dict:
        try:
            response = await self.client.post(path, json=payload)
        except httpx.RequestError as exc:
            raise PaymentProviderError(f"ارتباط با Tronado برقرار نشد: {exc}", retryable=True) from exc
        if response.status_code == 429:
            raise PaymentProviderError("محدودیت درخواست Tronado فعال شده است.", retryable=True)
        if response.status_code >= 500:
            raise PaymentProviderError(f"Tronado HTTP {response.status_code}", retryable=True)
        if response.status_code >= 400:
            raise PaymentProviderError(
                f"Tronado درخواست را رد کرد: HTTP {response.status_code} {response.text[:300]}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise PaymentProviderError("پاسخ Tronado JSON معتبر نیست.", retryable=True) from exc
        if isinstance(data, dict) and data.get("Code") not in (None, 0, "0"):
            raise PaymentProviderError(str(data.get("Message") or data.get("message") or "Tronado error"))
        return data

    @staticmethod
    def _first(data: dict, *keys: str):
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return None

    async def get_trx_price_toman(self) -> Decimal:
        data = await self._post("/Tron/GetPriceToToman", {})
        obj = data.get("Data") or data.get("data") or data
        value = self._first(obj, "TronPriceToman", "tron_price_toman", "Price", "price")
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:
            raise PaymentProviderError("قیمت TRX از Tronado قابل خواندن نیست.") from exc

    async def create_payment(self, *, payment_id: str, amount_toman: int, callback_url: str) -> PaymentQuote:
        if amount_toman <= 0:
            raise ValueError("مبلغ پرداخت باید مثبت باشد.")
        price = await self.get_trx_price_toman()
        if price <= 0:
            raise PaymentProviderError("قیمت TRX نامعتبر است.")
        trx_amount = (Decimal(amount_toman) / price).quantize(Decimal("0.000001"))
        data = await self._post(
            "/api/v5/GetOrderToken",
            {
                "PaymentID": payment_id,
                "WalletAddress": self.wallet_address,
                "TronAmount": float(trx_amount),
                "CallbackUrl": callback_url,
                "WageFromBusinessPercentage": self.wage_from_business_percentage,
            },
        )
        obj = data.get("Data") or data.get("data") or data
        payment_url = self._first(obj, "FullPaymentUrl", "full_payment_url", "PaymentUrl", "payment_url")
        provider_id = self._first(obj, "OrderID", "orderId", "TrndOrderID", "TrndOrderId", "id")
        return PaymentQuote(
            payment_id=payment_id,
            amount_toman=amount_toman,
            asset="TRX",
            asset_amount=trx_amount,
            payment_url=str(payment_url) if payment_url else None,
            provider_reference=str(provider_id) if provider_id else None,
            raw=data,
        )

    async def get_status(self, provider_reference: str) -> PaymentStatus:
        data = await self._post("/Order/GetStatus", {"ID": provider_reference})
        obj = data.get("Data") or data.get("data") or data
        status_id = self._first(obj, "OrderStatusID", "orderStatusID", "status_id", "StatusID")
        is_paid = bool(self._first(obj, "IsPaid", "isPaid", "is_paid")) or str(status_id) == "30"
        status = str(self._first(obj, "OrderStatusTitle", "status", "Status") or status_id or "UNKNOWN")
        user_paid = self._first(obj, "UserPaidTomanAmount", "user_paid_toman_amount")
        trx_amount = self._first(obj, "TronAmount", "tron_amount")
        txid = self._first(obj, "TXID", "TxID", "txid", "TransactionID")
        return PaymentStatus(
            payment_id=str(self._first(obj, "PaymentID", "paymentID") or provider_reference),
            paid=is_paid,
            status=status,
            user_paid_toman=int(user_paid) if user_paid is not None else None,
            asset_amount=Decimal(str(trx_amount)) if trx_amount is not None else None,
            transaction_id=str(txid) if txid else None,
            raw=data,
        )

    def verify_webhook(self, raw_body: bytes, signature: str) -> dict:
        if not self.ipn_signing_key:
            raise PaymentProviderError("کلید امضای Webhook Tronado تنظیم نشده است.")
        expected = hmac.new(
            self.ipn_signing_key.encode("utf-8"), raw_body, hashlib.sha512
        ).hexdigest()
        if not signature or not hmac.compare_digest(expected, signature.strip().lower()):
            raise PaymentProviderError("امضای Webhook Tronado نامعتبر است.")
        try:
            event = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PaymentProviderError("Webhook Tronado JSON نامعتبر است.") from exc
        if not isinstance(event, dict):
            raise PaymentProviderError("Webhook Tronado باید یک JSON object باشد.")
        return event

    async def close(self) -> None:
        await self.client.aclose()
