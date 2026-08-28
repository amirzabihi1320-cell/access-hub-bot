from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import VPNServiceStatus
from app.database.base import Base


class VPNService(Base):
    """
    یک سرویس VPN تحویل‌داده‌شده به کاربر (بند ۱۸: My Services) - نتیجه‌ی
    نهایی Flow بند ۱۶ (Automatic VPN Purchase). فعلاً مستقل از Order Engine
    قابل ساخت است (برای تست/ساخت دستی از پنل ادمین)؛ اتصال کامل به
    Order Engine خودکار در فاز Payment→VPN Automation انجام می‌شود.
    """
    __tablename__ = "vpn_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("vpn_panels.id"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    # محصول اصلی که این سرویس از آن ساخته شده - برای Auto-Renew (بند ۱۹) لازم
    # است تا قیمت/حجم/مدت فعلیِ محصول در لحظه‌ی تمدید (نه لحظه‌ی خرید اول)
    # خوانده شود. می‌تواند None باشد (سرویس ساخته‌شده‌ی دستی توسط ادمین).
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)

    # نام کاربری روی خودِ پنل (ممکن است با پیشوند یکتا از username تلگرام متفاوت باشد).
    remote_username: Mapped[str] = mapped_column(String(128), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=VPNServiceStatus.ACTIVE.value)

    data_limit_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    used_traffic_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    subscription_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    config_links: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded list[str]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship()
    panel: Mapped["VPNPanel"] = relationship()
