"""
Payment Provider Engine - رابط انتزاعی Providerهای پرداخت ارز دیجیتال
(بند ۱ سند ماژول اضافه: TronPaymentProvider / TronadoProvider / ...).

دقیقاً هم‌الگو با app/providers/vpn/base.py: این کلاس از BaseProvider
(app/providers/base.py) ارث می‌برد و فقط متدهای دامنه‌محور پرداخت
ارز دیجیتال را اضافه می‌کند. Core (Wallet Engine / Order Engine) فقط
همین Interface را می‌شناسد - هیچ Provider خاصی (Tronado و ...) نباید
مستقیم در Core Hard-code شود (بند ۱ و ۲۴ سند).
"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from app.providers.base import BaseProvider


@dataclass
class PaymentOrderResult:
    """خروجی یکسان ایجاد سفارش واریز، مستقل از این‌که Provider واقعی چه فرمتی برمی‌گرداند."""
    provider_order_id: str
    status: str
    crypto_amount: Decimal
    payment_url: str | None = None
    expected_wallet_address: str | None = None
    provider_reference: str | None = None
    raw: dict = field(default_factory=dict)


class BasePaymentProvider(BaseProvider):
    """
    رابط تخصصی Providerهای پرداخت ارز دیجیتال (بند ۱، ۲ سند).

    ⚠️ طبق بند ۲۵ سند: پیاده‌سازی هر متد این کلاس باید بر اساس مستندات
    رسمی و واقعی Provider باشد - هیچ Endpoint/Schema فرضی ساخته نشود.
    کلاس‌های Concrete (مثل TronadoProvider) تا وقتی مستندات رسمی API
    تایید نشده باشد، NotImplementedError صریح برمی‌گردانند تا این تفاوت
    با "پیاده‌سازی واقعی" همیشه شفاف بماند.
    """

    #: مقداری که در PaymentProviderType/registry استفاده می‌شود.
    provider_type: str = "generic_payment"

    @abstractmethod
    async def get_trx_price_toman(self) -> Decimal:
        """قیمت لحظه‌ای ۱ TRX به تومان (بند ۲: دریافت قیمت TRX)."""
        raise NotImplementedError

    @abstractmethod
    async def create_deposit_order(
        self,
        *,
        toman_amount: int,
        idempotency_key: str,
    ) -> PaymentOrderResult:
        """
        سفارش پرداخت TRX جدید نزد Provider می‌سازد (بند ۲: ایجاد سفارش
        پرداخت + تولید Payment URL). idempotency_key باید به Provider
        پاس داده شود (در صورت پشتیبانی) تا Retry باعث سفارش تکراری نشود.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_deposit_status(self, provider_order_id: str) -> str:
        """وضعیت سفارش نزد Provider (بند ۲: دریافت وضعیت سفارش)."""
        raise NotImplementedError

    @abstractmethod
    async def verify_deposit(self, provider_order_id: str) -> bool:
        """
        تایید قطعی پرداخت مستقیماً از Provider (نه فقط تکیه بر Webhook) -
        بند ۲: Verify Payment. لایه‌ی بالادستی (CryptoDepositService) این
        متد را هم در پردازش Webhook و هم در یک بررسی دوره‌ای صدا می‌زند
        تا هرگز فقط به یک منبع (Webhook) تکیه نشود.
        """
        raise NotImplementedError

    async def verify_webhook_signature(self, payload: dict, headers: dict) -> bool:
        """
        صحت Webhook دریافتی را بررسی می‌کند (امضا/HMAC طبق مستندات Provider).
        پیش‌فرض False است تا تا وقتی Provider واقعی این را پیاده نکرده،
        هیچ Webhook به‌صورت کورکورانه Trusted در نظر گرفته نشود.
        """
        return False
