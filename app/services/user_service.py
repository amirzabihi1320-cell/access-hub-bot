import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.wallet import Wallet
from app.services.game_service import TokenService
from app.services.settings_service import SettingsService


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

    async def award_start_bonuses(self, user: User) -> dict:
        """
        پرداخت پاداش‌های یک‌بارمصرف مرتبط با /start:
        ۱) پاداش عضویت به خودِ کاربر (اگر join_bonus_enabled فعال باشد).
        ۲) پاداش دعوت دوست به معرفِ او (اگر referral_invite_bonus_enabled فعال باشد).

        این متد باید فقط زمانی صدا زده شود که عضویت کاربر در کانال‌های
        اجباری قطعاً تأیید شده باشد (یعنی همان لحظه‌ای که پیام خوش‌آمد
        نهایی نمایش داده می‌شود)، نه در هر بار /start.

        هر دو پاداش دقیقاً یک‌بار برای هر کاربر پرداخت می‌شوند (با پرچم‌های
        join_bonus_claimed / referral_bonus_paid روی خودِ کاربر). اگر ادمین
        این پاداش‌ها را بعداً فعال کند، کاربرانی که هنوز پاداش نگرفته‌اند با
        /start زدنِ دوباره می‌توانند دریافتش کنند؛ برای همین پرچم فقط در
        لحظه‌ی پرداخت واقعی True می‌شود، نه در حالت غیرفعال.

        خروجی برای نمایش پیام مناسب به کاربر/معرف استفاده می‌شود؛ مقدار
        صفر یعنی چیزی پرداخت نشده (چه به‌خاطر غیرفعال بودن، چه چون قبلاً
        پرداخت شده است).
        """
        result: dict = {"join_bonus": 0, "referrer_telegram_id": None, "referral_bonus": 0}
        settings_service = SettingsService(self.session)
        token_service = TokenService(self.session)

        if not user.join_bonus_claimed:
            if await settings_service.is_join_bonus_enabled():
                try:
                    amount = int(await settings_service.get("join_bonus_amount", "50"))
                except (TypeError, ValueError):
                    amount = 0
                if amount > 0:
                    await token_service.credit(
                        user.id, amount, "join_bonus",
                        reference_id=f"join_bonus:user:{user.id}",
                        description="پاداش عضویت و شروع ربات",
                    )
                    user.join_bonus_claimed = True
                    result["join_bonus"] = amount

        if user.referred_by and not user.referral_bonus_paid:
            if await settings_service.is_referral_invite_bonus_enabled():
                try:
                    amount = int(await settings_service.get("referral_invite_bonus_amount", "50"))
                except (TypeError, ValueError):
                    amount = 0
                if amount > 0:
                    referrer = await self.session.get(User, user.referred_by)
                    if referrer:
                        await token_service.credit(
                            referrer.id, amount, "referral_invite_bonus",
                            reference_id=f"referral-invite:user:{user.id}",
                            description="پاداش دعوت دوست جدید",
                        )
                        user.referral_bonus_paid = True
                        result["referrer_telegram_id"] = referrer.telegram_id
                        result["referral_bonus"] = amount

        await self.session.commit()
        return result

    async def count_referrals(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.referred_by == user_id)
        )
        return result.scalar_one()

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(User))
        return result.scalar_one()
