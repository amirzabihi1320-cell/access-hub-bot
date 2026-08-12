from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import InventoryCodeStatus
from app.database.base import Base


class InventoryCode(Base):
    """کدهای از پیش بارگذاری‌شده برای محصولات نوع CODE (مثل گیفت‌کارت)."""

    __tablename__ = "inventory_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)

    code: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=InventoryCodeStatus.AVAILABLE.value
    )
    assigned_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
