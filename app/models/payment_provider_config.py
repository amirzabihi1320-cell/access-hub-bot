from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import HealthStatus, PaymentProviderStatus, PaymentProviderType
from app.database.base import Base


class PaymentProviderConfig(Base):
    """
    تنظیمات یک Payment Provider خارجی (Tronado و آینده: TON/دیگران) - بند ۲ سند.

    دقیقاً هم‌الگو با VPNPanel: Credential هرگز Hard-code یا Plain-text
    ذخیره نمی‌شود (password_encrypted -> اینجا api_key_encrypted)، و از
    Admin Panel قابل مدیریت است (API Key / API URL / Status / Auto Verify /
    Webhook URL / Test Connection).
    """
    __tablename__ = "payment_provider_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    provider_type: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)

    api_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # هرگز خام ذخیره نمی‌شود - از app.core.crypto.encrypt_secret عبور می‌کند.
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PaymentProviderStatus.DISABLED.value
    )
    auto_verify: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    webhook_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # آخرین نتیجه‌ی Test Connection / Health Check (کش شده - بند ۲۰).
    last_health_status: Mapped[str] = mapped_column(String(16), nullable=False, default=HealthStatus.UNKNOWN.value)
    last_health_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_health_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def is_enabled(self) -> bool:
        return self.status == PaymentProviderStatus.ACTIVE.value

    @staticmethod
    def default_for(provider_type: PaymentProviderType) -> "PaymentProviderConfig":
        return PaymentProviderConfig(provider_type=provider_type.value)
