"""
اگر ادمین کاربری را مسدود کرده باشد (User.is_blocked)، این Middleware
جلوی همه‌ی تعامل‌های او با ربات (به‌جز خودِ ادمین‌ها) را می‌گیرد.
مثل Middlewareهای دیگر، فقط روی چت خصوصی اعمال می‌شود تا در گروه/سوپرگروه
باعث اسپم پیام «مسدود هستید» برای کل گروه نشود.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from sqlalchemy import select

from app.config.settings import get_settings
from app.database.base import get_session
from app.models.user import User

settings = get_settings()

BLOCKED_TEXT = "⛔️ دسترسی شما به ربات توسط ادمین مسدود شده است."


class BlockedUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        message: Message | None = event.message
        callback: CallbackQuery | None = event.callback_query

        chat = (message.chat if message else None) or (callback.message.chat if callback and callback.message else None)
        if chat and chat.type != "private":
            return await handler(event, data)

        user = data.get("event_from_user")
        if not user or user.id in settings.admin_ids:
            return await handler(event, data)

        async with get_session() as session:
            db_user = await session.scalar(select(User).where(User.telegram_id == user.id))

        if db_user and db_user.is_blocked:
            if callback:
                try:
                    await callback.answer(BLOCKED_TEXT, show_alert=True)
                except Exception:
                    pass
            elif message:
                try:
                    await message.answer(BLOCKED_TEXT)
                except Exception:
                    pass
            return None

        return await handler(event, data)
