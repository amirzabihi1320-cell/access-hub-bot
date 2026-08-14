"""
نمایش «📦 سفارش‌های من» برای کاربر و دکمه‌ی «✅ تحویل شد» برای ادمین
(بخش ۱۵ و ۱۸ سند). ساخت/پرداخت سفارش خودش در handlers/shop.py انجام
می‌شود؛ اینجا فقط نمایش تاریخچه و تکمیل تحویل دستی است.
"""
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.base import get_session
from app.models.product import Product
from app.models.user import User
from app.services.order_service import OrderAlreadyProcessedError, OrderService, build_order_report_text
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

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
