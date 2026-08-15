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
