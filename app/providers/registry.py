"""
Registry مرکزی Provider Engine.

اضافه‌کردن پنل VPN جدید (مثلاً Sanaei کامل، Hiddify، X-UI و ...):
۱) کلاس Provider را در app/providers/vpn/ بنویس (ارث از BaseVPNProvider)
۲) این‌جا در VPN_PROVIDERS ثبتش کن.
هیچ فایل دیگری در پروژه نیازی به تغییر ندارد - این خودِ همان اصل
"Source Code باید Generic باشد" (بند ۶۷ سند) است.
"""
from __future__ import annotations

from app.core.enums import VPNPanelType
from app.providers.vpn.base import BaseVPNProvider
from app.providers.vpn.marzban import MarzbanProvider

VPN_PROVIDERS: dict[str, type[BaseVPNProvider]] = {
    VPNPanelType.MARZBAN.value: MarzbanProvider,
    # VPNPanelType.SANAEI.value: SanaeiProvider,  # فاز بعد - پیاده‌سازی کامل طبق بند ۱۳
}


class UnsupportedPanelTypeError(Exception):
    pass


def build_vpn_provider(
    panel_type: str,
    *,
    base_url: str,
    username: str,
    password: str,
) -> BaseVPNProvider:
    """
    یک نمونه‌ی Provider آماده‌ی استفاده برمی‌گرداند. فراخوان مسئول
    صداکردن ``await provider.close()`` بعد از اتمام کار است (بهتر است
    از ``async with`` در سرویس بالادستی استفاده شود).
    """
    provider_cls = VPN_PROVIDERS.get(panel_type)
    if provider_cls is None:
        raise UnsupportedPanelTypeError(
            f"نوع پنل «{panel_type}» هنوز پیاده‌سازی نشده است. "
            f"پنل‌های پشتیبانی‌شده: {', '.join(VPN_PROVIDERS.keys())}"
        )
    return provider_cls(base_url=base_url, username=username, password=password)
