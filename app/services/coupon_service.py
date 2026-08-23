"""
کد تخفیف یک‌بارمصرف (Single-use Discount Coupon).

هر کد فقط یک‌بار در کل قابل استفاده است: به محض این‌که یک خرید با آن کد
نهایی شد، is_used=True می‌شود و برای همیشه غیرقابل استفاده می‌ماند. برای
جلوگیری از Race Condition (دو کاربر هم‌زمان یک کد را اعمال کنند)، لحظه‌ی
مصرف نهایی با قفل ردیف (with_for_update) داخل همان تراکنشِ ساخت سفارش
انجام می‌شود؛ نه در لحظه‌ی «اعمال کد» روی صفحه‌ی تأیید سفارش.
"""
import secrets
import string
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discount_coupon import DiscountCoupon


class CouponError(Exception):
    """کد تخفیف نامعتبر، منقضی یا قبلاً مصرف‌شده است."""


class CouponService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def generate_code(length: int = 8) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def get_by_code(self, code: str) -> DiscountCoupon | None:
        code = (code or "").strip().upper()
        if not code:
            return None
        result = await self.session.execute(select(DiscountCoupon).where(DiscountCoupon.code == code))
        return result.scalar_one_or_none()

    def _is_expired(self, coupon: DiscountCoupon) -> bool:
        if not coupon.expires_at:
            return False
        expires = coupon.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires <= datetime.now(timezone.utc)

    async def validate(self, code: str) -> DiscountCoupon:
        """
        فقط برای پیش‌نمایش/محاسبه‌ی قیمت روی صفحه‌ی تأیید سفارش استفاده
        می‌شود؛ مصرف نهایی کد اینجا انجام نمی‌شود (مصرف واقعی توی
        redeem_locked است که داخل تراکنش پرداخت صدا زده می‌شود).
        """
        coupon = await self.get_by_code(code)
        if not coupon:
            raise CouponError("کد تخفیف پیدا نشد.")
        if coupon.is_used:
            raise CouponError("این کد قبلاً استفاده شده است.")
        if self._is_expired(coupon):
            raise CouponError("این کد منقضی شده است.")
        return coupon

    async def redeem_locked(self, coupon_id: int, user_id: int, order_id: int) -> DiscountCoupon:
        """
        باید داخل همان تراکنشی صدا زده شود که سفارش را می‌سازد و پول را
        کسر می‌کند. با قفل ردیف، تضمین می‌کند حتی اگر دو نفر هم‌زمان
        بخواهند از یک کد استفاده کنند، فقط یکی موفق می‌شود.
        """
        result = await self.session.execute(
            select(DiscountCoupon).where(DiscountCoupon.id == coupon_id).with_for_update()
        )
        coupon = result.scalar_one_or_none()
        if not coupon:
            raise CouponError("کد تخفیف پیدا نشد.")
        if coupon.is_used:
            raise CouponError("این کد قبلاً استفاده شده است.")
        if self._is_expired(coupon):
            raise CouponError("این کد منقضی شده است.")

        coupon.is_used = True
        coupon.used_by_user_id = user_id
        coupon.used_order_id = order_id
        coupon.used_at = datetime.now(timezone.utc)
        return coupon

    # ---------- ادمین ----------

    async def create(self, discount_percent: int, admin_id: int, code: str | None = None,
                      expires_at: datetime | None = None) -> DiscountCoupon:
        if discount_percent <= 0 or discount_percent > 90:
            raise CouponError("درصد تخفیف باید بین ۱ تا ۹۰ باشد.")

        final_code = (code or self.generate_code()).strip().upper()
        if await self.get_by_code(final_code):
            raise CouponError("این کد از قبل وجود دارد.")

        coupon = DiscountCoupon(
            code=final_code,
            discount_percent=discount_percent,
            created_by_admin_id=admin_id,
            expires_at=expires_at,
        )
        self.session.add(coupon)
        await self.session.commit()
        await self.session.refresh(coupon)
        return coupon

    async def list_active(self, limit: int = 20) -> list[DiscountCoupon]:
        result = await self.session.execute(
            select(DiscountCoupon)
            .where(DiscountCoupon.is_used.is_(False))
            .order_by(DiscountCoupon.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, coupon_id: int) -> None:
        coupon = await self.session.get(DiscountCoupon, coupon_id)
        if not coupon:
            raise CouponError("کد پیدا نشد.")
        if coupon.is_used:
            raise CouponError("کد مصرف‌شده برای حفظ سابقه قابل حذف نیست.")
        await self.session.delete(coupon)
        await self.session.commit()
