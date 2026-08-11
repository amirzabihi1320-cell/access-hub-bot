from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Setting(Base):
    """
    سیستم Key-Value برای تمام تنظیمات قابل تغییر از /admin
    مثل shop_name، maintenance_mode، card_number و ...
    هیچ‌کدام نباید در کد Hard-code شوند.
    """
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TextTemplate(Base):
    """
    متن‌های قابل ویرایش ربات (welcome, help, error و ...)
    با پشتیبانی از placeholder مثل {name}, {order_id}
    """
    __tablename__ = "text_templates"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
