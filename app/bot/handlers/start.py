from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.membership import membership_keyboard
from app.bot.keyboards.reply_menu import main_reply_keyboard
from app.database.base import get_session
from app.services.membership_service import MembershipService
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
        requirement = await settings_service.get("membership_requirement", "DISABLED")
        required_channels = await MembershipService(session).get_active_channels()

        is_member = True
        if requirement in ("ALL", "BOT_USE_ONLY") and required_channels:
            is_member = await MembershipService(session).is_user_member_of_all(
                message.bot, message.from_user.id
            )

    try:
        welcome_text = welcome_text.format(shop_name=shop_name)
    except (KeyError, IndexError):
        pass

    text = f"🌐 <b>{shop_name}</b>\n\n{welcome_text}" if welcome_text else f"🌐 <b>{shop_name}</b>"

    if requirement in ("ALL", "BOT_USE_ONLY") and required_channels and not is_member:
        await message.answer(
            text + "\n\n📢 برای ادامه ابتدا در کانال‌های زیر عضو شوید:",
            reply_markup=membership_keyboard(required_channels),
        )
        return

    await message.answer(text, reply_markup=main_reply_keyboard())
