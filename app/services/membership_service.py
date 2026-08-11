"""
بررسی عضویت کاربر در کانال‌های اجباری.
طبق تنظیم settings.membership_requirement تعیین می‌شود که آیا
اصلاً بررسی لازم است یا نه (ALL / PURCHASE_ONLY / BOT_USE_ONLY / DISABLED).
فعلاً در فاز ۱ فقط منطق ALL و BOT_USE_ONLY در Middleware استفاده می‌شود؛
PURCHASE_ONLY در فاز سفارش (فاز ۴) اعمال خواهد شد.
"""
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.required_channel import RequiredChannel

ACTIVE_MEMBER_STATUSES = {"member", "administrator", "creator"}


class MembershipService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_channels(self) -> list[RequiredChannel]:
        result = await self.session.execute(
            select(RequiredChannel)
            .where(RequiredChannel.is_active.is_(True))
            .order_by(RequiredChannel.sort_order)
        )
        return list(result.scalars().all())

    async def is_user_member_of_all(self, bot: Bot, user_id: int) -> bool:
        channels = await self.get_active_channels()
        if not channels:
            return True

        for channel in channels:
            chat_id = channel.username if channel.username.startswith("@") else f"@{channel.username}"
            try:
                member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            except TelegramBadRequest:
                # اگه ربات ادمین کانال نباشه یا کانال در دسترس نباشه، برای امنیت
                # فرض می‌کنیم عضو نیست تا کاربر مجبور به بررسی دستی بشه.
                return False

            if member.status not in ACTIVE_MEMBER_STATUSES:
                return False

        return True
