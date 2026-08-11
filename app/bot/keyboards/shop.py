from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.category import Category
from app.models.product import Product


def categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        icon = cat.icon or "📦"
        buttons.append(
            [InlineKeyboardButton(text=f"{icon} {cat.name}", callback_data=f"shop:category:{cat.id}")]
        )
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_keyboard(products: list[Product], category_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(text=p.name, callback_data=f"shop:product:{p.id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="menu:shop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    buttons = []
    if product.product_type == "VARIABLE_QUANTITY":
        buttons.append(
            [InlineKeyboardButton(text="🔢 وارد کردن تعداد", callback_data=f"shop:enter_qty:{product.id}")]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="🛒 خرید", callback_data=f"shop:buy:{product.id}:1")]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"shop:category:{product.category_id}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
