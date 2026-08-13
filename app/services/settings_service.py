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
    "shop_name": "Access Hub | مارکت دیجیتال",
    "maintenance_mode": "false",
    "card_number": "",
    "card_holder_name": "",
    "payment_description": "",
    "membership_requirement": "DISABLED",  # ALL / PURCHASE_ONLY / BOT_USE_ONLY / DISABLED
    # متن خوشامدگویی صفحه‌ی اصلی (بخش ۵ و ۳۱ سند). از {shop_name} پشتیبانی می‌کند.
    "welcome_text": "خوش آمدید به {shop_name}.\nدسترسی آسان به سرویس‌ها و محصولات دیجیتال.",
    # تعداد دکمه در هر ردیف برای لیست دسته‌بندی‌ها/محصولات (بخش ۴۱ سند - Navigation).
    # عدد ۱ تا ۳؛ برای متن‌های نسبتاً بزرگ عدد ۱ پیشنهاد می‌شود.
    "shop_buttons_per_row": "1",
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
