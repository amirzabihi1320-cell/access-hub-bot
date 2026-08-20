from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.category import Category
from app.models.product import Product
from app.utils.keyboards import DEFAULT_COLUMNS, clamp_columns


def _mixed_columns_buttons(items, button_factory, default_columns: int = 1):
    """
    چیدمان دکمه‌ها بر اساس button_columns هر آیتم.

    1 = یک دکمه در هر ردیف (تمام‌عرض از نظر چیدمان)
    2 = دو دکمه در هر ردیف

    نکته: اندازه پیکسلی خود دکمه توسط Telegram Client تعیین می‌شود؛ Bot API
    گزینه‌ای برای تعیین width مستقیم ندارد. با این حال، وقتی مقدار 1 است،
    هر دکمه در ردیف مستقل قرار می‌گیرد و دیگر به‌صورت یک‌چهارم/دوستونه
    کنار دکمه دیگری قرار نمی‌گیرد.
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
            style=ButtonStyle.SUCCESS,
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
            text=f"🛍 {product.name}",
            callback_data=f"shop:product:{product.id}",
            style=ButtonStyle.PRIMARY,
        ),
        columns,
    )

    rows.append(
        [InlineKeyboardButton(
            text="🔙 بازگشت",
            callback_data="menu:shop",
            style=ButtonStyle.DANGER,
        )]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_detail_keyboard(product: Product) -> InlineKeyboardMarkup:
    buttons = []

    if product.product_type == "VARIABLE_QUANTITY":
        buttons.append([InlineKeyboardButton(
            text="🔢 وارد کردن تعداد",
            callback_data=f"shop:enter_qty:{product.id}",
            style=ButtonStyle.PRIMARY,
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text="💳 خرید با کیف پول",
            callback_data=f"shop:buy:{product.id}:1",
            style=ButtonStyle.SUCCESS,
        )])
        if product.token_price:
            buttons.append([InlineKeyboardButton(
                text=f"🪙 خرید با Token — {product.token_price:,}",
                callback_data=f"shop:buy_token:{product.id}:1",
                style=ButtonStyle.PRIMARY,
            )])

    buttons.append([InlineKeyboardButton(
        text="🔙 بازگشت",
        callback_data=f"shop:category:{product.category_id}",
        style=ButtonStyle.DANGER,
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
