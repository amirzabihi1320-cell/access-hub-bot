"""
VPN Engine - رابط انتزاعی مشترک همه‌ی Providerهای پنل VPN (بند ۹، ۱۱، ۱۸).

Product VPN (مثلاً "100GB / 30 روزه") مستقل از Provider VPN (مثلاً
"Marzban Server 1") است (بند ۱۱) - این کلاس فقط لایه‌ی ارتباط با *پنل*
است؛ تصمیم این‌که کدام پنل برای کدام محصول استفاده شود بر عهده‌ی
VPNProvisioningService (لایه‌ی بالادستی، Smart Panel Selection - بند ۱۵) است.

هر پنل جدید (Sanaei، X-UI، Hiddify و ...) فقط باید این کلاس را پیاده‌سازی
کند و در app/providers/registry.py ثبت شود.
"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.providers.base import BaseProvider


@dataclass
class VPNUserCreateParams:
    """
    ورودی عمومی ساخت کاربر روی یک پنل VPN. فیلدهایی که یک پنل خاص
    پشتیبانی نمی‌کند را نادیده می‌گیرد (مثلاً Sanaei ممکن است inbound_tags
    را متفاوت تفسیر کند).
    """
    username: str
    data_limit_bytes: int | None = None  # None = نامحدود
    expire_at: datetime | None = None  # None = بدون انقضا
    note: str | None = None
    inbound_tags: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


@dataclass
class VPNUserInfo:
    """خروجی عمومی و یکسان از هر پنلی - بدون توجه به فرمت داخلی پنل."""
    username: str
    status: str  # ACTIVE / DISABLED / EXPIRED / LIMITED / ERROR
    data_limit_bytes: int | None
    used_traffic_bytes: int
    expire_at: datetime | None
    subscription_url: str | None
    config_links: list[str] = field(default_factory=list)  # vless://, vmess://, ...
    raw: dict = field(default_factory=dict)


class BaseVPNProvider(BaseProvider):
    """
    رابط تخصصی پنل‌های VPN. متدهای CRUD کاربر + مدیریت وضعیت که در بند
    ۱۲ (Marzban) و ۱۳ (Sanaei) به‌صورت صریح خواسته شده‌اند.
    """

    @abstractmethod
    async def create_user(self, params: VPNUserCreateParams) -> VPNUserInfo:
        raise NotImplementedError

    @abstractmethod
    async def get_user(self, username: str) -> VPNUserInfo:
        raise NotImplementedError

    @abstractmethod
    async def modify_user(
        self,
        username: str,
        *,
        data_limit_bytes: int | None = ...,
        expire_at: datetime | None = ...,
        status: str | None = None,
    ) -> VPNUserInfo:
        """
        برای پارامترهایی که کاربر تغییرشان نمی‌خواهد مقدار پیش‌فرض ``...``
        (Ellipsis) به‌عنوان "دست‌نخورده بماند" استفاده می‌شود تا بشود
        data_limit_bytes=None را از "تغییری نده" تمیز داد.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_user(self, username: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def revoke_user(self, username: str) -> VPNUserInfo:
        """UUID/کانفیگ کاربر را باطل و مجدداً تولید می‌کند (لینک‌های قبلی از کار می‌افتند)."""
        raise NotImplementedError

    @abstractmethod
    async def enable_user(self, username: str) -> VPNUserInfo:
        raise NotImplementedError

    @abstractmethod
    async def disable_user(self, username: str) -> VPNUserInfo:
        raise NotImplementedError

    async def get_capacity_info(self) -> dict:
        """
        اطلاعات ظرفیت پنل برای Smart Panel Selection (بند ۱۵)، مثل
        {"current_users": 120, "max_users": 500}. اگر پنل پشتیبانی نکند
        دیکشنری خالی برمی‌گردد و انتخابگر فقط بر اساس Priority/Health تصمیم می‌گیرد.
        """
        return {}

    async def reset_traffic(self, username: str) -> VPNUserInfo:
        """
        شمارنده‌ی ترافیک مصرفی کاربر را صفر می‌کند (بدون تغییر Data Limit یا
        Expire). استفاده‌ی اصلی: تمدید سرویس (بند ۱۹) - بعد از تمدید، کاربر
        باید یک سیکل مصرف تازه داشته باشد. پنل‌هایی که این قابلیت را ندارند
        NotImplementedError برمی‌گردانند و VPNProvisioningService این را
        Best-effort در نظر می‌گیرد (شکست این مرحله کل تمدید را Fail نمی‌کند).
        """
        raise NotImplementedError

    async def reset_traffic(self, username: str) -> None:
        """
        مصرف ترافیک کاربر را صفر می‌کند (برای Auto-Renew - بند ۱۹: در شروع
        دوره‌ی جدید، مصرف قبلی نباید باقی بماند). پنل‌هایی که این قابلیت
        را ندارند NotImplementedError برمی‌گردانند و فراخوان (VPNRenewalService)
        این حالت را نادیده می‌گیرد - Extend انجام می‌شود ولی مصرف قدیم صفر نمی‌شود.
        """
        raise NotImplementedError
