from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.pricing_service import is_discount_active

EDITABLE_SETTINGS = {
    "welcome_text": "📝 متن خوشامدگویی",
    "payment_info": "💳 اطلاعات پرداخت",
    "token_transfer_fee_percent": "💎 کارمزد انتقال Token (%)",
    "referral_cashback_percent": "👥 درصد پاداش رفرال (کش‌بک معرف)",
}



def admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛍 محصولات", callback_data="admin:products"),
                InlineKeyboardButton(text="📂 دسته‌بندی‌ها", callback_data="admin:categories"),
            ],
            [
                InlineKeyboardButton(text="💳 درخواست‌های شارژ", callback_data="admin:deposits"),
                InlineKeyboardButton(text="📦 سفارش‌های در انتظار", callback_data="admin:orders"),
            ],
            [
                InlineKeyboardButton(text="📢 عضویت اجباری", callback_data="admin:channels"),
                InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin:settings"),
            ],
            [
                InlineKeyboardButton(text="🏆 تورنومنت‌ها", callback_data="admin:tournaments"),
                InlineKeyboardButton(text="📊 آمار فروش", callback_data="admin:stats"),
            ],
        ]
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")]]
    )


STYLE_LABELS = {
    "primary": "🔵 آبی",
    "success": "🟢 سبز",
    "danger": "🔴 قرمز",
}


def style_label(style: str | None, default: str) -> str:
    return STYLE_LABELS.get((style or "").lower(), STYLE_LABELS[default])


def admin_category_style_keyboard(category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔵 آبی", callback_data=f"admin:category:style:{category_id}:primary", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(text="🟢 سبز", callback_data=f"admin:category:style:{category_id}:success", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton(text="🔴 قرمز", callback_data=f"admin:category:style:{category_id}:danger", style=ButtonStyle.DANGER),
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:categories")],
        ]
    )


def admin_product_style_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔵 آبی", callback_data=f"admin:product:style:{product_id}:primary", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(text="🟢 سبز", callback_data=f"admin:product:style:{product_id}:success", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton(text="🔴 قرمز", callback_data=f"admin:product:style:{product_id}:danger", style=ButtonStyle.DANGER),
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:products")],
        ]
    )


def admin_categories_keyboard(categories) -> InlineKeyboardMarkup:
    rows = []
    for c in categories:
        mark = "🟢" if c.status else "🔴"
        size_mark = "📏" if c.button_columns == 1 else "↔️"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {c.icon or ''} {c.name}", callback_data=f"admin:category:toggle:{c.id}"
                ),
                InlineKeyboardButton(text=size_mark, callback_data=f"admin:category:columns:{c.id}"),
                InlineKeyboardButton(
                    text=style_label(getattr(c, "button_style", None), "success"),
                    callback_data=f"admin:category:style:{c.id}",
                ),
                InlineKeyboardButton(text="🗑", callback_data=f"admin:category:del:{c.id}"),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(text="⬆️", callback_data=f"admin:category:up:{c.id}"),
                InlineKeyboardButton(text="⬇️", callback_data=f"admin:category:down:{c.id}"),
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ افزودن دسته‌بندی", callback_data="admin:category:add")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_category_delete_confirm_keyboard(category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ بله، حذف کن", callback_data=f"admin:category:delyes:{category_id}"),
                InlineKeyboardButton(text="❌ انصراف", callback_data="admin:categories"),
            ]
        ]
    )


def admin_products_keyboard(products) -> InlineKeyboardMarkup:
    rows = []
    for p in products:
        mark = "🟢" if p.status else "🔴"
        rows.append([InlineKeyboardButton(text=f"{mark} {p.name}", callback_data=f"admin:product:view:{p.id}")])
    rows.append([InlineKeyboardButton(text="➕ افزودن محصول", callback_data="admin:product:add")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_product_delete_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ بله، حذف کن", callback_data=f"admin:product:delyes:{product_id}"),
                InlineKeyboardButton(text="❌ انصراف", callback_data="admin:products"),
            ]
        ]
    )


def admin_product_category_pick_keyboard(categories) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{c.icon or ''} {c.name}", callback_data=f"admin:product:add:category:{c.id}")]
        for c in categories
    ]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:products")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_product_type_pick_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 قیمت ثابت", callback_data="admin:product:add:type:FIXED"),
                InlineKeyboardButton(text="🔢 تعداد متغیر", callback_data="admin:product:add:type:VARIABLE_QUANTITY"),
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:products")],
        ]
    )


def admin_product_detail_keyboard(product, is_featured: bool = False) -> InlineKeyboardMarkup:
    mark = "🔴 غیرفعال کن" if product.status else "🟢 فعال کن"
    size_label = "📏 نمایش: تمام‌عرض (تغییر به دو ستون)" if product.button_columns == 1 else "↔️ نمایش: دو ستون (تغییر به تمام‌عرض)"
    token_label = f"🪙 قیمت Token: {product.token_price:,}" if product.token_price else "🪙 فعال‌سازی خرید با Token"
    discount_label = "❌ لغو تخفیف زمان‌دار" if is_discount_active(product) else "🔥 تخفیف زمان‌دار"
    pin_label = "📌 برداشتن از پیشنهاد ویژه" if is_featured else "📌 پین به‌عنوان پیشنهاد ویژه"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 تغییر قیمت تومان", callback_data=f"admin:product:price:{product.id}", style=ButtonStyle.SUCCESS)],
            [InlineKeyboardButton(text=token_label, callback_data=f"admin:product:token_price:{product.id}", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton(text=mark, callback_data=f"admin:product:toggle:{product.id}", style=ButtonStyle.SUCCESS if not product.status else ButtonStyle.DANGER)],
            [InlineKeyboardButton(text=size_label, callback_data=f"admin:product:columns:{product.id}", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton(
                text=f"🎨 رنگ دکمه: {style_label(getattr(product, 'button_style', None), 'primary')}",
                callback_data=f"admin:product:style:{product.id}",
                style=ButtonStyle.PRIMARY,
            )],
            [
                InlineKeyboardButton(text="⬆️ بالاتر", callback_data=f"admin:product:up:{product.id}", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(text="⬇️ پایین‌تر", callback_data=f"admin:product:down:{product.id}", style=ButtonStyle.PRIMARY),
            ],
            [InlineKeyboardButton(text=discount_label, callback_data=f"admin:product:discount:{product.id}", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton(text=pin_label, callback_data=f"admin:product:pin:{product.id}", style=ButtonStyle.PRIMARY)],
            [InlineKeyboardButton(text="🗑 حذف محصول", callback_data=f"admin:product:del:{product.id}", style=ButtonStyle.DANGER)],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:products", style=ButtonStyle.DANGER)],
        ]
    )


def admin_discount_duration_keyboard(product_id: int) -> InlineKeyboardMarkup:
    options = [
        ("⏱ ۱ ساعت", 1),
        ("⏱ ۶ ساعت", 6),
        ("⏱ ۱۲ ساعت", 12),
        ("📅 ۱ روز", 24),
        ("📅 ۳ روز", 72),
        ("📅 ۷ روز", 168),
    ]
    rows = [[InlineKeyboardButton(text=label, callback_data=f"admin:product:discount:hours:{product_id}:{hours}")] for label, hours in options]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"admin:product:view:{product_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_settings_keyboard(report_enabled: bool = True) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"admin:setting:edit:{key}")
        for key, label in EDITABLE_SETTINGS.items()
    ]
    report_mark = "🟢" if report_enabled else "🔴"
    buttons.append(
        InlineKeyboardButton(
            text=f"📢 گزارش سفارش {report_mark}",
            callback_data="admin:setting:toggle_report",
        )
    )

    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_channels_keyboard(channels) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        mark = "🟢" if ch.is_active else "🔴"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {ch.title}",
                    callback_data=f"admin:channel:toggle:{ch.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ افزودن کانال", callback_data="admin:channel:add")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def button_columns_keyboard(back_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📏 تمام‌عرض",
                    callback_data="layout:columns:1",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="↔️ دو دکمه کنار هم",
                    callback_data="layout:columns:2",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data=back_callback,
                )
            ],
        ]
    )
