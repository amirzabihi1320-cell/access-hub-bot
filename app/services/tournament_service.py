"""
سرویس تورنومنت.

اصل مالی مهم: جایزه‌ی هر تورنومنت مقدار/توضیح ثابتی است که خودِ ادمین از
قبل تعیین می‌کند و هرگز از مجموع Entry Feeی که شرکت‌کننده‌ها پرداخت
می‌کنند محاسبه نمی‌شود. Entry Fee (در صورت تنظیم) مستقیماً به‌عنوان
درآمد فروشگاه کسر می‌شود، نه به‌عنوان استخر جایزه. رتبه‌بندی هم صرفاً بر
اساس عملکرد واقعی و قابل‌اندازه‌گیری (تعداد دعوت موفق یا تعداد خرید
تکمیل‌شده) در بازه‌ی زمانی تورنومنت است - نه شانس.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderStatus, WalletTransactionType
from app.models.order import Order
from app.models.tournament import Tournament, TournamentParticipant
from app.models.user import User
from app.services.wallet_service import InsufficientBalanceError, WalletService


class TournamentError(Exception):
    """خطای عمومی تورنومنت (پیام برای کاربر قابل نمایش است)."""


class AlreadyJoinedError(TournamentError):
    pass


class TournamentNotActiveError(TournamentError):
    pass


class AlreadySettledError(TournamentError):
    pass


class TournamentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- مدیریت ادمین ----------

    async def create(
        self,
        title: str,
        metric: str,
        entry_fee: int,
        prize_description: str,
        duration_days: int,
        admin_id: int,
        prize_wallet_credit: int | None = None,
    ) -> Tournament:
        now = datetime.now(timezone.utc)
        tournament = Tournament(
            title=title,
            metric=metric,
            entry_fee=entry_fee,
            prize_description=prize_description,
            prize_wallet_credit=prize_wallet_credit,
            start_at=now,
            end_at=now + timedelta(days=duration_days),
            status="ACTIVE",
            created_by_admin_id=admin_id,
        )
        self.session.add(tournament)
        await self.session.commit()
        await self.session.refresh(tournament)
        return tournament

    async def get(self, tournament_id: int) -> Tournament | None:
        return await self.session.get(Tournament, tournament_id)

    async def list_active(self) -> list[Tournament]:
        result = await self.session.execute(
            select(Tournament).where(Tournament.status == "ACTIVE").order_by(Tournament.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Tournament]:
        result = await self.session.execute(select(Tournament).order_by(Tournament.created_at.desc()))
        return list(result.scalars().all())

    async def end_now(self, tournament_id: int) -> Tournament:
        """پایان زودهنگام توسط ادمین (اختیاری)."""
        tournament = await self.get(tournament_id)
        if not tournament:
            raise TournamentError("تورنومنت پیدا نشد.")
        if tournament.status != "ACTIVE":
            raise TournamentNotActiveError("این تورنومنت فعال نیست.")
        tournament.end_at = datetime.now(timezone.utc)
        tournament.status = "ENDED"
        await self.session.commit()
        return tournament

    async def cancel(self, tournament_id: int) -> list[TournamentParticipant]:
        """
        لغو تورنومنت پیش از پایان؛ Entry Fee تمام شرکت‌کننده‌ها Refund می‌شود
        (اصل ۵۸ سند - هیچ پولی بدون دلیل نزد فروشگاه نمی‌ماند).
        """
        tournament = await self.get(tournament_id)
        if not tournament:
            raise TournamentError("تورنومنت پیدا نشد.")
        if tournament.status not in ("ACTIVE", "ENDED"):
            raise TournamentError("این تورنومنت قابل لغو نیست.")

        result = await self.session.execute(
            select(TournamentParticipant).where(TournamentParticipant.tournament_id == tournament_id)
        )
        participants = list(result.scalars().all())

        if tournament.entry_fee > 0:
            for p in participants:
                user = await self.session.get(User, p.user_id)
                if user:
                    await WalletService(self.session).credit(
                        user_id=user.id,
                        amount=tournament.entry_fee,
                        type_=WalletTransactionType.REFUND,
                        reference_id=f"tournament-cancel:{tournament.id}",
                        description=f"بازگشت ورودی تورنومنت لغوشده: {tournament.title}",
                    )

        tournament.status = "CANCELLED"
        await self.session.commit()
        return participants

    # ---------- شرکت کاربر ----------

    async def join(self, tournament_id: int, user_id: int) -> TournamentParticipant:
        tournament = await self.get(tournament_id)
        if not tournament:
            raise TournamentError("تورنومنت پیدا نشد.")
        if tournament.status != "ACTIVE":
            raise TournamentNotActiveError("این تورنومنت دیگر فعال نیست.")

        existing = await self.session.execute(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament_id,
                TournamentParticipant.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AlreadyJoinedError("شما قبلاً در این تورنومنت ثبت‌نام کرده‌اید.")

        if tournament.entry_fee > 0:
            try:
                await WalletService(self.session).debit(
                    user_id=user_id,
                    amount=tournament.entry_fee,
                    type_=WalletTransactionType.TOURNAMENT_ENTRY,
                    reference_id=f"tournament-entry:{tournament.id}",
                    description=f"ورودی تورنومنت: {tournament.title}",
                )
            except InsufficientBalanceError:
                raise TournamentError("موجودی کیف پول شما برای پرداخت ورودی این تورنومنت کافی نیست.")

        participant = TournamentParticipant(tournament_id=tournament_id, user_id=user_id)
        self.session.add(participant)
        await self.session.commit()
        await self.session.refresh(participant)
        return participant

    async def is_participant(self, tournament_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            select(TournamentParticipant).where(
                TournamentParticipant.tournament_id == tournament_id,
                TournamentParticipant.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    # ---------- امتیازدهی و لیدربورد ----------

    async def _score(self, tournament: Tournament, user_id: int) -> int:
        """
        امتیاز فقط بر اساس عملکرد واقعیِ ثبت‌شده در بازه‌ی زمانی تورنومنت
        محاسبه می‌شود؛ هیچ عنصر شانسی در این محاسبه نیست.
        """
        if tournament.metric == "REFERRALS":
            result = await self.session.execute(
                select(func.count()).select_from(User).where(
                    User.referred_by == user_id,
                    User.created_at >= tournament.start_at,
                    User.created_at <= tournament.end_at,
                )
            )
        else:  # PURCHASES
            result = await self.session.execute(
                select(func.count()).select_from(Order).where(
                    Order.user_id == user_id,
                    Order.status == OrderStatus.COMPLETED.value,
                    Order.created_at >= tournament.start_at,
                    Order.created_at <= tournament.end_at,
                )
            )
        return result.scalar_one()

    async def leaderboard(self, tournament_id: int, limit: int = 10) -> list[tuple[User, int]]:
        tournament = await self.get(tournament_id)
        if not tournament:
            return []

        result = await self.session.execute(
            select(TournamentParticipant).where(TournamentParticipant.tournament_id == tournament_id)
        )
        participants = list(result.scalars().all())

        rows: list[tuple[User, int]] = []
        for p in participants:
            user = await self.session.get(User, p.user_id)
            if not user:
                continue
            score = await self._score(tournament, user.id)
            rows.append((user, score))

        rows.sort(key=lambda r: r[1], reverse=True)
        return rows[:limit]

    # ---------- تعیین برنده و پرداخت جایزه ----------

    async def settle(self, tournament_id: int) -> tuple[Tournament, User | None, int]:
        """
        برنده را قطعی می‌کند و در صورت تنظیم prize_wallet_credit، جایزه را
        یک‌بار برای همیشه به کیف‌پول او واریز می‌کند (بخش ۵۸ سند - هر
        عملیات مالی فقط یک‌بار قابل انجام است).
        """
        tournament = await self.get(tournament_id)
        if not tournament:
            raise TournamentError("تورنومنت پیدا نشد.")
        if tournament.status == "SETTLED":
            raise AlreadySettledError("این تورنومنت قبلاً تسویه شده است.")
        if tournament.status not in ("ACTIVE", "ENDED"):
            raise TournamentError("این تورنومنت قابل تسویه نیست.")

        board = await self.leaderboard(tournament_id, limit=1)
        winner_user = None
        winner_score = 0
        if board and board[0][1] > 0:
            winner_user, winner_score = board[0]

        # نکته‌ی مهم (مثل رفع باگ فاز شارژ کیف‌پول): وضعیت SETTLED را قبل
        # از واریز جایزه روی همین Session تنظیم می‌کنیم. چون WalletService.credit
        # خودش در انتها session.commit() می‌زند، این تغییر و واریز جایزه با هم
        # در یک تراکنش دیتابیس ثبت یا رد می‌شوند - یعنی اگر واریز جایزه انجام
        # شود، دیگر امکان صدا زدن دوباره‌ی settle() و واریز تکراری وجود ندارد.
        tournament.status = "SETTLED"
        tournament.winner_user_id = winner_user.id if winner_user else None
        tournament.settled_at = datetime.now(timezone.utc)

        if winner_user and tournament.prize_wallet_credit:
            await WalletService(self.session).credit(
                user_id=winner_user.id,
                amount=tournament.prize_wallet_credit,
                type_=WalletTransactionType.TOURNAMENT_PRIZE,
                reference_id=f"tournament-prize:{tournament.id}",
                description=f"جایزه‌ی برنده‌ی تورنومنت: {tournament.title}",
            )
        else:
            await self.session.commit()

        return tournament, winner_user, winner_score
