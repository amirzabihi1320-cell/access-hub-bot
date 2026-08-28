"""
نمایش «📦 سفارش‌های من» برای کاربر و دکمه‌ی «✅ تحویل شد» برای ادمین
(بخش ۱۵ و ۱۸ سند). ساخت/پرداخت سفارش خودش در handlers/shop.py انجام
می‌شود؛ اینجا فقط نمایش تاریخچه و تکمیل تحویل دستی است.
"""
import json

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.base import get_session
from app.models.product import Product
from app.models.user import User
from app.models.vpn_service import VPNService
from app.providers.exceptions import ProviderError
from app.services.auto_delivery_service import format_vpn_delivery_text, try_auto_renew_vpn
from app.services.order_service import OrderAlreadyProcessedError, OrderService, build_order_report_text
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.services.vpn_renewal_service import ServiceNotRenewableError, VPNRenewalService
from app.services.wallet_service import InsufficientBalanceError

router = Router(name="orders")
settings = get_settings()

STATUS_LABELS = {
    "PENDING": "⏳ در انتظار",
    "WAITING_PAYMENT": "⏳ در انتظار پرداخت",
    "PAID": "✅ پرداخت‌شده",
    "PROCESSING": "🔄 در حال پردازش",
    "WAITING_ADMIN": "🔄 در حال آماده‌سازی",
    "COMPLETED": "✅ تکمیل‌شده",
    "FAILED": "❌ ناموفق",
    "CANCELLED": "❌ لغوشده",
    "REFUNDED": "↩️ بازگشت وجه",
}


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


async def build_orders_view(session: AsyncSession, tg_user) -> str:
    user = await UserService(session).get_or_create(
        tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name
    )
    orders = await OrderService(session).list_for_user(user.id, limit=10)

    if not orders:
        return "📦 <b>سفارش‌های من</b>\n\nهنوز سفارشی ثبت نشده."

    lines = ["📦 <b>سفارش‌های من</b>\n"]
    for order in orders:
        product = await session.get(Product, order.product_id)
        label = STATUS_LABELS.get(order.status, order.status)
        code = f"#{order.order_number}" if order.order_number else f"#{order.id}"
        lines.append(
            f"{code} — {product.name if product else '—'} — {order.final_price:,} تومان — {label}"
        )
    return "\n".join(lines)


async def list_vpn_services_for_user(session: AsyncSession, user_id: int) -> list[VPNService]:
    result = await session.execute(
        select(VPNService).where(VPNService.user_id == user_id).order_by(VPNService.created_at.desc())
    )
    return list(result.scalars().all())


def vpn_services_entry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔐 سرویس‌های VPN من", callback_data="myservices:list")]]
    )


VPN_STATUS_LABELS = {
    "ACTIVE": "🟢 فعال",
    "EXPIRED": "🔴 منقضی‌شده",
    "DISABLED": "⛔️ غیرفعال",
    "ERROR": "⚠️ خطا",
}


def _format_traffic(used: int, limit: int | None) -> str:
    used_gb = used / 1024 ** 3
    if limit:
        limit_gb = limit / 1024 ** 3
        return f"{used_gb:.1f} از {limit_gb:.0f} GB"
    return f"{used_gb:.1f} GB (نامحدود)"


@router.callback_query(F.data == "myservices:list")
async def handle_my_vpn_services(callback: CallbackQuery) -> None:
    async with get_session() as session:
        user = await UserService(session).get_or_create(
            callback.from_user.id, callback.from_user.username, callback.from_user.first_name,
            callback.from_user.last_name,
        )
        services = await list_vpn_services_for_user(session, user.id)

    if not services:
        await callback.message.edit_text("🔐 <b>سرویس‌های VPN من</b>\n\nهنوز سرویسی نداری.")
        await callback.answer()
        return

    rows = []
    lines = ["🔐 <b>سرویس‌های VPN من</b>\n"]
    for service in services:
        expire_text = service.expire_at.strftime("%Y-%m-%d") if service.expire_at else "بدون انقضا"
        label = VPN_STATUS_LABELS.get(service.status, service.status)
        lines.append(
            f"{label} — انقضا: {expire_text} — "
            f"{_format_traffic(service.used_traffic_bytes, service.data_limit_bytes)}"
        )
        row = [InlineKeyboardButton(text=f"🔗 کانفیگ ({service.id})", callback_data=f"myservices:view:{service.id}")]
        if service.product_id is not None:
            row.append(InlineKeyboardButton(text="🔄 تمدید", callback_data=f"myservices:renew:{service.id}"))
        rows.append(row)
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("myservices:view:"))
async def handle_my_vpn_service_view(callback: CallbackQuery) -> None:
    service_id = int(callback.data.split(":")[2])
    async with get_session() as session:
        user = await UserService(session).get_or_create(
            callback.from_user.id, callback.from_user.username, callback.from_user.first_name,
            callback.from_user.last_name,
        )
        service = await session.get(VPNService, service_id)

    # مالکیت سرویس چک می‌شود تا کاربری نتواند با حدس‌زدن آیدی، کانفیگ کاربر دیگری را ببیند.
    if service is None or service.user_id != user.id:
        await callback.answer("سرویس پیدا نشد.", show_alert=True)
        return

    config_links = json.loads(service.config_links) if service.config_links else []
    text = format_vpn_delivery_text(service.subscription_url, config_links)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔄 تمدید سرویس", callback_data=f"myservices:renew:quote:{service.id}")]]
    )
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("myservices:renew:quote:"))
async def handle_vpn_renew_quote(callback: CallbackQuery) -> None:
    service_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        user = await UserService(session).get_or_create(
            callback.from_user.id, callback.from_user.username, callback.from_user.first_name,
            callback.from_user.last_name,
        )
        try:
            service, product, price = await VPNRenewalService(session).get_renewal_quote(service_id, user.id)
        except ServiceNotRenewableError as e:
            await callback.answer(f"❌ {e}", show_alert=True)
            return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأیید و پرداخت از کیف پول", callback_data=f"myservices:renew:confirm:{service_id}")],
            [InlineKeyboardButton(text="❌ انصراف", callback_data=f"myservices:view:{service_id}")],
        ]
    )
    await callback.message.answer(
        f"🔄 <b>تمدید سرویس</b>\n\n"
        f"محصول: {product.name}\n"
        f"مبلغ تمدید: {price:,} تومان (از کیف پول کسر می‌شود)\n\n"
        "برای تأیید، دکمه‌ی زیر را بزن.",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("myservices:renew:confirm:"))
async def handle_vpn_renew_confirm(callback: CallbackQuery) -> None:
    service_id = int(callback.data.split(":")[3])
    await callback.answer("⏳ در حال تمدید...")
    async with get_session() as session:
        user = await UserService(session).get_or_create(
            callback.from_user.id, callback.from_user.username, callback.from_user.first_name,
            callback.from_user.last_name,
        )
        try:
            service, amount = await VPNRenewalService(session).renew_service(service_id, user.id)
        except InsufficientBalanceError:
            await callback.message.edit_text("❌ موجودی کیف پول کافی نیست.")
            return
        except ServiceNotRenewableError as e:
            await callback.message.edit_text(f"❌ {e}")
            return
        except ProviderError:
            # پول قبلاً Refund شده (داخل VPNRenewalService)؛ کاربر خطای فنی نمی‌بیند (بند ۵۸).
            await callback.message.edit_text(
                "⚠️ در حال حاضر امکان تمدید خودکار سرویس وجود ندارد. "
                "مبلغ به کیف پول شما بازگشت داده شد. لطفاً بعداً دوباره تلاش کن یا با پشتیبانی تماس بگیر."
            )
            return

        config_links = json.loads(service.config_links) if service.config_links else []

    expire_text = service.expire_at.strftime("%Y-%m-%d") if service.expire_at else "بدون انقضا"
    await callback.message.edit_text(
        f"✅ <b>سرویس با موفقیت تمدید شد</b>\n\n"
        f"مبلغ کسرشده: {amount:,} تومان\n"
        f"انقضای جدید: {expire_text}\n\n"
        + format_vpn_delivery_text(service.subscription_url, config_links)
    )


@router.callback_query(F.data.startswith("myservices:renew:"))
async def handle_my_vpn_service_renew_confirm(callback: CallbackQuery) -> None:
    service_id = int(callback.data.split(":")[2])
    async with get_session() as session:
        user = await UserService(session).get_or_create(
            callback.from_user.id, callback.from_user.username, callback.from_user.first_name,
            callback.from_user.last_name,
        )
        service = await session.get(VPNService, service_id)
        if service is None or service.user_id != user.id:
            await callback.answer("سرویس پیدا نشد.", show_alert=True)
            return
        if service.product_id is None:
            await callback.answer("تمدید خودکار برای این سرویس تعریف نشده.", show_alert=True)
            return
        product = await session.get(Product, service.product_id)

    if product is None or not product.status:
        await callback.answer("❌ محصول مربوط به این سرویس دیگر در دسترس نیست.", show_alert=True)
        return

    price = product.fixed_price if product.product_type == "FIXED" else product.unit_price
    duration_text = f"{product.vpn_duration_days} روز" if product.vpn_duration_days else "بدون تغییر انقضا"
    await callback.message.edit_text(
        f"🔄 <b>تمدید سرویس</b>\n\n"
        f"محصول: {product.name}\n"
        f"مدت افزوده: {duration_text}\n"
        f"هزینه: {price:,} تومان (از کیف‌پول کسر می‌شود)\n\n"
        "تایید می‌کنی؟",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ بله، تمدید کن", callback_data=f"myservices:renew_go:{service_id}"),
                    InlineKeyboardButton(text="❌ انصراف", callback_data="myservices:list"),
                ]
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("myservices:renew_go:"))
async def handle_my_vpn_service_renew_execute(callback: CallbackQuery) -> None:
    service_id = int(callback.data.split(":")[2])
    await callback.answer("⏳ در حال تمدید...")

    async with get_session() as session:
        user = await UserService(session).get_or_create(
            callback.from_user.id, callback.from_user.username, callback.from_user.first_name,
            callback.from_user.last_name,
        )
        ok, text = await try_auto_renew_vpn(session, user.id, service_id)

    if ok:
        await callback.message.edit_text(text)
    else:
        await callback.message.edit_text(
            text or "❌ در حال حاضر امکان تمدید وجود ندارد. مبلغ (در صورت کسر) به کیف‌پول برگشت داده شد؛ "
            "لطفاً بعداً دوباره امتحان کن یا با پشتیبانی تماس بگیر."
        )


@router.callback_query(F.data.startswith("admin:order:deliver:"))
async def handle_admin_deliver(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return

    order_id = int(callback.data.split(":")[3])

    async with get_session() as session:
        order_service = OrderService(session)
        try:
            order = await order_service.mark_delivered(order_id)
        except OrderAlreadyProcessedError:
            await callback.answer("این سفارش قبلاً پردازش شده است.", show_alert=True)
            return
        target_user = await session.get(User, order.user_id)
        product = await session.get(Product, order.product_id)
        report_enabled = await SettingsService(session).is_order_report_enabled()

    current_text = callback.message.text or callback.message.caption or ""
    await callback.message.edit_text(current_text + "\n\n✅ <b>تحویل شد</b>", reply_markup=None)
    await callback.answer("ثبت شد ✅")

    if target_user:
        try:
            await callback.bot.send_message(
                chat_id=target_user.telegram_id,
                text=(
                    "✅ <b>سفارش شما تحویل داده شد</b>\n\n"
                    f"{product.name if product else ''}\n"
                    f"شماره سفارش: #{order.order_number}"
                ),
            )
        except Exception:
            pass

    # به‌روزرسانی گزارش کانال با وضعیت نهایی «تکمیل شد» (بخش ۳۳ سند)
    if report_enabled and product:
        try:
            await callback.bot.send_message(
                chat_id=settings.report_channel_id,
                text=build_order_report_text(order, product.name),
            )
        except Exception:
            pass
