from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image: Mapped[str | None] = mapped_column(String(255), nullable=True)  # file_id تلگرام یا URL

    # FIXED یا VARIABLE_QUANTITY (بقیه انواع در فازهای بعد اضافه می‌شوند)
    product_type: Mapped[str] = mapped_column(String(32), nullable=False, default="FIXED")

    # برای محصول FIXED
    fixed_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # برای محصول VARIABLE_QUANTITY
    unit_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    min_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # تعداد دکمه در هر ردیف:
    # 1 = تمام‌عرض
    # 2 = دو دکمه کنار هم
    button_columns: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # استایل رنگی دکمه فروشگاه: primary / success / danger
    button_style: Mapped[str] = mapped_column(String(16), nullable=False, default="primary")

    # قیمت اختیاری محصول با Access Token. برای FIXED قیمت کل محصول
    # و برای VARIABLE_QUANTITY قیمت هر واحد است. مقدار None یعنی خرید Token فعال نیست.
    token_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # تخفیف زمان‌دار (اختیاری). وقتی discount_percent ست شده و هنوز به
    # discount_expires_at نرسیده باشیم، قیمت نمایشی/نهایی تخفیف می‌خورد.
    discount_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped["Category"] = relationship(back_populates="products")
