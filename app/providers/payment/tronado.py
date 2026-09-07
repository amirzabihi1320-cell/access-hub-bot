"""
TronadoProvider - Adapter مستقل برای Tronado (بند ۲ سند ماژول اضافه).

⚠️ وضعیت فعلی این فایل: SKELETON، نه پیاده‌سازی کامل.

طبق بند ۲۵ سند ("هیچ Endpoint یا قابلیت فرضی ساخته نشود")، تا وقتی
مستندات رسمی API واقعی Tronado (Base URL درست، مسیر دقیق Endpointها،
فرمت Request/Response، نحوه‌ی Authentication، Webhook Signature، Error
Codeها و Rate Limit) در اختیار نباشد، این کلاس نباید هیچ مسیر HTTP
فرضی بسازد - چون در بهترین حالت کار نمی‌کند و در بدترین حالت باعث
گم‌شدن پول واقعی کاربر می‌شود (پرداخت واقعی TRX در میان است).

آنچه *الان* آماده و واقعی است (بدون فرض‌سازی):
- ساختار Provider مطابق BasePaymentProvider/BaseProvider (Core فقط این
  Interface را می‌شناسد - افزودن Tronado کامل بعداً هیچ فایل دیگری را
  تغییر نمی‌دهد).
- خواندن Credential از PaymentProviderConfig (DB) - نه Hard-code.
- httpx.AsyncClient آماده با base_url/headers standard (Authorization
  Bearer به‌عنوان حدس منطقی اولیه - باید با مستندات واقعی Tronado
  تطبیق داده شود، فعلاً مصرف نمی‌شود چون هیچ Endpoint واقعی صدا زده نمی‌شود).
- منطق Idempotency/Health-check-caching که مستقل از API واقعی است.

هر متدی که واقعاً به یک Endpoint HTTP نیاز دارد، عمداً
``ProviderNotConfiguredError`` (خطای اختصاصی همین فایل) raise می‌کند تا
لایه‌ی بالادستی (CryptoDepositService) پیام روشن به ادمین بدهد:
"مستندات رسمی Tronado هنوز پیاده‌سازی نشده"، نه یک خطای HTTP گنگ از یک
Endpoint ساختگی.

برای تکمیل این فایل:
۱) لینک مستندات رسمی/پنل توسعه‌دهنده‌ی Tronado را بده.
۲) هر متد پایین با Endpoint واقعی پر می‌شود (فقط همان متد تغییر می‌کند،
   بقیه‌ی پروژه دست‌نخورده می‌ماند - این دقیقاً همان مزیت Adapter Pattern
   بند ۲۴ سند است).
"""
from __future__ import annotations

from decimal import Decimal

import httpx

from app.providers.exceptions import ProviderAuthError, ProviderConnectionError
from app.providers.base import ProviderHealth
from app.providers.payment.base import BasePaymentProvider, PaymentOrderResult
from app.core.enums import HealthStatus, PaymentProviderType


class ProviderNotConfiguredError(Exception):
    """
    Endpoint واقعی این عملیات هنوز طبق مستندات رسمی Tronado پیاده‌سازی
    نشده (بند ۲۵ سند). این خطا عمداً از ProviderError جدا نگه داشته شده
    تا با یک خطای واقعیِ زمان اجرا (مثلاً قطعی شبکه) اشتباه گرفته نشود.
    """

    def __init__(self, operation: str):
        super().__init__(
            f"عملیات «{operation}» برای Tronado هنوز پیاده‌سازی نشده - "
            "نیاز به مستندات رسمی API (بند ۲۵ سند: بدون Endpoint فرضی)."
        )
        self.operation = operation


class TronadoProvider(BasePaymentProvider):
    provider_type = PaymentProviderType.TRONADO.value

    def __init__(self, *, api_key: str, api_url: str, timeout_seconds: float = 15.0):
        if not api_url:
            raise ProviderAuthError("آدرس API Tronado تنظیم نشده است.")
        self._api_key = api_key
        self._api_url = api_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout_seconds
        self._authenticated = False

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._api_url,
                timeout=self._timeout,
                # TODO(tronado-docs): روش Authentication واقعی را طبق مستندات
                # رسمی جایگزین کن (Bearer/HMAC-per-request/API-Key header و...).
                headers={"Authorization": f"Bearer {self._api_key}"} if self._api_key else {},
            )
        return self._client

    async def authenticate(self) -> None:
        # بدون Endpoint رسمی برای اعتبارسنجی مستقیم، health_check تنها
        # سیگنال "در دسترس بودن" است - نه "Credential معتبر است".
        self._authenticated = True

    async def health_check(self) -> ProviderHealth:
        if not self._api_url or not self._api_key:
            return ProviderHealth(status=HealthStatus.UNKNOWN, detail="API Key/URL تنظیم نشده")
        # TODO(tronado-docs): جایگزین با یک GET سبک به Endpoint واقعی
        # وضعیت/Ping Tronado (مثلاً بررسی موجودی یا نسخه‌ی API).
        raise ProviderNotConfiguredError("health_check")

    async def get_trx_price_toman(self) -> Decimal:
        raise ProviderNotConfiguredError("get_trx_price_toman")

    async def create_deposit_order(
        self,
        *,
        toman_amount: int,
        idempotency_key: str,
    ) -> PaymentOrderResult:
        raise ProviderNotConfiguredError("create_deposit_order")

    async def get_deposit_status(self, provider_order_id: str) -> str:
        raise ProviderNotConfiguredError("get_deposit_status")

    async def verify_deposit(self, provider_order_id: str) -> bool:
        raise ProviderNotConfiguredError("verify_deposit")

    async def handle_webhook(self, payload: dict) -> dict:
        # TODO(tronado-docs): پارس فرمت واقعی Webhook Tronado + تایید امضا
        # از طریق verify_webhook_signature قبل از هرگونه اعتماد به payload.
        raise ProviderNotConfiguredError("handle_webhook")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
