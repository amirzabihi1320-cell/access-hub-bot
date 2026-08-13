from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.product import Product


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

    async def delete(self, category_id: int) -> None:
        """
        حذف دسته‌بندی. برای جلوگیری از پاک شدن ناخواسته‌ی محصولات (بخش ۵۸:
        یکپارچگی مالی/داده)، تا وقتی حداقل یک محصول به این دسته‌بندی وصل است
        اجازه‌ی حذف داده نمی‌شود؛ ادمین باید ابتدا محصولات را حذف/جابه‌جا کند.
        """
        category = await self.get(category_id)
        if category is None:
            raise ValueError("دسته‌بندی پیدا نشد.")

        count_result = await self.session.execute(
            select(func.count()).select_from(Product).where(Product.category_id == category_id)
        )
        product_count = count_result.scalar_one()
        if product_count > 0:
            raise ValueError(
                f"این دسته‌بندی {product_count} محصول دارد. ابتدا محصولات آن را حذف یا غیرفعال کنید."
            )

        await self.session.delete(category)
        await self.session.commit()
