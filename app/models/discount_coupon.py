from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class DiscountCoupon(Base):
    """
    کد تخفیف یک‌بارمصرف: با یک عدد درصد ساخته می‌شود و به محض اینکه یک نفر
    آن را در تسویه‌حساب اعمال و خرید نهایی را انجام داد، برای همیشه مصرف‌شده
    علامت می‌خورد (is_used=True) و دیگر توسط هیچ‌کس دیگری قابل استفاده نیست.
    فقط روی خرید با کیف‌پول ریالی اعمال می‌شود.
    """

    __tablename__ = "discount_coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)

    is_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    used_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    used_by_user: Mapped["User"] = relationship()
