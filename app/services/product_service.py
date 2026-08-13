from sqlalchemy import func, select
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
            .order_by(Product.sort_order)
        )
        return list(result.scalars().all())

    async def get(self, product_id: int) -> Product | None:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    # ---------- ادمین (بخش ۲۹: مدیریت محصولات) ----------

    async def list_all(self) -> list[Product]:
        result = await self.session.execute(select(Product).order_by(Product.category_id, Product.sort_order))
        return list(result.scalars().all())

    async def toggle_status(self, product_id: int) -> Product:
        product = await self.get(product_id)
        if product is None:
            raise ValueError("محصول پیدا نشد.")
        product.status = not product.status
        await self.session.commit()
        return product

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

    async def create_fixed(self, category_id: int, name: str, price: int) -> Product:
        product = Product(
            category_id=category_id,
            name=name,
            slug="",
            product_type="FIXED",
            fixed_price=price,
            status=True,
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
        self, category_id: int, name: str, unit_price: int, min_quantity: int, max_quantity: int
    ) -> Product:
        product = Product(
            category_id=category_id,
            name=name,
            slug="",
            product_type="VARIABLE_QUANTITY",
            unit_price=unit_price,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            status=True,
        )
        self.session.add(product)
        await self.session.flush()
        product.slug = f"product-{product.id}"
        await self.session.commit()
        await self.session.refresh(product)
        return product
