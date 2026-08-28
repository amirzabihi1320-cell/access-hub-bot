"""
Auto Renew (بند ۱۹ سند): Renew → Payment → Verify → Provider → Extend User →
Update Database → Notify.

فقط برای سرویس‌هایی که از یک سفارش واقعی (order_id) ساخته شده‌اند و آن
سفارش هنوز به یک Product متصل است قابل استفاده است - چون قیمت و مدت
تمدید از همان Product خوانده می‌شود (بند ۲۰: Traffic Packages). سرویس‌های
دستی (بدون order_id، مثلاً ساخته‌شده برای تست از پنل ادمین) قابل تمدید
خودکار نیستند.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import VPNServiceStatus, WalletTransactionType
from app.models.order import Order
from app.models.product import Product
from app.models.vpn_service import VPNService
from app.providers.exceptions import ProviderError
from app.services.pricing_service import calculate_price
from app.services.vpn_panel_service import VPNPanelService
from app.services.wallet_service import WalletService

logger = logging.getLogger("access_hub.vpn_renewal")


class ServiceNotRenewableError(Exception):
    """این سرویس اطلاعات کافی (محصول اصلی/پنل فعال) برای تمدید خودکار ندارد."""


class VPNRenewalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.panel_service = VPNPanelService(session)

    async def _get_service_owned_by(self, service_id: int, user_id: int) -> VPNService:
        service = await self.session.get(VPNService, service_id)
        if service is None or service.user_id != user_id:
            raise ServiceNotRenewableError("سرویس پیدا نشد.")
        return service

    async def _get_renewable_product(self, service: VPNService) -> Product:
        if not service.order_id:
            raise ServiceNotRenewableError(
                "این سرویس محصول مرجعی برای تمدید خودکار ندارد؛ برای تمدید با پشتیبانی تماس بگیر."
            )
        order = await self.session.get(Order, service.order_id)
        if order is None:
            raise ServiceNotRenewableError("سفارش اصلی این سرویس پیدا نشد.")
        product = await self.session.get(Product, order.product_id)
        if product is None or not product.is_vpn_product:
            raise ServiceNotRenewableError("محصول اصلی این سرویس دیگر برای تمدید خودکار در دسترس نیست.")
        return product

    async def get_renewal_quote(self, service_id: int, user_id: int) -> tuple[VPNService, Product, int]:
        """قیمت تمدید را بدون کسر پول برمی‌گرداند - برای نمایش پیش از تأیید کاربر."""
        service = await self._get_service_owned_by(service_id, user_id)
        product = await self._get_renewable_product(service)
        price = calculate_price(product, 1)
        return service, product, price.total_price

    async def renew_service(self, service_id: int, user_id: int) -> tuple[VPNService, int]:
        """
        کیف‌پول کاربر را برای مبلغ تمدید کسر می‌کند (Ledger مستقل - بند ۲۳)،
        پنل مربوطه را Extend می‌کند و رکورد محلی را به‌روز می‌کند.

        اگر Provider هنگام Extend شکست بخورد، مبلغ کسرشده بلافاصله Refund
        می‌شود (بند ۲۷) تا کاربر برای سرویسی که واقعاً تمدید نشده پول نداده
        باشد؛ خطای فنی Provider هرگز به کاربر نمایش داده نمی‌شود (بند ۵۸)،
        فقط پیام «تمدید ناموفق بود، مبلغ بازگشت داده شد» + جزئیات در Log.

        برمی‌گرداند: (VPNService به‌روزشده, مبلغی که نهایتاً کسر ماند)
        """
        service = await self._get_service_owned_by(service_id, user_id)
        product = await self._get_renewable_product(service)
        panel = await self.panel_service.get(service.panel_id)
        if panel is None or panel.status != "ACTIVE":
            raise ServiceNotRenewableError("پنل مرتبط با این سرویس در حال حاضر در دسترس نیست.")

        price = calculate_price(product, 1)
        amount = price.total_price

        # هر تمدید reference_id یکتای خودش را دارد (بند ۲۹: Idempotency) -
        # امکان کسر دوباره برای همین درخواست تمدید وجود ندارد.
        reference_id = f"vpn-renew:{service.id}:{int(datetime.now(timezone.utc).timestamp())}"
        await WalletService(self.session).debit(
            user_id=user_id,
            amount=amount,
            type_=WalletTransactionType.PURCHASE,
            reference_id=reference_id,
            description=f"تمدید سرویس VPN #{service.id} ({product.name})",
        )

        provider = self.panel_service.build_provider(panel)
        try:
            now = datetime.now(timezone.utc)
            base_time = service.expire_at if (service.expire_at and service.expire_at > now) else now
            new_expire = base_time + timedelta(days=product.vpn_duration_days) if product.vpn_duration_days else None
            new_limit = product.vpn_data_limit_gb * 1024 ** 3 if product.vpn_data_limit_gb else None

            try:
                await provider.reset_traffic(service.remote_username)
            except NotImplementedError:
                pass  # همه‌ی پنل‌ها Reset ترافیک را پشتیبانی نمی‌کنند - مشکلی نیست، فقط Extend انجام می‌شود.

            info = await provider.modify_user(
                service.remote_username,
                data_limit_bytes=new_limit,
                expire_at=new_expire,
                status="ACTIVE",
            )
        except ProviderError as exc:
            logger.error("VPN renewal failed for service_id=%s: %s", service.id, exc.message)
            await WalletService(self.session).credit(
                user_id=user_id,
                amount=amount,
                type_=WalletTransactionType.REFUND,
                reference_id=f"{reference_id}:refund",
                description=f"بازگشت وجه تمدید ناموفق سرویس VPN #{service.id}",
            )
            raise
        finally:
            await provider.close()

        service.status = VPNServiceStatus.ACTIVE.value
        service.expire_at = info.expire_at
        service.data_limit_bytes = info.data_limit_bytes
        service.used_traffic_bytes = info.used_traffic_bytes
        if info.subscription_url:
            service.subscription_url = info.subscription_url
        if info.config_links:
            service.config_links = json.dumps(info.config_links, ensure_ascii=False)
        await self.session.commit()
        return service, amount
