"""
Seed اولیه فروشگاه.

اگر جدول categories خالی باشد:
- یک دسته‌بندی می‌سازد.
- محصول Telegram Premium را می‌سازد.
- محصول Access Token را می‌سازد.

Access Token:
- هر 500 Token = 20,000 تومان
- حداقل خرید = 500 Token
- حداکثر خرید = ندارد
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
            return

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

        product_token = Product(
            category_id=category.id,
            name="🪙 Access Token",
            slug="access-token",
            description=(
                "خرید Access Token برای استفاده در بخش بازی. "
                "هر ۵۰۰ توکن ۲۰٬۰۰۰ تومان. "
                "حداقل خرید ۵۰۰ توکن و بدون سقف خرید."
            ),
            product_type="VARIABLE_QUANTITY",
            unit_price=40,
            min_quantity=500,
            max_quantity=None,
            status=True,
            sort_order=2,
        )

        session.add_all([product_fixed, product_token])
        await session.commit()

        logger.info(
            "Seed data created: 1 category, 2 products "
            "(Telegram Premium + Access Token)."
        )
