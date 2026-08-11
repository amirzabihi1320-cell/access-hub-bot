from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.database.base import get_session
from app.models.user import User
from app.services.user_service import UserService

router = Router(name="account")
settings = get_settings()


def _account_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎁 دعوت دوستان", callback_data="account:referral")]]
    )


def _referral_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="account:view")]]
    )


def _account_text(user: User) -> str:
    name = user.first_name or "کاربر"
    username = f"@{user.username}" if user.username else "—"
    return (
        f"👤 <b>حساب من</b>\n\n"
        f"نام:\n{name}\n\n"
        f"Username:\n{username}\n\n"
        f"موجودی:\n{user.wallet.balance:,} تومان\n\n"
        f"تعداد سفارش:\n{user.total_purchases}\n\n"
        f"مجموع خرید:\n{user.total_spent:,} تومان\n\n"
        f"سطح:\n{user.vip_level}"
    )


async def build_account_view(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> tuple[str, InlineKeyboardMarkup]:
    """خروجی مشترک بین ورودی اولیه (از منوی ثابت) و بازگشت از صفحه رفرال."""
    user = await UserService(session).get_or_create(telegram_id, username, first_name, last_name)
    return _account_text(user), _account_keyboard()


@router.callback_query(F.data == "account:view")
async def handle_account_view(callback: CallbackQuery) -> None:
    async with get_session() as session:
        text, keyboard = await build_account_view(
            session,
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name,
        )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "account:referral")
async def handle_referral(callback: CallbackQuery) -> None:
    async with get_session() as session:
        user_service = UserService(session)
        user = await user_service.get_or_create(
            callback.from_user.id,
            callback.from_user.username,
            callback.from_user.first_name,
            callback.from_user.last_name,
        )
        referrals_count = await user_service.count_referrals(user.id)

    invite_link = f"https://t.me/{settings.bot_username}?start=ref_{user.referral_code}"
    text = (
        f"🎁 <b>دعوت دوستان</b>\n\n"
        f"کد معرف شما:\n<code>{user.referral_code}</code>\n\n"
        f"لینک دعوت:\n{invite_link}\n\n"
        f"تعداد افراد معرفی‌شده:\n{referrals_count}"
    )
    await callback.message.edit_text(text, reply_markup=_referral_keyboard())
    await callback.answer()
