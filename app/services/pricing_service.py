"""
Pricing Engine جدا از Product Model (طبق اصل بخش ۱۳ مستند).
در فاز ۱ فقط Fixed و Unit Price ساده پیاده می‌شود.
Tier pricing / VIP discount / Coupon در فازهای بعد به همین تابع اضافه می‌شوند
بدون نیاز به تغییر مدل محصول.

فاز جدید: تخفیف زمان‌دار محصول (discount_percent + discount_expires_at روی
خودِ Product) اینجا روی total_price اعمال می‌شود؛ قیمت اصلی هم برای نمایش
خط‌خورده در UI نگه داشته می‌شود.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.product import Product


class InvalidQuantityError(Exception):
    pass


@dataclass
class PriceResult:
    unit_price: int | None
    quantity: int
    total_price: int
    original_total_price: int | None = None  # فقط وقتی تخفیف فعاله مقدار می‌گیره


def is_discount_active(product: Product) -> bool:
    if not product.discount_percent or product.discount_percent <= 0:
        return False
    if not product.discount_expires_at:
        return False
    expires = product.discount_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > datetime.now(timezone.utc)


def apply_discount(product: Product, total_price: int) -> tuple[int, int | None]:
    if not is_discount_active(product):
        return total_price, None
    percent = max(0, min(90, product.discount_percent))  # سقف ایمنی ۹۰٪
    discounted = total_price - (total_price * percent // 100)
    return discounted, total_price


def calculate_price(product: Product, quantity: int = 1) -> PriceResult:
    if product.product_type == "FIXED":
        if product.fixed_price is None:
            raise ValueError(f"محصول {product.id} از نوع FIXED است ولی fixed_price ندارد.")
        total, original = apply_discount(product, product.fixed_price)
        return PriceResult(unit_price=product.fixed_price, quantity=1, total_price=total, original_total_price=original)

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
        total, original = apply_discount(product, total)
        return PriceResult(unit_price=product.unit_price, quantity=quantity, total_price=total, original_total_price=original)

    raise ValueError(f"نوع محصول پشتیبانی‌نشده برای Pricing: {product.product_type}")
