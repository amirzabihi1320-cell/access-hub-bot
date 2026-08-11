from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DepositRequestStatus
from app.database.base import Base


class DepositRequest(Base):
    """
    درخواست شارژ دستی کیف پول.

    تا وقتی وضعیت PENDING است هیچ تغییری روی Wallet.balance اعمال نمی‌شود.
    فقط بعد از approve() در DepositService، از طریق WalletService.credit
    موجودی افزایش پیدا می‌کند (اصل ۵۸: هیچ Balance بدون Ledger تغییر نکند).
    هر رکورد فقط یک‌بار می‌تواند از PENDING خارج شود (اصل ۹: Duplicate
    approval/rejection غیرممکن).
    """

    __tablename__ = "deposit_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    receipt_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DepositRequestStatus.PENDING.value
    )
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # آیدی عددی تلگرام ادمینی که تصمیم گرفته (نه FK به جدول admins که در فاز ۵ می‌آید)
    decided_by_admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
