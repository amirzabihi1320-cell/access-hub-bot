import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.enums import WalletTransactionType
from app.database.base import Base
from app.services.user_service import UserService
from app.services.wallet_service import InsufficientBalanceError, WalletService


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


async def _make_user(session: AsyncSession):
    return await UserService(session).get_or_create(111, "u", "U", None)


@pytest.mark.asyncio
async def test_credit_increases_balance_and_creates_ledger_entry(session: AsyncSession):
    user = await _make_user(session)
    wallet_service = WalletService(session)

    tx = await wallet_service.credit(user.id, 500_000, WalletTransactionType.DEPOSIT)

    assert tx.balance_before == 0
    assert tx.balance_after == 500_000
    assert await wallet_service.get_balance(user.id) == 500_000


@pytest.mark.asyncio
async def test_debit_decreases_balance(session: AsyncSession):
    user = await _make_user(session)
    wallet_service = WalletService(session)
    await wallet_service.credit(user.id, 1_000_000, WalletTransactionType.DEPOSIT)

    tx = await wallet_service.debit(user.id, 400_000, WalletTransactionType.PURCHASE)

    assert tx.amount == -400_000
    assert tx.balance_after == 600_000
    assert await wallet_service.get_balance(user.id) == 600_000


@pytest.mark.asyncio
async def test_debit_raises_when_balance_insufficient(session: AsyncSession):
    user = await _make_user(session)
    wallet_service = WalletService(session)

    with pytest.raises(InsufficientBalanceError):
        await wallet_service.debit(user.id, 1, WalletTransactionType.PURCHASE)


@pytest.mark.asyncio
async def test_list_transactions_returns_most_recent_first(session: AsyncSession):
    user = await _make_user(session)
    wallet_service = WalletService(session)
    await wallet_service.credit(user.id, 100_000, WalletTransactionType.DEPOSIT)
    await wallet_service.credit(user.id, 50_000, WalletTransactionType.BONUS)

    history = await wallet_service.list_transactions(user.id)

    assert len(history) == 2
    assert history[0].type == WalletTransactionType.BONUS.value
