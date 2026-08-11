from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active(self) -> list[Category]:
        result = await self.session.execute(
            select(Category).where(Category.status.is_(True)).order_by(Category.sort_order)
        )
        return list(result.scalars().all())

    async def get(self, category_id: int) -> Category | None:
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()
