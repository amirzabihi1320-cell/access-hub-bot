"""
VPN Provisioning Service (بند ۱۵: Smart Panel Selection، بند ۱۶: Automatic
VPN Purchase، بند ۱۹: Auto Renew).

این سرویس سطح بالای Order Engine را از جزئیات هر پنل جدا می‌کند: به او
فقط می‌گویی "برای این کاربر یک سرویس با فلان مشخصات بساز"؛ خودش تصمیم
می‌گیرد کدام پنل را امتحان کند و اگر Fail شد به پنل بعدی برود (Failover).

اتصال این سرویس به Order Engine واقعی (بعد از پرداخت موفق، خودکار صدا
زده شود) در فاز Payment→VPN Automation انجام می‌شود؛ فعلاً برای ساخت
سرویس آزمایشی/دستی از پنل ادمین و برای Unit Test قابل استفاده است.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import VPNServiceStatus
from app.core.retry import retry_provider_call
from app.models.vpn_panel import VPNPanel
from app.models.vpn_service import VPNService
from app.providers.exceptions import ProviderError
from app.providers.vpn.base import BaseVPNProvider, VPNUserCreateParams
from app.services.vpn_panel_service import VPNPanelService

logger = logging.getLogger("access_hub.vpn_provisioning")


class NoAvailablePanelError(Exception):
    """هیچ پنل فعالی جواب نداد (بند ۵۸: کاربر نباید خطای فنی ببیند، این خطا در بالادست Catch می‌شود)."""


class VPNProvisioningService:
    #: تاخیر بین تلاش‌های Retry روی *همان* پنل، فقط برای خطاهای موقت/قابل
    #: تلاش‌مجدد (بند ۲۸: Retry 1, Retry 2, Retry 3 با Exponential Backoff).
    #: خطاهای غیرقابل‌تلاش‌مجدد (Auth/Validation) بلافاصله به پنل بعدی می‌روند.
    RETRY_DELAYS_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)

    def __init__(self, session: AsyncSession):
        self.session = session
        self.panel_service = VPNPanelService(session)

    async def _pick_panels(self) -> list[VPNPanel]:
        """
        ترتیب تلاش طبق بند ۱۵: Priority اول، بعد آخرین Health شناخته‌شده
        (پنل‌هایی که آخرین بار ONLINE بوده‌اند زودتر امتحان می‌شوند).
        """
        panels = await self.panel_service.list_active_sorted()
        return sorted(
            panels,
            key=lambda p: (p.priority, 0 if p.last_health_status == "ONLINE" else 1),
        )

    async def _call_with_retry(self, func, *args, **kwargs):
        """
        Retry واقعی حالا در app/core/retry.py متمرکز شده (Provider-agnostic،
        قابل استفاده برای هر Provider آینده - VPN یا Payment). این متد فقط
        RETRY_DELAYS_SECONDS مخصوص VPNProvisioningService را به همان تابع
        عمومی وصل می‌کند تا کلاس‌های فرزند/تست بتوانند تایمینگ را override کنند.
        """
        max_attempts = 1 + len(self.RETRY_DELAYS_SECONDS)
        base_delay = self.RETRY_DELAYS_SECONDS[0] if self.RETRY_DELAYS_SECONDS else 1.0
        return await retry_provider_call(
            lambda: func(*args, **kwargs),
            max_attempts=max_attempts,
            base_delay_seconds=base_delay,
            context=getattr(func, "__name__", "vpn_provider_call"),
        )

    async def _create_user_with_retry(self, provider: BaseVPNProvider, params: VPNUserCreateParams):
        """
        روی یک پنل مشخص، در صورت خطای موقت (ProviderError.retryable=True مثل
        قطعی اتصال/۵xx) تا ۳ بار دیگر با Backoff تصاعدی تلاش می‌کند. خطای
        غیرموقت (Auth/Validation) بدون تلف‌کردن وقت بلافاصله بالا می‌رود تا
        فراخوان (provision_for_user) سراغ پنل بعدی برود - بند ۲۷: Retry →
        Alternative Provider.
        """
        return await self._call_with_retry(provider.create_user, params)

    async def provision_for_user(
        self,
        *,
        user_id: int,
        username_prefix: str,
        data_limit_bytes: int | None,
        expire_at: datetime | None,
        order_id: int | None = None,
        product_id: int | None = None,
        note: str | None = None,
    ) -> VPNService:
        """
        Flow بند ۱۶ (از مرحله‌ی "Select Provider" به بعد): روی اولین پنل
        فعالی که جواب بدهد کاربر می‌سازد، رکورد VPNService را ذخیره و
        برمی‌گرداند. اگر همه‌ی پنل‌ها Fail شدند NoAvailablePanelError
        raise می‌شود تا لایه‌ی بالادستی به کاربر پیام عمومی نشان دهد و
        خطای واقعی را فقط در Log ثبت کند (بند ۵۸).
        """
        panels = await self._pick_panels()
        if not panels:
            raise NoAvailablePanelError("هیچ پنل VPN فعالی ثبت نشده است.")

        remote_username = f"{username_prefix}_{user_id}_{int(datetime.utcnow().timestamp())}"
        last_error: Exception | None = None

        for panel in panels:
            provider = self.panel_service.build_provider(panel)
            try:
                info = await self._create_user_with_retry(
                    provider,
                    VPNUserCreateParams(
                        username=remote_username,
                        data_limit_bytes=data_limit_bytes,
                        expire_at=expire_at,
                        note=note or (f"order:{order_id}" if order_id else None),
                    ),
                )
            except ProviderError as exc:
                logger.warning("VPN provisioning failed on panel %s (%s): %s", panel.id, panel.name, exc.message)
                last_error = exc
                continue
            finally:
                await provider.close()

            service = VPNService(
                user_id=user_id,
                panel_id=panel.id,
                order_id=order_id,
                product_id=product_id,
                remote_username=info.username,
                status=VPNServiceStatus.ACTIVE.value,
                data_limit_bytes=info.data_limit_bytes,
                used_traffic_bytes=info.used_traffic_bytes,
                expire_at=info.expire_at,
                subscription_url=info.subscription_url,
                config_links=json.dumps(info.config_links, ensure_ascii=False),
            )
            self.session.add(service)
            await self.session.commit()
            return service

        # همه‌ی پنل‌ها Fail شدند -> Retry/Manual Review در فاز Order Engine (بند ۲۷، ۲۸)
        logger.error("All VPN panels failed for user_id=%s: %s", user_id, last_error)
        raise NoAvailablePanelError("در حال حاضر امکان ساخت سرویس VPN وجود ندارد.")

    async def renew_service(
        self,
        service_id: int,
        *,
        extra_days: int | None,
        new_data_limit_bytes=...,
    ) -> VPNService:
        """
        Flow بند ۱۹ (Auto Renew): همان اکانت روی همان پنل تمدید می‌شود
        (کاربر جدیدی روی پنل ساخته نمی‌شود، لینک/کانفیگ قبلی همچنان معتبر
        می‌ماند). اگر سرویس هنوز منقضی نشده، تاریخ انقضا از روی تاریخ فعلی
        جمع زده می‌شود؛ اگر منقضی شده، از "الان" شروع می‌شود.

        new_data_limit_bytes=... (پیش‌فرض/Ellipsis) یعنی حجم دست‌نخورده
        بماند؛ مقدار مشخص یعنی این مقدار جایگزین حجم فعلی شود - تصمیم
        این‌که «حجم قبلی حفظ شود یا با مقدار تازه‌ی محصول جایگزین شود» به
        لایه‌ی بالادستی (auto_delivery_service) واگذار شده است.
        """
        service = await self.session.get(VPNService, service_id)
        if service is None:
            raise ValueError("سرویس پیدا نشد.")
        panel = await self.panel_service.get(service.panel_id)
        if panel is None or panel.status != "ACTIVE":
            raise NoAvailablePanelError("پنل مرتبط با این سرویس در دسترس نیست؛ برای تمدید با پشتیبانی تماس بگیرید.")

        new_expire = service.expire_at
        if extra_days:
            now = datetime.now(timezone.utc)
            current_expire = service.expire_at
            if current_expire and current_expire.tzinfo is None:
                current_expire = current_expire.replace(tzinfo=timezone.utc)
            base = current_expire if (current_expire and current_expire > now) else now
            new_expire = base + timedelta(days=extra_days)

        provider = self.panel_service.build_provider(panel)
        try:
            info = await self._call_with_retry(
                provider.modify_user,
                service.remote_username,
                data_limit_bytes=new_data_limit_bytes,
                expire_at=new_expire if extra_days else ...,
                status="ACTIVE",
            )
            # اگر حجم تازه تنظیم شد، مصرف قبلی باید صفر شود وگرنه کاربر
            # ممکن است بلافاصله به سقف حجم برخورد کند. این مرحله Best-effort
            # است: اگر پنل reset_traffic ندارد یا موقتاً خطا داد، خودِ تمدید
            # (که مرحله‌ی مهم‌تر است) Fail نمی‌شود - فقط در Log ثبت می‌شود.
            if new_data_limit_bytes is not ...:
                try:
                    info = await self._call_with_retry(provider.reset_traffic, service.remote_username)
                except (ProviderError, NotImplementedError) as exc:
                    logger.warning(
                        "Traffic reset skipped for %s on panel %s: %s", service.remote_username, panel.id, exc
                    )
        finally:
            await provider.close()

        service.status = VPNServiceStatus.ACTIVE.value
        service.data_limit_bytes = info.data_limit_bytes
        service.used_traffic_bytes = info.used_traffic_bytes
        service.expire_at = info.expire_at
        service.subscription_url = info.subscription_url
        service.config_links = json.dumps(info.config_links, ensure_ascii=False)
        await self.session.commit()
        return service

    async def sync_status(self, service_id: int) -> VPNService:
        """وضعیت/ترافیک واقعی را از روی پنل دوباره می‌خواند و رکورد محلی را به‌روز می‌کند."""
        service = await self.session.get(VPNService, service_id)
        if service is None:
            raise ValueError("سرویس پیدا نشد.")
        panel = await self.panel_service.get(service.panel_id)
        if panel is None:
            raise ValueError("پنل مرتبط با این سرویس پیدا نشد.")

        provider = self.panel_service.build_provider(panel)
        try:
            info = await provider.get_user(service.remote_username)
        finally:
            await provider.close()

        service.status = info.status if info.status in VPNServiceStatus.__members__ else service.status
        service.used_traffic_bytes = info.used_traffic_bytes
        service.data_limit_bytes = info.data_limit_bytes
        service.expire_at = info.expire_at
        service.subscription_url = info.subscription_url
        service.config_links = json.dumps(info.config_links, ensure_ascii=False)
        await self.session.commit()
        return service
