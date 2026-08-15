from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DepositRequestStatus
from app.database.base import Base


class DepositRequest(Base):
    """
    درخواست شارژ دستی.

    دو نوع درخواست داریم:

    RIAL:
        مبلغ پرداختی به کیف پول ریالی کاربر اضافه می‌شود.

    TOKEN:
        مبلغ پرداختی کارت‌به‌کارت است و پس از تأیید ادمین،
        مقدار token_amount به موجودی Access Token کاربر اضافه می‌شود.

    هر درخواست فقط یک‌بار می‌تواند از حالت PENDING خارج شود.
    """

    __tablename__ = "deposit_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # نوع درخواست:
    # RIAL = شارژ کیف پول ریالی
    # TOKEN = شارژ Access Token
    deposit_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="RIAL",
    )

    # مبلغی که کاربر باید کارت‌به‌کارت کند، به تومان
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # مقدار Token که پس از تأیید به کاربر داده می‌شود.
    # برای درخواست RIAL مقدار آن None است.
    token_amount: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    receipt_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=DepositRequestStatus.PENDING.value,
    )

    reject_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # آیدی عددی تلگرام ادمینی که تصمیم گرفته
    decided_by_admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship()
