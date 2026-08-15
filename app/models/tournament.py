"""
سیستم تورنومنت (بخش جدید - مرحله ۷).

مهم: این ماژول هیچ ارتباطی با app/models/game.py و اقتصاد Token ندارد و
منطقاً کاملاً مستقل است. جایزه توسط خودِ ادمین از قبل و به‌صورت ثابت تعیین
می‌شود؛ هرگز از Entry Fee شرکت‌کننده‌های دیگر محاسبه/تأمین نمی‌شود - یعنی
پول یک کاربر هرگز مستقیم یا غیرمستقیم به کاربر دیگر منتقل نمی‌شود. Entry
Fee (در صورت تنظیم) مستقیماً درآمد فروشگاه است، نه بخشی از جایزه.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)

    # معیار رتبه‌بندی: REFERRALS (بیشترین دعوت موفق) یا PURCHASES (بیشترین
    # تعداد سفارش تکمیل‌شده) در بازه‌ی زمانی تورنومنت.
    metric: Mapped[str] = mapped_column(String(16), nullable=False, default="REFERRALS")

    entry_fee: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)  # تومان؛ ۰ = رایگان

    # توضیح آزاد جایزه که به شرکت‌کننده‌ها نمایش داده می‌شود، مثلاً «۱۰۰٪ تخفیف روی خرید بعدی».
    prize_description: Mapped[str] = mapped_column(Text, nullable=False)
    # اگر ادمین بخواهد جایزه را خودکار به‌صورت اعتبار کیف‌پول به برنده واریز شود؛
    # None یعنی جایزه غیرنقدی است و ادمین باید دستی تحویل دهد.
    prize_wallet_credit: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # DRAFT -> ACTIVE -> ENDED -> SETTLED / CANCELLED
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")

    winner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    participants: Mapped[list["TournamentParticipant"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"
    __table_args__ = ()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tournament: Mapped["Tournament"] = relationship(back_populates="participants")
