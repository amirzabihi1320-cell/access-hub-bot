from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="fa")

    total_purchases: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[int] = mapped_column(BigInteger, default=0)  # تومان (ریال در آینده قابل تغییر)

    # Access Token: مستقل از کیف پول فروشگاه
    token_balance: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_tokens_purchased: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_tokens_spent: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_tokens_won: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_game_fees_paid: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    referral_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    referred_by: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # FK به users.id در فاز Referral کامل می‌شود

    vip_level: Mapped[str] = mapped_column(String(32), default="NONE")

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # پاداش عضویت (join bonus) و پاداش دعوت دوست (referral invite bonus)
    # هرکدام فقط یک‌بار برای هر کاربر پرداخت می‌شوند؛ این دو پرچم از
    # پرداخت تکراری (مثلاً با /start زدن چندباره یا کلیک مکرر روی
    # «بررسی عضویت») جلوگیری می‌کنند.
    join_bonus_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referral_bonus_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # چک-این روزانه (بخش نگه‌داشت کاربر): آخرین تاریخی که پاداش روزانه
    # گرفته و چند روز پشت‌سرهم بدون وقفه چک-این کرده (streak).
    last_checkin_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    checkin_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    wallet: Mapped["Wallet"] = relationship(back_populates="user", uselist=False)
