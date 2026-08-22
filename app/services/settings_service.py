"""
لایه‌ی سرویس برای خواندن/نوشتن تنظیمات از جدول settings.
این سرویس تنها راه رسمی برای دسترسی به مقادیر داینامیک (نام فروشگاه،
شماره کارت، maintenance_mode و ...) است. Handlerها هرگز مستقیم به
Repository دسترسی ندارند.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting

# مقادیر پیش‌فرض برای اولین اجرا (Seed) - فقط fallback، نه Hard-code منطق تجاری
DEFAULT_SETTINGS: dict[str, str] = {
    "maintenance_mode": "false",
    "payment_info": "",
    "welcome_text": "خوش آمدید.\nدسترسی آسان به سرویس‌ها و محصولات دیجیتال.",
    "order_report_enabled": "true",
    "token_transfer_fee_percent": "10",
    # درصدی از مبلغ خرید که به‌عنوان پاداش (Cashback) به کیف‌پول معرف بازمی‌گردد؛ ۰ = غیرفعال.
    "referral_cashback_percent": "0",
    # آیدی محصولی که به‌عنوان «پیشنهاد ویژه» بالای فروشگاه پین می‌شود؛ خالی = چیزی پین نیست.
    "featured_product_id": "",
    # چیدمان دکمه‌های فروشگاه: 1=تمام‌عرض، 2=دو ستون
    "shop_category_button_columns": "1",
    "shop_product_button_columns": "1",
    # قیمت هر Token هنگام خرید Token
    "token_purchase_price": "40",

    # پاداش عضویت: وقتی فعال باشد، هر کاربری که /start بزند و در همه‌ی
    # کانال‌های اجباری عضو شود، یک‌بار مقدار زیر را به‌صورت Token هدیه می‌گیرد.
    "join_bonus_enabled": "false",
    "join_bonus_amount": "50",

    # پاداش رفرال - بخش کش‌بک: درصدی از هر خرید دوستِ دعوت‌شده به معرف برمی‌گردد.
    "referral_cashback_enabled": "true",
    # پاداش رفرال - بخش دعوت: مبلغ ثابت Token که یک‌بار، به‌ازای هر دوستی که
    # با لینک دعوت وارد و در کانال‌ها عضو شود، به معرف تعلق می‌گیرد.
    "referral_invite_bonus_enabled": "false",
    "referral_invite_bonus_amount": "50",

    # چک-این روزانه: هر کاربر یک‌بار در روز با زدن دکمه‌ی مربوطه Token می‌گیرد.
    "daily_checkin_enabled": "false",
    "daily_checkin_amount": "10",

    # پاداش هفتگی لیدربرد بازی (Reaction Battle): هر هفته به‌صورت خودکار به
    # سه نفر برتر جدول امتیازات هفتگی (بر اساس تعداد برد) Token پرداخت می‌شود.
    "weekly_leaderboard_reward_enabled": "false",
    "weekly_leaderboard_reward_top1": "100",
    "weekly_leaderboard_reward_top2": "60",
    "weekly_leaderboard_reward_top3": "30",
    # آخرین هفته‌ای (مثلاً 2026-W34) که پاداش لیدربرد پرداخت شده؛ داخلی است
    # و در پنل تنظیمات برای ویرایش دستی نمایش داده نمی‌شود.
    "weekly_leaderboard_last_payout": "",
}



class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: str | None = None) -> str | None:
        result = await self.session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        return default if default is not None else DEFAULT_SETTINGS.get(key)

    async def set(self, key: str, value: str, description: str | None = None) -> None:
        result = await self.session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value, description=description)
            self.session.add(setting)
        await self.session.commit()

    async def is_maintenance_mode(self) -> bool:
        value = await self.get("maintenance_mode", "false")
        return value.lower() == "true"

    async def is_order_report_enabled(self) -> bool:
        value = await self.get("order_report_enabled", "true")
        return value.lower() == "true"

    async def toggle_order_report(self) -> bool:
        """وضعیت فعلی را برعکس می‌کند و مقدار جدید را برمی‌گرداند."""
        current = await self.is_order_report_enabled()
        new_value = "false" if current else "true"
        await self.set("order_report_enabled", new_value)
        return new_value == "true"

    # ---------- پاداش عضویت و رفرال ----------

    async def _is_flag_enabled(self, key: str, default: str = "false") -> bool:
        value = await self.get(key, default)
        return (value or "").strip().lower() == "true"

    async def _toggle_flag(self, key: str, default: str = "false") -> bool:
        current = await self._is_flag_enabled(key, default)
        new_value = "false" if current else "true"
        await self.set(key, new_value)
        return new_value == "true"

    async def is_join_bonus_enabled(self) -> bool:
        return await self._is_flag_enabled("join_bonus_enabled", "false")

    async def toggle_join_bonus(self) -> bool:
        return await self._toggle_flag("join_bonus_enabled", "false")

    async def is_referral_cashback_enabled(self) -> bool:
        return await self._is_flag_enabled("referral_cashback_enabled", "true")

    async def toggle_referral_cashback(self) -> bool:
        return await self._toggle_flag("referral_cashback_enabled", "true")

    async def is_referral_invite_bonus_enabled(self) -> bool:
        return await self._is_flag_enabled("referral_invite_bonus_enabled", "false")

    async def toggle_referral_invite_bonus(self) -> bool:
        return await self._toggle_flag("referral_invite_bonus_enabled", "false")

    # ---------- چک-این روزانه ----------

    async def is_daily_checkin_enabled(self) -> bool:
        return await self._is_flag_enabled("daily_checkin_enabled", "false")

    async def toggle_daily_checkin(self) -> bool:
        return await self._toggle_flag("daily_checkin_enabled", "false")

    # ---------- پاداش هفتگی لیدربرد ----------

    async def is_weekly_leaderboard_reward_enabled(self) -> bool:
        return await self._is_flag_enabled("weekly_leaderboard_reward_enabled", "false")

    async def toggle_weekly_leaderboard_reward(self) -> bool:
        return await self._toggle_flag("weekly_leaderboard_reward_enabled", "false")
