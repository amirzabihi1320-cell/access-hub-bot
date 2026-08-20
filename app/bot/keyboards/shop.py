from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.category import Category
from app.models.product import Product
from app.utils.keyboards import DEFAULT_COLUMNS, clamp_columns


STYLE_MAP = {
    "primary": ButtonStyle.PRIMARY,
    "success": ButtonStyle.SUCCESS,
    "danger": ButtonStyle.DANGER,
}

# Telegram Bot API برای InlineKeyboardButton عرض/ارتفاع پیکسلی مستقیم ندارد.
# برای فروشگاه، اندازه بصری دکمه‌ها را عمداً بزرگ می‌کنیم: یک حداقل عرض
# ثابت با EM SPACE و یک خط دومِ نامرئی باعث می‌شود دکمه روی موبایل هم
# حدوداً دو برابر بزرگ‌تر از حالت قبلی دیده شود.
_EM_SPACE = "\u2003"
_BLANK = "\u2800"


def _large_shop_button_text(text: str, min_width: int = 30) -> str:
    text = str(text).strip()
    # طول تقریبی متن برای جلوگیری از دکمه‌های بیش از حد پهن
    current = len(text)
    padding = max(5, (min_width - current) // 2)
    side = _EM_SPACE * padding
    # خط دوم با کاراکتر خالیِ قابل‌عرض برای افزایش ارتفاع دکمه
    return f"{side}{text}{side}\n{_BLANK * 8}"


def button_style(value: str | None, default: ButtonStyle) -> ButtonStyle:
    return STYLE_MAP.get((value or "").lower(), default)


def _mixed_columns_buttons(items, button_factory, default_columns: int = 1, force_columns: bool = False):
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
        columns = default_columns if force_columns else getattr(item, "button_columns", None)
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
    force_columns: bool = False,
) -> InlineKeyboardMarkup:
    rows = _mixed_columns_buttons(
        categories,
        lambda cat: InlineKeyboardButton(
            text=_large_shop_button_text(f"{cat.icon or '📦'} {cat.name}", min_width=30),
            callback_data=f"shop:category:{cat.id}",
            style=button_style(getattr(cat, "button_style", None), ButtonStyle.SUCCESS),
        ),
        columns,
        force_columns=force_columns,
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_keyboard(
    products: list[Product],
    category_id: int,
    columns: int = DEFAULT_COLUMNS,
    force_columns: bool = False,
) -> InlineKeyboardMarkup:
    """
    فهرست فروشگاه را به‌صورت واقعیِ قابل خرید می‌سازد.

    هر محصول یک ردیف نام/انتخاب دارد و در صورت فعال بودن قیمت‌ها،
    دکمه‌های پرداخت ریالی و توکنی نیز همان‌جا نمایش داده می‌شوند.
    برای محصول VARIABLE_QUANTITY ابتدا باید تعداد انتخاب شود.
    """
    rows = []
    effective_columns = columns if columns in (1, 2) else DEFAULT_COLUMNS
    # وقتی تنظیمات سراسری فروشگاه فعال است، چیدمان همه محصولات دقیقاً از همان مقدار پیروی می‌کند.
    pending_product_buttons = []

    for product in products:
        product_button = InlineKeyboardButton(
            text=_large_shop_button_text(f"🛍 {product.name}", min_width=32),
            callback_data=f"shop:product:{product.id}",
            style=button_style(getattr(product, "button_style", None), ButtonStyle.PRIMARY),
        )
        pending_product_buttons.append(product_button)
        if effective_columns == 1 or len(pending_product_buttons) == 2:
            rows.append(pending_product_buttons)
            pending_product_buttons = []

        if product.product_type == "FIXED":
            payment_buttons = []
            if product.fixed_price is not None:
                payment_buttons.append(InlineKeyboardButton(
                    text=f"💳 ریالی — {product.fixed_price:,} تومان",
                    callback_data=f"shop:buy:{product.id}:1",
                    style=ButtonStyle.SUCCESS,
                ))
            if product.token_price and product.token_price > 0:
                payment_buttons.append(InlineKeyboardButton(
                    text=f"🪙 توکنی — {product.token_price:,} Token",
                    callback_data=f"shop:buy_token:{product.id}:1",
                    style=ButtonStyle.PRIMARY,
                ))
            if payment_buttons:
                if effective_columns == 2 and len(payment_buttons) == 2:
                    rows.append(payment_buttons)
                else:
                    rows.extend([[button] for button in payment_buttons])
        else:
            rows.append([InlineKeyboardButton(
                text="🔢 انتخاب تعداد و پرداخت",
                callback_data=f"shop:enter_qty:{product.id}",
                style=ButtonStyle.SUCCESS,
            )])

    if pending_product_buttons:
        rows.append(pending_product_buttons)

    rows.append([InlineKeyboardButton(
        text="🔙 بازگشت",
        callback_data="menu:shop",
        style=ButtonStyle.DANGER,
    )])
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
        # روش‌های پرداخت محصول: ریالی از کیف‌پول ریالی یا با Access Token.
        # هر روش در یک ردیف مستقل نمایش داده می‌شود تا انتخاب پرداخت واضح باشد.
        rial_price = product.fixed_price if product.product_type == "FIXED" else product.unit_price
        if rial_price is not None:
            buttons.append([InlineKeyboardButton(
                text=f"💳 پرداخت ریالی — {rial_price:,} تومان",
                callback_data=f"shop:buy:{product.id}:1",
                style=ButtonStyle.SUCCESS,
            )])
        if product.token_price:
            buttons.append([InlineKeyboardButton(
                text=f"🪙 پرداخت توکنی — {product.token_price:,} Token",
                callback_data=f"shop:buy_token:{product.id}:1",
                style=ButtonStyle.PRIMARY,
            )])

    buttons.append([InlineKeyboardButton(
        text="🔙 بازگشت",
        callback_data=f"shop:category:{product.category_id}",
        style=ButtonStyle.DANGER,
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
