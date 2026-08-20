from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.product import Product


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_by_category(self, category_id: int) -> list[Product]:
        result = await self.session.execute(
            select(Product)
            .where(Product.category_id == category_id, Product.status.is_(True))
            .order_by(Product.sort_order, Product.id)
        )
        return list(result.scalars().all())

    async def get(self, product_id: int) -> Product | None:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    # ---------- ادمین (بخش ۲۹: مدیریت محصولات) ----------

    async def list_all(self) -> list[Product]:
        result = await self.session.execute(
            select(Product).order_by(Product.category_id, Product.sort_order, Product.id)
        )
        return list(result.scalars().all())

    async def toggle_status(self, product_id: int) -> Product:
        product = await self.get(product_id)
        if product is None:
            raise ValueError("محصول پیدا نشد.")
        product.status = not product.status
        await self.session.commit()
        return product

    async def toggle_columns(self, product_id: int) -> Product:
        """تعویض نمایش بین «تمام‌عرض» (۱) و «دو دکمه کنار هم» (۲) برای محصولات موجود."""
        product = await self.get(product_id)
        if product is None:
            raise ValueError("محصول پیدا نشد.")
        product.button_columns = 2 if product.button_columns == 1 else 1
        await self.session.commit()
        return product

    async def move(self, product_id: int, direction: str) -> None:
        """
        جابه‌جایی محصول در ترتیب نمایش داخل همون دسته‌بندی (بالا/پایین).
        مقایسه بر اساس (sort_order, id) تا با مقادیر تکراری قدیمی هم درست کار کند.
        """
        product = await self.get(product_id)
        if product is None:
            raise ValueError("محصول پیدا نشد.")

        key = tuple_(Product.sort_order, Product.id)
        my_key = (product.sort_order, product.id)

        query = select(Product).where(Product.category_id == product.category_id)
        if direction == "up":
            query = query.where(key < my_key).order_by(Product.sort_order.desc(), Product.id.desc())
        else:
            query = query.where(key > my_key).order_by(Product.sort_order.asc(), Product.id.asc())

        result = await self.session.execute(query.limit(1))
        neighbor = result.scalar_one_or_none()
        if neighbor is None:
            return  # همین‌جا اولین/آخرین است، کاری لازم نیست

        product.sort_order, neighbor.sort_order = neighbor.sort_order, product.sort_order
        await self.session.commit()

    async def update_price(self, product_id: int, new_price: int) -> Product:
        if new_price <= 0:
            raise ValueError("قیمت باید مثبت باشد.")
        product = await self.get(product_id)
        if product is None:
            raise ValueError("محصول پیدا نشد.")
        if product.product_type == "FIXED":
            product.fixed_price = new_price
        else:
            product.unit_price = new_price
        await self.session.commit()
        return product

    async def update_token_price(self, product_id: int, new_price: int | None) -> Product:
        """تنظیم/حذف قیمت محصول با Access Token."""
        if new_price is not None and new_price <= 0:
            raise ValueError("قیمت Token باید مثبت باشد.")
        product = await self.get(product_id)
        if product is None:
            raise ValueError("محصول پیدا نشد.")
        product.token_price = new_price
        await self.session.commit()
        return product

    async def _next_sort_order(self, category_id: int) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(Product.sort_order), -1)).where(Product.category_id == category_id)
        )
        return result.scalar_one() + 1

    async def create_fixed(
        self,
        category_id: int,
        name: str,
        price: int,
        button_columns: int = 1,
    ) -> Product:
        if button_columns not in (1, 2):
            raise ValueError("تعداد ستون دکمه باید ۱ یا ۲ باشد.")

        product = Product(
            category_id=category_id,
            name=name,
            slug="",
            product_type="FIXED",
            fixed_price=price,
            status=True,
            button_columns=button_columns,
            sort_order=await self._next_sort_order(category_id),
        )
        self.session.add(product)
        await self.session.flush()
        product.slug = f"product-{product.id}"
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete(self, product_id: int) -> None:
        """
        حذف محصول. طبق اصل ۵۸ سند (یکپارچگی مالی)، سابقه‌ی سفارش‌ها هرگز
        نباید ناقص شود؛ پس اگر این محصول در حداقل یک سفارش استفاده شده،
        حذف واقعی رد می‌شود و فقط پیشنهاد می‌شود «غیرفعال» شود (که تاریخچه
        و گزارش‌های قبلی را دست‌نخورده نگه می‌دارد).
        """
        product = await self.get(product_id)
        if product is None:
            raise ValueError("محصول پیدا نشد.")

        count_result = await self.session.execute(
            select(func.count()).select_from(Order).where(Order.product_id == product_id)
        )
        order_count = count_result.scalar_one()
        if order_count > 0:
            raise ValueError(
                f"این محصول در {order_count} سفارش استفاده شده و برای حفظ سوابق مالی قابل حذف نیست. "
                "به‌جای حذف، آن را غیرفعال کنید."
            )

        await self.session.delete(product)
        await self.session.commit()

    async def create_variable(
        self,
        category_id: int,
        name: str,
        unit_price: int,
        min_quantity: int,
        max_quantity: int,
        button_columns: int = 1,
    ) -> Product:
        if button_columns not in (1, 2):
            raise ValueError("تعداد ستون دکمه باید ۱ یا ۲ باشد.")

        product = Product(
            category_id=category_id,
            name=name,
            slug="",
            product_type="VARIABLE_QUANTITY",
            unit_price=unit_price,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            status=True,
            button_columns=button_columns,
            sort_order=await self._next_sort_order(category_id),
        )
        self.session.add(product)
        await self.session.flush()
        product.slug = f"product-{product.id}"
        await self.session.commit()
        await self.session.refresh(product)
        return product
