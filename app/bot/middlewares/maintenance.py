"""
اگر Maintenance Mode فعال باشد، فقط ادمین‌ها اجازه‌ی عبور دارند.
این Middleware باید قبل از تمام Handlerهای غیر-ادمین اجرا شود.
"""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.config.settings import get_settings
from app.database.base import get_session
from app.services.settings_service import SettingsService

settings = get_settings()


class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user and user.id in settings.admin_ids:
            return await handler(event, data)

        # مثل عضویت اجباری: این پیام فقط برای چت خصوصی کاربر با ربات معناداره.
        message_obj = getattr(event, "message", None) or getattr(event, "callback_query", None)
        chat = getattr(message_obj, "chat", None) or getattr(getattr(message_obj, "message", None), "chat", None)
        if chat and chat.type != "private":
            return await handler(event, data)

        async with get_session() as session:
            is_maintenance = await SettingsService(session).is_maintenance_mode()

        if is_maintenance:
            message = getattr(event, "message", None) or getattr(event, "callback_query", None)
            if message:
                target = message if hasattr(message, "answer") else message.message
                if target:
                    await target.answer("🔧 Access Hub در حال بروزرسانی است.")
            return None

        return await handler(event, data)
