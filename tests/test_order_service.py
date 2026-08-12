import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.enums import WalletTransactionType
from app.database.base import Base
from app.models.category import Category
from app.models.product import Product
from app.services.order_service import OrderAlreadyProcessedError, OrderService
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


async def _make_fixed_product(session: AsyncSession) -> Product:
    category = Category(name="AI", icon="🤖", status=True, sort_order=1)
    session.add(category)
    await session.flush()
    product = Product(
        category_id=category.id,
        name="Telegram Premium 3M",
        slug="tg-premium-3m",
        product_type="FIXED",
        fixed_price=2_000_000,
        status=True,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


@pytest.mark.asyncio
async def test_create_and_pay_debits_wallet_and_creates_order(session: AsyncSession):
    user = await UserService(session).get_or_create(555, "u", "U", None)
    product = await _make_fixed_product(session)
    await WalletService(session).credit(user.id, 5_000_000, WalletTransactionType.DEPOSIT)

    order = await OrderService(session).create_and_pay(user.id, product.id, 1)

    assert order.final_price == 2_000_000
    assert order.status == "WAITING_ADMIN"
    balance = await WalletService(session).get_balance(user.id)
    assert balance == 3_000_000


@pytest.mark.asyncio
async def test_create_and_pay_raises_and_rolls_back_when_balance_insufficient(session: AsyncSession):
    user = await UserService(session).get_or_create(666, "u", "U", None)
    product = await _make_fixed_product(session)

    with pytest.raises(Exception):
        await OrderService(session).create_and_pay(user.id, product.id, 1)
    await session.rollback()  # همان کاری که get_session() در بات به‌صورت خودکار انجام می‌دهد

    balance = await WalletService(session).get_balance(user.id)
    assert balance == 0
    orders = await OrderService(session).list_for_user(user.id)
    assert orders == []


@pytest.mark.asyncio
async def test_mark_delivered_twice_raises(session: AsyncSession):
    user = await UserService(session).get_or_create(777, "u", "U", None)
    product = await _make_fixed_product(session)
    await WalletService(session).credit(user.id, 5_000_000, WalletTransactionType.DEPOSIT)
    order_service = OrderService(session)
    order = await order_service.create_and_pay(user.id, product.id, 1)

    await order_service.mark_delivered(order.id)
    with pytest.raises(OrderAlreadyProcessedError):
        await order_service.mark_delivered(order.id)
