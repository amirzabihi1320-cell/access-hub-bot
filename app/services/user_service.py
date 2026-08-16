import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.wallet import Wallet


def _generate_referral_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "AH" + "".join(secrets.choice(alphabet) for _ in range(6))


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        referral_code: str | None = None,
    ) -> User:
        result = await self.session.execute(
            select(User).options(selectinload(User.wallet)).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # به‌روزرسانی اطلاعات نمایشی در صورت تغییر + ثبت آخرین فعالیت
            # (برای آمار «کاربران فعال» در داشبورد ادمین لازم است).
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.last_activity = datetime.now(timezone.utc)
            await self.session.commit()
            return user

        referred_by_id: int | None = None
        if referral_code:
            referrer_result = await self.session.execute(
                select(User).where(User.referral_code == referral_code)
            )
            referrer = referrer_result.scalar_one_or_none()
            # کاربر جدید هنوز رکورد ندارد، پس مقایسه با telegram_id او بی‌معناست؛
            # فقط باید مطمئن شویم معرف با خودِ کاربرِ در حال ساخت یکی نیست.
            if referrer and referrer.telegram_id != telegram_id:
                referred_by_id = referrer.id

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            referral_code=_generate_referral_code(),
            referred_by=referred_by_id,
            last_activity=datetime.now(timezone.utc),
        )
        self.session.add(user)
        await self.session.flush()  # برای گرفتن user.id قبل از commit

        wallet = Wallet(user_id=user.id, balance=0)
        self.session.add(wallet)
        user.wallet = wallet  # ست کردن دستی رابطه تا بعد از بسته‌شدن session قابل خواندن باشه

        await self.session.commit()
        return user

    async def count_referrals(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.referred_by == user_id)
        )
        return result.scalar_one()

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(User))
        return result.scalar_one()
