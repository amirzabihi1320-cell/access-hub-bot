from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CryptoCurrency, CryptoWalletTxType
from app.database.base import Base

# دقت اعشاری کافی برای TRX/TON (هر دو ۶ رقم اعشار دارند در اکثر اکسپلورر/کیف‌پول‌ها).
_CRYPTO_PRECISION = 24
_CRYPTO_SCALE = 8


class CryptoWallet(Base):
    """
    کیف‌پول ارز دیجیتال کاربر - جدا از Wallet تومانی/Access Token (بند ۳ سند).
    هر کاربر برای هر Currency (TRX, TON, ...) یک ردیف مستقل دارد تا هر
    Ledger کاملاً جدا بماند.
    """
    __tablename__ = "crypto_wallets"
    __table_args__ = (UniqueConstraint("user_id", "currency", name="uq_crypto_wallet_user_currency"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default=CryptoCurrency.TRX.value)

    # موجودی هرگز مستقیم دستکاری نمی‌شود؛ فقط از طریق crypto_wallet_service
    # که هر تغییر را در CryptoWalletTransaction ثبت می‌کند (اصل Financial Integrity
    # - همان اصلی که Wallet تومانی از آن پیروی می‌کند).
    balance: Mapped[Decimal] = mapped_column(
        Numeric(_CRYPTO_PRECISION, _CRYPTO_SCALE), nullable=False, default=Decimal("0")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship()


class CryptoWalletTransaction(Base):
    """
    Ledger کامل کیف‌پول ارز دیجیتال - هیچ رکوردی هرگز Delete/Edit نمی‌شود
    (همان قانون WalletTransaction تومانی). reference_id برای Idempotency
    استفاده می‌شود: قبل از هر Credit، این جدول باید برای همان reference_id
    چک شود تا Callback تکراری باعث شارژ دوباره نشود (بند ۵ سند).
    """
    __tablename__ = "crypto_wallet_transactions"
    __table_args__ = (
        UniqueConstraint("reference_id", "type", name="uq_crypto_wallet_tx_reference"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(_CRYPTO_PRECISION, _CRYPTO_SCALE), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(_CRYPTO_PRECISION, _CRYPTO_SCALE), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(_CRYPTO_PRECISION, _CRYPTO_SCALE), nullable=False)

    type: Mapped[CryptoWalletTxType] = mapped_column(String(32), nullable=False)
    # شناسه‌ی یکتای منبع تراکنش (مثلاً order_id سفارش واریز Tronado) -
    # پایه‌ی Idempotency طبق UniqueConstraint بالا.
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
