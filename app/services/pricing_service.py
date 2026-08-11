"""
Pricing Engine جدا از Product Model (طبق اصل بخش ۱۳ مستند).
در فاز ۱ فقط Fixed و Unit Price ساده پیاده می‌شود.
Tier pricing / VIP discount / Coupon در فازهای بعد به همین تابع اضافه می‌شوند
بدون نیاز به تغییر مدل محصول.
"""
from dataclasses import dataclass

from app.models.product import Product


class InvalidQuantityError(Exception):
    pass


@dataclass
class PriceResult:
    unit_price: int | None
    quantity: int
    total_price: int


def calculate_price(product: Product, quantity: int = 1) -> PriceResult:
    if product.product_type == "FIXED":
        if product.fixed_price is None:
            raise ValueError(f"محصول {product.id} از نوع FIXED است ولی fixed_price ندارد.")
        return PriceResult(unit_price=product.fixed_price, quantity=1, total_price=product.fixed_price)

    if product.product_type == "VARIABLE_QUANTITY":
        if product.unit_price is None:
            raise ValueError(f"محصول {product.id} از نوع VARIABLE_QUANTITY است ولی unit_price ندارد.")

        min_q = product.min_quantity or 1
        max_q = product.max_quantity or float("inf")
        if quantity < min_q or quantity > max_q:
            raise InvalidQuantityError(
                f"تعداد باید بین {min_q} تا {product.max_quantity or '∞'} باشد."
            )

        total = product.unit_price * quantity
        return PriceResult(unit_price=product.unit_price, quantity=quantity, total_price=total)

    raise ValueError(f"نوع محصول پشتیبانی‌نشده برای Pricing: {product.product_type}")
