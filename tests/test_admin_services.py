import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.base import Base
from app.services.category_service import CategoryService
from app.services.product_service import ProductService


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
async def test_create_category(session: AsyncSession):
    category = await CategoryService(session).create("Gaming", "🎮")
    assert category.id is not None
    assert category.status is True

    all_categories = await CategoryService(session).list_all()
    assert len(all_categories) == 1


@pytest.mark.asyncio
async def test_create_fixed_product_gets_unique_slug(session: AsyncSession):
    category = await CategoryService(session).create("AI", "🤖")
    product = await ProductService(session).create_fixed(category.id, "ChatGPT Plus", 900_000)

    assert product.product_type == "FIXED"
    assert product.fixed_price == 900_000
    assert product.slug == f"product-{product.id}"


@pytest.mark.asyncio
async def test_create_variable_product(session: AsyncSession):
    category = await CategoryService(session).create("Telegram", "💎")
    product = await ProductService(session).create_variable(category.id, "Telegram Stars", 1500, 50, 10000)

    assert product.product_type == "VARIABLE_QUANTITY"
    assert product.unit_price == 1500
    assert product.min_quantity == 50
    assert product.max_quantity == 10000
