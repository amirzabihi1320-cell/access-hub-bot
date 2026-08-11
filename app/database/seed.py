"""
اگه جدول categories خالی باشه، یه دسته‌بندی و دو محصول نمونه می‌سازه
تا بشه فروشگاه رو قبل از آماده شدن پنل ادمین (فاز ۵) تست کرد.
این فایل موقتیه و بعد از فاز ۵ (که افزودن محصول از تلگرام ممکن می‌شه) حذف می‌شود.
"""
import logging

from sqlalchemy import select

from app.database.base import get_session
from app.models.category import Category
from app.models.product import Product

logger = logging.getLogger("access_hub")


async def seed_initial_data() -> None:
    async with get_session() as session:
        result = await session.execute(select(Category))
        if result.scalars().first():
            return  # قبلاً seed شده، کاری نکن

        category = Category(
            name="🤖 هوش مصنوعی",
            icon="🤖",
            description="سرویس‌های AI",
            status=True,
            sort_order=1,
        )
        session.add(category)
        await session.flush()

        product_fixed = Product(
            category_id=category.id,
            name="Telegram Premium 3 Months",
            slug="tg-premium-3m",
            description="اشتراک ۳ ماهه تلگرام پرمیوم",
            product_type="FIXED",
            fixed_price=2_490_000,
            status=True,
            sort_order=1,
        )
        product_variable = Product(
            category_id=category.id,
            name="Telegram Stars",
            slug="tg-stars",
            description="خرید استارز تلگرام به هر تعداد دلخواه",
            product_type="VARIABLE_QUANTITY",
            unit_price=1_200,
            min_quantity=50,
            max_quantity=10_000,
            status=True,
            sort_order=2,
        )
        session.add_all([product_fixed, product_variable])
        await session.commit()

        logger.info("Seed data created: 1 category, 2 products.")
