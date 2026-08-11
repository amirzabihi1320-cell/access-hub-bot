"""
تنها راه رسمی برای تغییر موجودی کیف پول.

اصول اجباری (بخش ۵۸ سند - Financial Integrity):
  - هیچ Balance بدون ثبت WalletTransaction تغییر نمی‌کند.
  - هیچ Transaction مالی هرگز Delete/Edit نمی‌شود؛ Refund یعنی رکورد جدید.
  - برای جلوگیری از Race Condition، هنگام تغییر موجودی سطر Wallet قفل
    می‌شود (`SELECT ... FOR UPDATE` روی PostgreSQL؛ روی SQLite در تست‌ها
    این عبارت نادیده گرفته می‌شود ولی منطق تراکنشی همچنان درست کار می‌کند).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import WalletTransactionType
from app.models.wallet import Wallet, WalletTransaction


class InsufficientBalanceError(Exception):
    """موجودی کیف پول کافی نیست."""


class WalletService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_wallet_locked(self, user_id: int) -> Wallet:
        result = await self.session.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            raise ValueError("کیف پول برای این کاربر پیدا نشد.")
        return wallet

    async def get_balance(self, user_id: int) -> int:
        result = await self.session.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = result.scalar_one()
        return wallet.balance

    async def credit(
        self,
        user_id: int,
        amount: int,
        type_: WalletTransactionType,
        reference_id: str | None = None,
        description: str | None = None,
        admin_id: int | None = None,
    ) -> WalletTransaction:
        """افزایش موجودی: DEPOSIT, REFUND, BONUS, ADMIN_ADJUSTMENT."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد.")

        wallet = await self._get_wallet_locked(user_id)
        balance_before = wallet.balance
        wallet.balance = balance_before + amount

        tx = WalletTransaction(
            user_id=user_id,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            type=type_.value,
            reference_id=reference_id,
            description=description,
            admin_id=admin_id,
        )
        self.session.add(tx)
        await self.session.commit()
        return tx

    async def debit(
        self,
        user_id: int,
        amount: int,
        type_: WalletTransactionType,
        reference_id: str | None = None,
        description: str | None = None,
        admin_id: int | None = None,
    ) -> WalletTransaction:
        """کاهش موجودی: PURCHASE, WITHDRAWAL, ADMIN_ADJUSTMENT منفی."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد.")

        wallet = await self._get_wallet_locked(user_id)
        if wallet.balance < amount:
            raise InsufficientBalanceError("موجودی کیف پول کافی نیست.")

        balance_before = wallet.balance
        wallet.balance = balance_before - amount

        tx = WalletTransaction(
            user_id=user_id,
            amount=-amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            type=type_.value,
            reference_id=reference_id,
            description=description,
            admin_id=admin_id,
        )
        self.session.add(tx)
        await self.session.commit()
        return tx

    async def list_transactions(self, user_id: int, limit: int = 10) -> list[WalletTransaction]:
        result = await self.session.execute(
            select(WalletTransaction)
            .where(WalletTransaction.user_id == user_id)
            .order_by(WalletTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
