import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.services.deposit_service import DepositAlreadyDecidedError, DepositService
from app.services.user_service import UserService
from app.services.wallet_service import WalletService


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest.mark.asyncio
async def test_approve_credits_wallet_once(session: AsyncSession):
    user = await UserService(session).get_or_create(222, "u", "U", None)
    deposit_service = DepositService(session)
    request = await deposit_service.create_request(user.id, 300_000)

    await deposit_service.approve(request.id, admin_id=999)

    balance = await WalletService(session).get_balance(user.id)
    assert balance == 300_000
    assert request.status == "APPROVED"


@pytest.mark.asyncio
async def test_approve_twice_raises_and_does_not_double_credit(session: AsyncSession):
    user = await UserService(session).get_or_create(333, "u", "U", None)
    deposit_service = DepositService(session)
    request = await deposit_service.create_request(user.id, 200_000)

    await deposit_service.approve(request.id, admin_id=999)
    with pytest.raises(DepositAlreadyDecidedError):
        await deposit_service.approve(request.id, admin_id=999)

    balance = await WalletService(session).get_balance(user.id)
    assert balance == 200_000  # نه ۴۰۰,۰۰۰ - تأیید دوباره اثر مالی ندارد


@pytest.mark.asyncio
async def test_reject_does_not_touch_wallet(session: AsyncSession):
    user = await UserService(session).get_or_create(444, "u", "U", None)
    deposit_service = DepositService(session)
    request = await deposit_service.create_request(user.id, 150_000)

    await deposit_service.reject(request.id, admin_id=999, reason="رسید نامعتبر")

    balance = await WalletService(session).get_balance(user.id)
    assert balance == 0
    assert request.status == "REJECTED"
    assert request.reject_reason == "رسید نامعتبر"
