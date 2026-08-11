from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main_menu import main_menu_keyboard
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

    text = (
        f"🌐 <b>{shop_name}</b>\n\n"
        "خوش آمدید به Access Hub.\n"
        "دسترسی آسان به سرویس‌ها و محصولات دیجیتال."
    )
    await message.answer(text, reply_markup=main_menu_keyboard())
