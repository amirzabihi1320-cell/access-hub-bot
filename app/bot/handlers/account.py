from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app.database.base import get_session
from app.services.user_service import UserService

router = Router(name="account")


def _back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:home")]]
    )


@router.callback_query(F.data == "menu:account")
async def handle_account(callback: CallbackQuery) -> None:
    async with get_session() as session:
        user = await UserService(session).get_or_create(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )

    name = user.first_name or "کاربر"
    username = f"@{user.username}" if user.username else "—"

    text = (
        f"👤 <b>حساب من</b>\n\n"
        f"نام:\n{name}\n\n"
        f"Username:\n{username}\n\n"
        f"موجودی:\n{user.wallet.balance:,} تومان\n\n"
        f"تعداد سفارش:\n{user.total_purchases}\n\n"
        f"مجموع خرید:\n{user.total_spent:,} تومان\n\n"
        f"سطح:\n{user.vip_level}\n\n"
        f"Referral:\n{user.referral_code}"
    )
    await callback.message.edit_text(text, reply_markup=_back_keyboard())
    await callback.answer()
