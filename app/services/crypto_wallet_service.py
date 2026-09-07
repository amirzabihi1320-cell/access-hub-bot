"""
تنها راه رسمی برای تغییر موجودی کیف‌پول ارز دیجیتال (TRX/TON) - همان
اصل Financial Integrity که app/services/wallet_service.py برای Wallet
تومانی رعایت می‌کند، به‌علاوه‌ی یک نکته‌ی اضافه‌ی مخصوص پرداخت‌های
بیرونی (بند ۵ سند): Callback تکراری هرگز نباید باعث Credit دوباره شود -
credit() قبل از افزایش موجودی، reference_id را چک می‌کند و اگر قبلاً
پردازش شده، بدون خطا همان تراکنش قبلی را برمی‌گرداند (Idempotent).
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CryptoCurrency, CryptoWalletTxType
from app.models.crypto_wallet import CryptoWallet, CryptoWalletTransaction


class InsufficientCryptoBalanceError(Exception):
    """موجودی کیف‌پول ارز دیجیتال کافی نیست."""


class CryptoWalletService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_or_create_wallet_locked(self, user_id: int, currency: CryptoCurrency) -> CryptoWallet:
        result = await self.session.execute(
            select(CryptoWallet)
            .where(CryptoWallet.user_id == user_id, CryptoWallet.currency == currency.value)
            .with_for_update()
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            wallet = CryptoWallet(user_id=user_id, currency=currency.value, balance=Decimal("0"))
            self.session.add(wallet)
            await self.session.flush()
        return wallet

    async def get_balance(self, user_id: int, currency: CryptoCurrency) -> Decimal:
        result = await self.session.execute(
            select(CryptoWallet).where(CryptoWallet.user_id == user_id, CryptoWallet.currency == currency.value)
        )
        wallet = result.scalar_one_or_none()
        return wallet.balance if wallet else Decimal("0")

    async def _find_existing(
        self, reference_id: str | None, type_: CryptoWalletTxType
    ) -> CryptoWalletTransaction | None:
        if not reference_id:
            return None
        result = await self.session.execute(
            select(CryptoWalletTransaction).where(
                CryptoWalletTransaction.reference_id == reference_id,
                CryptoWalletTransaction.type == type_.value,
            )
        )
        return result.scalar_one_or_none()

    async def credit(
        self,
        user_id: int,
        currency: CryptoCurrency,
        amount: Decimal,
        type_: CryptoWalletTxType,
        reference_id: str | None = None,
        description: str | None = None,
        admin_id: int | None = None,
    ) -> CryptoWalletTransaction:
        """افزایش موجودی: DEPOSIT, CONVERSION_IN, ADMIN_ADJUSTMENT.

        Idempotent روی (reference_id, type_): اگر قبلاً برای همین
        reference_id تراکنشی از همین نوع ثبت شده باشد، موجودی دوباره
        افزایش پیدا نمی‌کند و همان رکورد قبلی برگردانده می‌شود - این
        همان محافظتی است که بند ۵ سند برای Callback تکراری Tronado می‌خواهد.
        """
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد.")

        existing = await self._find_existing(reference_id, type_)
        if existing is not None:
            return existing

        wallet = await self._get_or_create_wallet_locked(user_id, currency)
        balance_before = wallet.balance
        wallet.balance = balance_before + amount

        tx = CryptoWalletTransaction(
            user_id=user_id,
            currency=currency.value,
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
        currency: CryptoCurrency,
        amount: Decimal,
        type_: CryptoWalletTxType,
        reference_id: str | None = None,
        description: str | None = None,
        admin_id: int | None = None,
    ) -> CryptoWalletTransaction:
        """کاهش موجودی: CONVERSION_OUT, WITHDRAWAL, ADMIN_ADJUSTMENT منفی."""
        if amount <= 0:
            raise ValueError("مبلغ باید مثبت باشد.")

        existing = await self._find_existing(reference_id, type_)
        if existing is not None:
            return existing

        wallet = await self._get_or_create_wallet_locked(user_id, currency)
        if wallet.balance < amount:
            raise InsufficientCryptoBalanceError("موجودی کیف‌پول ارز دیجیتال کافی نیست.")

        balance_before = wallet.balance
        wallet.balance = balance_before - amount

        tx = CryptoWalletTransaction(
            user_id=user_id,
            currency=currency.value,
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

    async def list_transactions(self, user_id: int, currency: CryptoCurrency, limit: int = 10) -> list[CryptoWalletTransaction]:
        result = await self.session.execute(
            select(CryptoWalletTransaction)
            .where(CryptoWalletTransaction.user_id == user_id, CryptoWalletTransaction.currency == currency.value)
            .order_by(CryptoWalletTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
