from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.category import Category
from app.models.product import Product
from app.utils.keyboards import DEFAULT_COLUMNS, clamp_columns


def _mixed_columns_buttons(items, button_factory, default_columns: int = 1):
    """
    هر آیتم می‌تواند layout مستقل خودش را داشته باشد.

    button_columns:
    1 = تمام‌عرض
    2 = دو دکمه کنار هم
    """

    default_columns = clamp_columns(default_columns)

    rows = []
    pending_two = []

    for item in items:
        columns = getattr(item, "button_columns", None)

        if columns not in (1, 2):
            columns = default_columns

        button = button_factory(item)

        if columns == 1:
            if pending_two:
                rows.append(pending_two)
                pending_two = []

            rows.append([button])
            continue

        # columns == 2
        pending_two.append(button)

        if len(pending_two) == 2:
            rows.append(pending_two)
            pending_two = []

    if pending_two:
        rows.append(pending_two)

    return rows


def categories_keyboard(
    categories: list[Category],
    columns: int = DEFAULT_COLUMNS,
) -> InlineKeyboardMarkup:
    rows = _mixed_columns_buttons(
        categories,
        lambda cat: InlineKeyboardButton(
            text=f"{cat.icon or '📦'} {cat.name}",
            callback_data=f"shop:category:{cat.id}",
        ),
        columns,
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_keyboard(
    products: list[Product],
    category_id: int,
    columns: int = DEFAULT_COLUMNS,
) -> InlineKeyboardMarkup:
    rows = _mixed_columns_buttons(
        products,
        lambda product: InlineKeyboardButton(
            text=product.name,
            callback_data=f"shop:product:{product.id}",
        ),
        columns,
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data="menu:shop",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    buttons = []

    if product.product_type == "VARIABLE_QUANTITY":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔢 وارد کردن تعداد",
                    callback_data=f"shop:enter_qty:{product.id}",
                )
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🛒 خرید",
                    callback_data=f"shop:buy:{product.id}:1",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data=f"shop:category:{product.category_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
