from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.reply_menu import main_reply_keyboard
from app.database.base import get_session
from app.services.settings_service import SettingsService
from app.services.user_service import UserService

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    async with get_session() as session:
        user_service = UserService(session)
        await user_service.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        settings_service = SettingsService(session)
        shop_name = await settings_service.get("shop_name")
        welcome_text = await settings_service.get("welcome_text") or ""

    try:
        welcome_text = welcome_text.format(shop_name=shop_name)
    except (KeyError, IndexError):
        pass  # اگر ادمین Placeholder نامعتبر وارد کرده باشد، متن خام نمایش داده شود.

    text = f"🌐 <b>{shop_name}</b>\n\n{welcome_text}" if welcome_text else f"🌐 <b>{shop_name}</b>"
    await message.answer(text, reply_markup=main_reply_keyboard())
