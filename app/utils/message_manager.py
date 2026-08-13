"""
Message Manager (بخش ۴ و ۴۲ سند پروژه).

مسئول این است که چت ربات شلوغ نشود: هر بار که کاربر وارد یک مرحله‌ی
جدید می‌شود، پیام(های) TEMPORARY مرحله‌ی قبل که با همین ابزار ارسال
شده‌اند، حذف می‌شوند. دسته‌های IMPORTANT / ORDER / PAYMENT / DELIVERY /
SYSTEM هرگز به‌صورت خودکار حذف نمی‌شوند (رسید، تأیید سفارش، نتیجه‌ی
تراکنش و ...).

آیدی پیام‌های TEMPORARY داخل داده‌ی FSMContext کاربر نگه‌داری می‌شود،
پس با ری‌استارت ربات هم چیزی خراب نمی‌شود (فقط اگر Storage از نوع
MemoryStorage باشد و پروسه ری‌استارت شود، لیست خالی می‌شود که بی‌خطر
است - در بدترین حالت یکی دو پیام قدیمی پاک نمی‌شوند).
"""
from __future__ import annotations

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message

from app.core.enums import MessageCategory

_TEMP_KEY = "temp_message_ids"

# دسته‌هایی که هرگز به‌صورت خودکار حذف نمی‌شوند.
_PROTECTED = {
    MessageCategory.IMPORTANT,
    MessageCategory.ORDER,
    MessageCategory.PAYMENT,
    MessageCategory.DELIVERY,
    MessageCategory.SYSTEM,
}


class MessageManager:
    def __init__(self, bot: Bot, chat_id: int, state: FSMContext):
        self.bot = bot
        self.chat_id = chat_id
        self.state = state

    async def cleanup_temp(self) -> None:
        """پیام‌های TEMPORARY ثبت‌شده‌ی قبلی همین کاربر را حذف می‌کند."""
        data = await self.state.get_data()
        ids: list[int] = data.get(_TEMP_KEY, [])
        for message_id in ids:
            try:
                await self.bot.delete_message(self.chat_id, message_id)
            except Exception:
                # پیام ممکن است قبلاً حذف شده یا قدیمی‌تر از ۴۸ ساعت باشد؛
                # نباید کل فرآیند را متوقف کند.
                pass
        if ids:
            await self.state.update_data(**{_TEMP_KEY: []})

    async def delete_message_id(self, message_id: int) -> None:
        """حذف مستقیم یک پیام مشخص (مثلاً پیامی که کاربر تایپ کرده)."""
        try:
            await self.bot.delete_message(self.chat_id, message_id)
        except Exception:
            pass

    async def send(
        self,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        category: MessageCategory = MessageCategory.TEMPORARY,
        **kwargs,
    ) -> Message:
        """
        پیام جدید ارسال می‌کند. اگر دسته TEMPORARY باشد، ابتدا پیام‌های
        TEMPORARY قبلی پاک و آیدی پیام جدید جایگزین می‌شود؛ در نتیجه در هر
        لحظه حداکثر یک پیام TEMPORARY برای این کاربر در چت باقی می‌ماند.
        """
        if category == MessageCategory.TEMPORARY:
            await self.cleanup_temp()

        message = await self.bot.send_message(self.chat_id, text, reply_markup=reply_markup, **kwargs)

        if category == MessageCategory.TEMPORARY:
            await self.state.update_data(**{_TEMP_KEY: [message.message_id]})

        return message
