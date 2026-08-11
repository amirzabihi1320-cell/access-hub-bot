from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.user import User
from app.services.user_service import UserService

settings = get_settings()


def _account_text(user: User) -> str:
    username = f"@{user.username}" if user.username else "—"
    return (
        f"👤 <b>{user.first_name or 'کاربر'}</b> ({username})\n\n"
        f"💰 موجودی: {user.wallet.balance:,} تومان\n"
        f"🛍 سفارش‌ها: {user.total_purchases} | مجموع خرید: {user.total_spent:,} تومان\n"
        f"⭐ سطح: {user.vip_level}"
    )


async def build_account_view(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> str:
    user = await UserService(session).get_or_create(telegram_id, username, first_name, last_name)
    return _account_text(user)


async def build_referral_view(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> str:
    user_service = UserService(session)
    user = await user_service.get_or_create(telegram_id, username, first_name, last_name)
    referrals_count = await user_service.count_referrals(user.id)

    invite_link = f"https://t.me/{settings.bot_username}?start=ref_{user.referral_code}"
    return (
        f"🤝 <b>دعوت از دوستان</b>\n\n"
        f"کد معرف شما:\n<code>{user.referral_code}</code>\n\n"
        f"لینک دعوت:\n{invite_link}\n\n"
        f"تعداد افراد معرفی‌شده:\n{referrals_count}"
    )
