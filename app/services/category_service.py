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

    # ---------- ادمین (بخش ۱۴: ایجاد/ویرایش/فعال-غیرفعال) ----------

    async def list_all(self) -> list[Category]:
        result = await self.session.execute(select(Category).order_by(Category.sort_order))
        return list(result.scalars().all())

    async def toggle_status(self, category_id: int) -> Category:
        category = await self.get(category_id)
        if category is None:
            raise ValueError("دسته‌بندی پیدا نشد.")
        category.status = not category.status
        await self.session.commit()
        return category

    async def create(self, name: str, icon: str | None = None) -> Category:
        category = Category(name=name, icon=icon, status=True)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category
