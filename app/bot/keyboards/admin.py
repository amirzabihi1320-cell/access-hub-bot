from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

EDITABLE_SETTINGS = {
    "shop_name": "نام فروشگاه",
    "welcome_text": "متن خوشامدگویی (صفحه اصلی)",
    "card_number": "شماره کارت",
    "card_holder_name": "به نام (صاحب کارت)",
    "payment_description": "توضیحات پرداخت",
    "shop_buttons_per_row": "تعداد دکمه در هر ردیف فروشگاه (۱ تا ۳)",
    "game_chat_link": "🔗 لینک گپ بازی",
    "token_transfer_fee_percent": "💎 کارمزد انتقال Token (%)",
    "membership_requirement": "📢 حالت عضویت اجباری",
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
        ]
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")]]
    )


def admin_categories_keyboard(categories) -> InlineKeyboardMarkup:
    rows = []
    for c in categories:
        mark = "🟢" if c.status else "🔴"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {c.icon or ''} {c.name}", callback_data=f"admin:category:toggle:{c.id}"
                ),
                InlineKeyboardButton(text="🗑", callback_data=f"admin:category:del:{c.id}"),
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


def admin_product_detail_keyboard(product) -> InlineKeyboardMarkup:
    mark = "🔴 غیرفعال کن" if product.status else "🟢 فعال کن"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 تغییر قیمت", callback_data=f"admin:product:price:{product.id}")],
            [InlineKeyboardButton(text=mark, callback_data=f"admin:product:toggle:{product.id}")],
            [InlineKeyboardButton(text="🗑 حذف محصول", callback_data=f"admin:product:del:{product.id}")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:products")],
        ]
    )


def admin_settings_keyboard(report_enabled: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"admin:setting:edit:{key}")]
        for key, label in EDITABLE_SETTINGS.items()
    ]
    report_mark = "🟢 فعال" if report_enabled else "🔴 غیرفعال"
    rows.append(
        [InlineKeyboardButton(text=f"📢 گزارش سفارش در کانال: {report_mark}", callback_data="admin:setting:toggle_report")]
    )
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
                )
            ],
            [
                InlineKeyboardButton(
                    text="↔️ دو دکمه کنار هم",
                    callback_data="layout:columns:2",
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
