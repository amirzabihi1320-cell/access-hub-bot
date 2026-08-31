import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.models.payment_transaction import PaymentTransaction
from app.models.user import User
from app.models.wallet import Wallet, WalletTransaction
from app.services.payment_service import PaymentService


@pytest.mark.asyncio
async def test_payment_service_models_load():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        user = User(telegram_id=123, username="test", first_name="Test")
        session.add(user)
        await session.flush()
        session.add(Wallet(user_id=user.id, balance=0))
        session.add(PaymentTransaction(user_id=user.id, payment_id="p1", provider="TRONADO", amount_toman=1000))
        await session.commit()
    await engine.dispose()
