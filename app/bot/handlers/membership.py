from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.reply_menu import main_reply_keyboard
from app.database.base import get_session
from app.services.membership_service import MembershipService
from app.services.user_service import UserService

router = Router(name="membership")


@router.callback_query(lambda c: c.data == "membership:check")
async def handle_membership_check(callback: CallbackQuery) -> None:
    bonus_result: dict | None = None
    async with get_session() as session:
        membership_service = MembershipService(session)
        channels = await membership_service.get_active_channels()
        is_member = await membership_service.is_user_member_of_all(callback.bot, callback.from_user.id)

        if is_member or not channels:
            user_service = UserService(session)
            user = await user_service.get_or_create(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
            )
            bonus_result = await user_service.award_start_bonuses(user)

    if is_member or not channels:
        await callback.message.edit_text("✅ عضویت شما تأیید شد.")
        text = "🌐 <b>Access Hub</b>"
        if bonus_result and bonus_result.get("join_bonus"):
            text += f"\n\n🎁 <b>{bonus_result['join_bonus']:,} Token</b> پاداش عضویت به شما تعلق گرفت!"
        await callback.message.answer(text, reply_markup=main_reply_keyboard())

        if bonus_result and bonus_result.get("referral_bonus") and bonus_result.get("referrer_telegram_id"):
            try:
                await callback.bot.send_message(
                    chat_id=bonus_result["referrer_telegram_id"],
                    text=(
                        f"🤝 یکی از دوستانتان با لینک دعوت شما به ربات پیوست و عضو شد!\n"
                        f"🎁 <b>{bonus_result['referral_bonus']:,} Token</b> به موجودی شما اضافه شد."
                    ),
                )
            except Exception:
                pass
    else:
        await callback.answer("❌ هنوز عضو همه‌ی کانال‌ها نشده‌اید.", show_alert=True)
