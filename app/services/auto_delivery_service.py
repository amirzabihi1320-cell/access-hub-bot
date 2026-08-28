"""
Payment → VPN Automation (بند ۵۷ سند).

این سرویس عمداً از OrderService جدا نگه داشته شده تا مسیر پرداخت اصلی
(کسر پول/Token + Ledger) دست‌نخورده و بدون هیچ وابستگی جدیدی به
Provider Engine باقی بماند - اگر VPN Engine یا یک پنل خاص مشکل داشته
باشد، هرگز روی خرید محصولات غیر-VPN تاثیر نمی‌گذارد.

فراخوانی: بعد از create_and_pay/create_and_pay_with_coupon/create_and_pay_token
موفق و *داخل همان session* (قبل از بسته‌شدن آن)، اگر product.is_vpn_product
باشد این تابع صدا زده می‌شود.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderStatus, WalletTransactionType
from app.models.order import Order
from app.models.product import Product
from app.models.vpn_service import VPNService
from app.providers.exceptions import ProviderError
from app.services.vpn_provisioning_service import NoAvailablePanelError, VPNProvisioningService
from app.services.wallet_service import InsufficientBalanceError, WalletService

logger = logging.getLogger("access_hub.auto_delivery")


def format_vpn_delivery_text(subscription_url: str | None, config_links: list[str]) -> str:
    lines = ["🔐 <b>سرویس VPN شما آماده شد</b>"]
    if subscription_url:
        lines.append(f"\nلینک اشتراک (Subscription):\n<code>{subscription_url}</code>")
    if config_links:
        lines.append("\nکانفیگ مستقیم:")
        for link in config_links[:5]:
            lines.append(f"<code>{link}</code>")
    lines.append("\nاین لینک را داخل اپلیکیشن VPN خود Import کنید.")
    return "\n".join(lines)


async def try_auto_deliver_vpn(session: AsyncSession, order: Order, product: Product) -> tuple[bool, str]:
    """
    تلاش برای تحویل خودکار. در صورت موفقیت، order.status را COMPLETED
    می‌کند و متن تحویل را برمی‌گرداند. در صورت شکست (بند ۲۷: Retry →
    Alternative Provider → Manual Review)، وضعیت سفارش دست‌نخورده
    (WAITING_ADMIN، طبق مقداردهی خودِ OrderService) باقی می‌ماند تا ادمین
    دستی رسیدگی کند - کاربر فقط پیام عمومی می‌بیند (بند ۵۸).
    """
    if not product.is_vpn_product:
        return False, ""

    data_limit_bytes = (
        product.vpn_data_limit_gb * 1024 ** 3 if product.vpn_data_limit_gb else None
    )
    expire_at = (
        datetime.now(timezone.utc) + timedelta(days=product.vpn_duration_days)
        if product.vpn_duration_days
        else None
    )

    provisioning = VPNProvisioningService(session)
    try:
        service = await provisioning.provision_for_user(
            user_id=order.user_id,
            username_prefix="ah",
            data_limit_bytes=data_limit_bytes,
            expire_at=expire_at,
            order_id=order.id,
            product_id=product.id,
            note=f"order:{order.order_number or order.id}",
        )
    except NoAvailablePanelError as exc:
        logger.error("Auto VPN delivery failed for order_id=%s: %s", order.id, exc)
        return False, ""

    config_links = json.loads(service.config_links) if service.config_links else []
    delivery_text = format_vpn_delivery_text(service.subscription_url, config_links)

    order.status = OrderStatus.COMPLETED.value
    order.delivery_type = "API"
    order.delivery_data = json.dumps(
        {
            "vpn_service_id": service.id,
            "subscription_url": service.subscription_url,
            "config_links": config_links,
        },
        ensure_ascii=False,
    )
    await session.commit()
    return True, delivery_text


async def try_auto_renew_vpn(session: AsyncSession, user_id: int, service_id: int) -> tuple[bool, str]:
    """
    Auto Renew (بند ۱۹): Payment → Verify → Provider → Extend User →
    Update Database → Notify.

    مبلغ تمدید طبق قیمت *فعلیِ* محصول مبدا کسر می‌شود (نه قیمت لحظه‌ی خرید
    اول)، چون قیمت‌ها ممکن است از آن موقع تغییر کرده باشند. اگر تمدید روی
    پنل شکست بخورد، مبلغ کسرشده بلافاصله Refund می‌شود (بند ۲۶: هیچ Balance
    بدون Ledger تغییر نمی‌کند - Refund همیشه یک رکورد جدید است، نه ویرایش).
    خروجی (False, "") یعنی خطای فنی رخ داده و پیام عمومی باید نشان داده شود؛
    خروجی (False, "متن مشخص") یعنی خطای قابل‌فهم برای کاربر است (مثلاً موجودی
    ناکافی) و همان متن مستقیم نمایش داده شود.
    """
    service = await session.get(VPNService, service_id)
    if service is None or service.user_id != user_id:
        return False, "❌ سرویس پیدا نشد."
    if service.product_id is None:
        return False, "❌ این سرویس به‌صورت دستی ساخته شده و تمدید خودکار برایش تعریف نشده؛ با پشتیبانی تماس بگیرید."

    product = await session.get(Product, service.product_id)
    if product is None or not product.status:
        return False, "❌ محصول مربوط به این سرویس دیگر در دسترس نیست."

    price = product.fixed_price if product.product_type == "FIXED" else product.unit_price
    if not price or price <= 0:
        return False, "❌ قیمت تمدید این محصول تنظیم نشده است."

    order = Order(
        user_id=user_id,
        product_id=product.id,
        quantity=1,
        unit_price=price,
        final_price=price,
        status=OrderStatus.PENDING.value,
        delivery_type="VPN_RENEWAL",
    )
    session.add(order)
    await session.flush()
    order.order_number = f"AH-{order.id:06d}"

    try:
        await WalletService(session).debit(
            user_id=user_id,
            amount=price,
            type_=WalletTransactionType.PURCHASE,
            reference_id=f"renewal-order:{order.id}",
            description=f"تمدید {product.name}",
        )
    except InsufficientBalanceError:
        await session.rollback()
        return False, f"❌ موجودی کیف‌پول کافی نیست. مبلغ تمدید: {price:,} تومان"

    data_limit_bytes = product.vpn_data_limit_gb * 1024 ** 3 if product.vpn_data_limit_gb else None

    provisioning = VPNProvisioningService(session)
    try:
        renewed = await provisioning.renew_service(
            service.id,
            extra_days=product.vpn_duration_days,
            new_data_limit_bytes=data_limit_bytes,
        )
    except (ProviderError, NoAvailablePanelError, ValueError) as exc:
        logger.error("Auto VPN renewal failed for service_id=%s: %s", service_id, exc)
        # پرداخت را برگردان - کاربر نباید بابت تمدیدی که انجام نشد پول بدهد.
        await WalletService(session).credit(
            user_id=user_id,
            amount=price,
            type_=WalletTransactionType.REFUND,
            reference_id=f"renewal-refund:order:{order.id}",
            description=f"بازگشت وجه تمدید ناموفق {product.name}",
        )
        order.status = OrderStatus.REFUNDED.value
        await session.commit()
        return False, ""

    order.status = OrderStatus.COMPLETED.value
    order.delivery_data = json.dumps(
        {
            "vpn_service_id": renewed.id,
            "renewed_expire_at": renewed.expire_at.isoformat() if renewed.expire_at else None,
        },
        ensure_ascii=False,
    )
    await session.commit()

    config_links = json.loads(renewed.config_links) if renewed.config_links else []
    expire_text = renewed.expire_at.strftime("%Y-%m-%d") if renewed.expire_at else "بدون انقضا"
    text = (
        f"✅ <b>سرویس با موفقیت تمدید شد</b>\n"
        f"انقضای جدید: {expire_text}\n\n" + format_vpn_delivery_text(renewed.subscription_url, config_links)
    )
    return True, text
