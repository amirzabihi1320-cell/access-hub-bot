from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import HealthStatus, VPNPanelStatus, VPNPanelType
from app.database.base import Base


class VPNPanel(Base):
    """
    یک پنل VPN متصل (Marzban/Sanaei/...) - بند ۱۴ سند.
    چندین پنل هم‌زمان قابل ثبت است؛ انتخاب پنل مناسب هنگام خرید بر عهده‌ی
    VPNProvisioningService است (بند ۱۵: Smart Panel Selection).
    """
    __tablename__ = "vpn_panels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    panel_type: Mapped[str] = mapped_column(String(32), nullable=False, default=VPNPanelType.MARZBAN.value)

    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    # هرگز خام ذخیره نمی‌شود - همیشه از app.core.crypto.encrypt_secret عبور می‌کند.
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=VPNPanelStatus.ACTIVE.value)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)  # کوچک‌تر = اولویت بالاتر
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = بدون محدودیت اعلامی

    # آخرین نتیجه‌ی Health Check (کش شده تا هر انتخاب پنل، درخواست جدید نزند).
    last_health_status: Mapped[str] = mapped_column(String(16), nullable=False, default=HealthStatus.UNKNOWN.value)
    last_health_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_health_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
