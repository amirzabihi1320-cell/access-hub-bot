import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CryptoCurrency, CryptoDepositStatus, PaymentProviderType
from app.database.base import Base


def _generate_order_id() -> str:
    # شناسه‌ی داخلی یکتا - مستقل از provider_order_id بیرونی (بند ۵ سند:
    # Unique Payment ID جدا از Unique Order ID).
    return f"CDP-{uuid.uuid4().hex[:20]}"


class CryptoDepositOrder(Base):
    """
    یک سفارش واریز TRX از طریق یک Payment Provider خارجی (فعلاً Tronado) -
    بندهای ۴ و ۵ سند. این رکورد از لحظه‌ی ایجاد تا Verify نهایی، وضعیت را
    دنبال می‌کند و پایه‌ی Idempotency/Fraud Protection است.
    """
    __tablename__ = "crypto_deposit_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # شناسه‌ی داخلی یکتا - در پیام‌های کاربر/ادمین نمایش داده می‌شود.
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, default=_generate_order_id)
    # کلید Idempotency جدا - جلوگیری از ایجاد دوبار سفارش برای یک درخواست
    # (مثلاً Double-tap کاربر روی دکمه‌ی پرداخت).
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    provider_type: Mapped[str] = mapped_column(String(32), nullable=False, default=PaymentProviderType.TRONADO.value)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default=CryptoCurrency.TRX.value)

    toman_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crypto_amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)

    # شناسه/آدرس/رفرنسی که سمت Provider برمی‌گرداند - قبل از دریافت پاسخ Provider خالی است.
    provider_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expected_wallet_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payment_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CryptoDepositStatus.CREATED.value)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()
