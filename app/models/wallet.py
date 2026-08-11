from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import WalletTransactionType
from app.database.base import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)

    # موجودی هرگز مستقیم دستکاری نمی‌شود؛ فقط از طریق wallet_service
    # که هر تغییر را در WalletTransaction ثبت می‌کند (اصل ۵۸: Financial Integrity)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="wallet")


class WalletTransaction(Base):
    """
    Ledger کامل - هیچ رکوردی هرگز Delete یا Edit نمی‌شود.
    برای Refund، تراکنش جدید ثبت می‌شود نه ویرایش قدیمی.
    """
    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # می‌تواند منفی باشد
    balance_before: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)

    type: Mapped[WalletTransactionType] = mapped_column(String(32), nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admin_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
