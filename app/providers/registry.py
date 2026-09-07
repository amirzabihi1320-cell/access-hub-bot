"""
Registry مرکزی Provider Engine.

اضافه‌کردن پنل VPN جدید (مثلاً Sanaei کامل، Hiddify، X-UI و ...):
۱) کلاس Provider را در app/providers/vpn/ بنویس (ارث از BaseVPNProvider)
۲) این‌جا در VPN_PROVIDERS ثبتش کن.
هیچ فایل دیگری در پروژه نیازی به تغییر ندارد - این خودِ همان اصل
"Source Code باید Generic باشد" (بند ۶۷ سند) است.
"""
from __future__ import annotations

from app.core.enums import PaymentProviderType, VPNPanelType
from app.providers.payment.base import BasePaymentProvider
from app.providers.payment.tronado import TronadoProvider
from app.providers.vpn.base import BaseVPNProvider
from app.providers.vpn.marzban import MarzbanProvider
from app.providers.vpn.sanaei import SanaeiProvider

VPN_PROVIDERS: dict[str, type[BaseVPNProvider]] = {
    VPNPanelType.MARZBAN.value: MarzbanProvider,
    VPNPanelType.SANAEI.value: SanaeiProvider,
}

# افزودن Provider پرداخت جدید (TON و ...): ۱) کلاس در app/providers/payment/،
# ۲) این‌جا ثبت کن. هیچ فایل دیگری (Wallet/Order Engine) نیازی به تغییر ندارد.
PAYMENT_PROVIDERS: dict[str, type[BasePaymentProvider]] = {
    PaymentProviderType.TRONADO.value: TronadoProvider,
}


class UnsupportedPanelTypeError(Exception):
    pass


def build_vpn_provider(
    panel_type: str,
    *,
    base_url: str,
    username: str,
    password: str,
    default_inbound_id: int | None = None,
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
    kwargs = {"base_url": base_url, "username": username, "password": password}
    if provider_cls is SanaeiProvider:
        kwargs["default_inbound_id"] = default_inbound_id
    return provider_cls(**kwargs)


class UnsupportedPaymentProviderError(Exception):
    pass


def build_payment_provider(provider_type: str, *, api_key: str, api_url: str) -> BasePaymentProvider:
    """
    مشابه build_vpn_provider - فراخوان مسئول ``await provider.close()``
    بعد از اتمام کار است.
    """
    provider_cls = PAYMENT_PROVIDERS.get(provider_type)
    if provider_cls is None:
        raise UnsupportedPaymentProviderError(
            f"Payment Provider «{provider_type}» پشتیبانی نمی‌شود. "
            f"پشتیبانی‌شده‌ها: {', '.join(PAYMENT_PROVIDERS.keys())}"
        )
    return provider_cls(api_key=api_key, api_url=api_url)
