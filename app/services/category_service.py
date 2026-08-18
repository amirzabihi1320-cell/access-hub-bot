from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.product import Product


class CategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active(self) -> list[Category]:
        result = await self.session.execute(
            select(Category).where(Category.status.is_(True)).order_by(Category.sort_order, Category.id)
        )
        return list(result.scalars().all())

    async def get(self, category_id: int) -> Category | None:
        result = await self.session.execute(select(Category).where(Category.id == category_id))
        return result.scalar_one_or_none()

    # ---------- ادمین (بخش ۱۴: ایجاد/ویرایش/فعال-غیرفعال) ----------

    async def list_all(self) -> list[Category]:
        result = await self.session.execute(select(Category).order_by(Category.sort_order, Category.id))
        return list(result.scalars().all())

    async def toggle_status(self, category_id: int) -> Category:
        category = await self.get(category_id)
        if category is None:
            raise ValueError("دسته‌بندی پیدا نشد.")
        category.status = not category.status
        await self.session.commit()
        return category

    async def toggle_columns(self, category_id: int) -> Category:
        """تعویض نمایش بین «تمام‌عرض» (۱) و «دو دکمه کنار هم» (۲) برای دسته‌بندی‌های موجود."""
        category = await self.get(category_id)
        if category is None:
            raise ValueError("دسته‌بندی پیدا نشد.")
        category.button_columns = 2 if category.button_columns == 1 else 1
        await self.session.commit()
        return category

    async def create(
        self,
        name: str,
        icon: str | None = None,
        button_columns: int = 1,
    ) -> Category:
        if button_columns not in (1, 2):
            raise ValueError("تعداد ستون دکمه باید ۱ یا ۲ باشد.")

        category = Category(
            name=name,
            icon=icon,
            status=True,
            button_columns=button_columns,
            sort_order=await self._next_sort_order(),
        )
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category

    async def _next_sort_order(self) -> int:
        result = await self.session.execute(select(func.coalesce(func.max(Category.sort_order), -1)))
        return result.scalar_one() + 1

    async def move(self, category_id: int, direction: str) -> None:
        """جابه‌جایی دسته‌بندی در ترتیب نمایش (بالا/پایین) با نزدیک‌ترین همسایه.
        مقایسه بر اساس (sort_order, id) انجام می‌شود تا حتی اگر چند دسته‌بندی
        قدیمی sort_order برابر (مثلاً همه ۰) داشته باشند هم جابه‌جایی درست کار کند.
        """
        category = await self.get(category_id)
        if category is None:
            raise ValueError("دسته‌بندی پیدا نشد.")

        key = tuple_(Category.sort_order, Category.id)
        my_key = (category.sort_order, category.id)

        query = select(Category)
        if direction == "up":
            query = query.where(key < my_key).order_by(Category.sort_order.desc(), Category.id.desc())
        else:
            query = query.where(key > my_key).order_by(Category.sort_order.asc(), Category.id.asc())

        result = await self.session.execute(query.limit(1))
        neighbor = result.scalar_one_or_none()
        if neighbor is None:
            return

        category.sort_order, neighbor.sort_order = neighbor.sort_order, category.sort_order
        await self.session.commit()

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
