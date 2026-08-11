"""
اگر membership_requirement روی ALL یا BOT_USE_ONLY باشد، کاربر قبل از
استفاده از هر بخشی (به‌جز /start و دکمه‌ی بررسی عضویت) باید عضو کانال‌های
اجباری باشد. حالت PURCHASE_ONLY در فاز سفارش (فاز ۴) روی مسیر خرید اعمال
می‌شود، نه اینجا.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from app.bot.keyboards.membership import membership_keyboard
from app.database.base import get_session
from app.services.membership_service import MembershipService
from app.services.settings_service import SettingsService

EXEMPT_CALLBACKS = {"membership:check"}


class MembershipMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        message: Message | None = event.message
        callback: CallbackQuery | None = event.callback_query

        # دستور /start همیشه آزاده تا کاربر بتونه ثبت‌نام کنه
        if message and message.text and message.text.startswith("/start"):
            return await handler(event, data)

        if callback and callback.data in EXEMPT_CALLBACKS:
            return await handler(event, data)

        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        async with get_session() as session:
            requirement = await SettingsService(session).get("membership_requirement", "DISABLED")

            if requirement not in ("ALL", "BOT_USE_ONLY"):
                return await handler(event, data)

            membership_service = MembershipService(session)
            channels = await membership_service.get_active_channels()
            if not channels:
                return await handler(event, data)

            bot = data["bot"]
            is_member = await membership_service.is_user_member_of_all(bot, user.id)

        if is_member:
            return await handler(event, data)

        text = (
            "📢 برای استفاده از Access Hub ابتدا در کانال‌های زیر عضو شوید،"
            " سپس روی «بررسی عضویت» بزنید."
        )
        markup = membership_keyboard(channels)

        if callback:
            await callback.message.answer(text, reply_markup=markup)
            await callback.answer()
        elif message:
            await message.answer(text, reply_markup=markup)

        return None
