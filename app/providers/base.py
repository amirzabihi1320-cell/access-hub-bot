"""
Provider Engine - رابط انتزاعی مشترک همه‌ی Providerهای خارجی (بند ۹).

هر Provider (VPN، SMM، Digital API و ...) باید از BaseProvider ارث‌بری کند.
هدف: افزودن Provider جدید نباید به تغییر Core نیاز داشته باشد - فقط یک
کلاس جدید اینجا/زیرپوشه‌ی مربوطه پیاده‌سازی و در app/providers/registry.py
ثبت می‌شود.

این کلاس عمداً "کمینه و عمومی" است؛ نیازهای دامنه‌محور (مثل VPN) در
زیرکلاس‌های تخصصی مثل app/providers/vpn/base.py اضافه می‌شوند
(Interface Segregation - Provider VPN مجبور به پیاده‌سازی چیزهایی مثل
Refund عمومی هم نیست مگر واقعاً معنا داشته باشد).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.enums import HealthStatus


@dataclass
class ProviderHealth:
    status: HealthStatus
    detail: str = ""
    latency_ms: float | None = None


@dataclass
class ProviderOrderResult:
    """نتیجه‌ی عمومی ایجاد/بررسی سفارش نزد یک Provider خارجی."""
    provider_order_id: str
    status: str
    raw: dict = field(default_factory=dict)


class BaseProvider(ABC):
    """
    رابط پایه. تمام متدها async هستند و در صورت خطا باید یکی از
    Exceptionهای app/providers/exceptions.py را raise کنند - هرگز
    مستقیم None/False برای خطا برنگردانید تا لایه‌ی بالادستی نتواند
    خطای واقعی را از "موفقیت با نتیجه‌ی خالی" تشخیص بدهد.
    """

    #: مقداری که در VPNPanelType/سایر Enumهای نوع Provider استفاده می‌شود.
    provider_type: str = "generic"

    @abstractmethod
    async def authenticate(self) -> None:
        """اتصال/گرفتن توکن را برقرار می‌کند. نتیجه داخلی cache می‌شود."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Provider در دسترس است یا نه (بند ۵۴: Health Monitoring)."""
        raise NotImplementedError

    async def get_balance(self) -> float | None:
        """موجودی حساب نزد Provider (اگر Provider این مفهوم را دارد)."""
        return None

    async def get_products(self) -> list[dict]:
        """فهرست محصولات/پلن‌های قابل خرید نزد Provider (در صورت پشتیبانی)."""
        return []

    async def get_price(self, provider_product_id: str) -> float | None:
        return None

    async def create_order(self, provider_product_id: str, **kwargs) -> ProviderOrderResult:
        raise NotImplementedError

    async def check_order(self, provider_order_id: str) -> ProviderOrderResult:
        raise NotImplementedError

    async def cancel_order(self, provider_order_id: str) -> bool:
        return False

    async def refund_order(self, provider_order_id: str) -> bool:
        return False

    async def handle_webhook(self, payload: dict) -> dict:
        """پردازش Webhook دریافتی از Provider (در صورت پشتیبانی)."""
        return {}

    async def close(self) -> None:
        """آزادسازی منابع (مثل httpx.AsyncClient) - در finally صدا زده شود."""
        return None
