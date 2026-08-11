"""
تمام مقادیر حساس و محیطی از اینجا خوانده می‌شوند.
هیچ Secret نباید Hard-code شود؛ همه چیز از .env می‌آید.
تنظیمات کسب‌وکاری (نام فروشگاه، متن‌ها، شماره کارت و ...) اینجا نیستند
و از جدول `settings` در دیتابیس خوانده می‌شوند (به core/dynamic_settings.py
در فازهای بعد مراجعه کن).
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Bot core ---
    bot_token: str = Field(..., alias="BOT_TOKEN")
    bot_username: str = Field(..., alias="BOT_USERNAME")
    run_mode: Literal["polling", "webhook"] = Field("polling", alias="RUN_MODE")

    # --- Webhook (اختیاری) ---
    webhook_base_url: str | None = Field(None, alias="WEBHOOK_BASE_URL")
    webhook_path: str = Field("/webhook", alias="WEBHOOK_PATH")
    webapp_host: str = Field("0.0.0.0", alias="WEBAPP_HOST")
    webapp_port: int = Field(8080, alias="WEBAPP_PORT")

    # --- Database ---
    database_url: str = Field(..., alias="DATABASE_URL")

    # --- Channels ---
    main_channel_id: str = Field(..., alias="MAIN_CHANNEL_ID")
    report_channel_id: str = Field(..., alias="REPORT_CHANNEL_ID")

    # --- Admins (bootstrap فقط؛ نقش‌های دقیق در دیتابیس مدیریت می‌شوند) ---
    admin_ids_raw: str = Field("", alias="ADMIN_IDS")

    # --- App ---
    environment: Literal["development", "production"] = Field(
        "development", alias="ENVIRONMENT"
    )
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @property
    def admin_ids(self) -> list[int]:
        if not self.admin_ids_raw.strip():
            return []
        return [int(x) for x in self.admin_ids_raw.split(",") if x.strip()]

    @field_validator("database_url")
    @classmethod
    def validate_async_driver(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            # اجبار به درایور async برای جلوگیری از باگ‌های سخت
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
