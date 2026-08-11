from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.main_menu import main_menu_keyboard
from app.database.base import get_session
from app.services.membership_service import MembershipService

router = Router(name="membership")


@router.callback_query(lambda c: c.data == "membership:check")
async def handle_membership_check(callback: CallbackQuery) -> None:
    async with get_session() as session:
        membership_service = MembershipService(session)
        channels = await membership_service.get_active_channels()
        is_member = await membership_service.is_user_member_of_all(callback.bot, callback.from_user.id)

    if is_member or not channels:
        await callback.message.edit_text(
            "✅ عضویت شما تأیید شد. خوش آمدید!",
        )
        await callback.message.answer("🌐 منوی اصلی:", reply_markup=main_menu_keyboard())
    else:
        await callback.answer("❌ هنوز عضو همه‌ی کانال‌ها نشده‌اید.", show_alert=True)
