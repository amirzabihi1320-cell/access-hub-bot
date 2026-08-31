from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PaymentTransaction(Base):
    """Auditable external payment record.

    A unique payment_id makes provider callbacks idempotent. The raw provider
    payload is retained for diagnostics, but secrets/signatures are never
    persisted here.
    """

    __tablename__ = "payment_transactions"
    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_payment_transactions_payment_id"),
        UniqueConstraint("provider_reference", name="uq_payment_transactions_provider_reference"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    payment_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, default="WALLET_DEPOSIT")
    amount_toman: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_toman: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    asset: Mapped[str] = mapped_column(String(16), nullable=False, default="TRX")
    asset_amount: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payment_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
