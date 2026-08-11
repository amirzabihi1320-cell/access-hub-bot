"""
تست نمونه با SQLite in-memory برای اثبات کارکرد UserService.
از فاز ۳ به بعد، تست‌های Wallet/Ledger/Coupon/Referral هم به همین شکل
اضافه می‌شوند (طبق بخش ۴۵ مستند).
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.services.user_service import UserService


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
async def test_get_or_create_new_user(session: AsyncSession):
    service = UserService(session)
    user = await service.get_or_create(
        telegram_id=123456789,
        username="tester",
        first_name="Test",
        last_name="User",
    )

    assert user.telegram_id == 123456789
    assert user.referral_code.startswith("AH")
    assert user.wallet.balance == 0


@pytest.mark.asyncio
async def test_get_or_create_existing_user_updates_fields(session: AsyncSession):
    service = UserService(session)
    first = await service.get_or_create(123, "old_name", "Old", "Name")
    second = await service.get_or_create(123, "new_name", "New", "Name")

    assert first.id == second.id
    assert second.username == "new_name"
