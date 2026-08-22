"""
محدودکننده‌ی ساده‌ی نرخ درخواست (Anti-Flood): جلوی اسپم سریع پیام/کلیک هر
کاربر را می‌گیرد تا هم بار روی دیتابیس کم شود و هم امکان سوءاستفاده (مثلاً
تلاش مکرر برای چک-این یا ساخت بازی) محدود شود.

عمداً یک ساختار درون‌حافظه‌ای ساده است (نه Redis) چون ربات روی یک پردازه
اجرا می‌شود؛ اگر بعداً چندنسخه‌ای (Multi-instance) شد باید به Redis منتقل شود.
"""
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject, Update

from app.config.settings import get_settings

settings = get_settings()

# حداقل فاصله‌ی زمانی مجاز (ثانیه) بین دو اکشن متوالی یک کاربر عادی.
MIN_INTERVAL_SECONDS = 0.6

_last_action: dict[int, float] = {}


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user or user.id in settings.admin_ids:
            return await handler(event, data)

        now = time.monotonic()
        last = _last_action.get(user.id, 0.0)
        if now - last < MIN_INTERVAL_SECONDS:
            callback: CallbackQuery | None = event.callback_query
            if callback:
                try:
                    await callback.answer()
                except Exception:
                    pass
            return None

        _last_action[user.id] = now
        return await handler(event, data)
