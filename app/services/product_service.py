from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_category(self, category_id: int) -> list[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.category_id == category_id, Product.status.is_(True))
            .order_by(Product.sort_order)
        )
        return list(result.scalars().all())

    async def get(self, product_id: int) -> Product | None:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()
