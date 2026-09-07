from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.pricing_service import is_discount_active

EDITABLE_SETTINGS = {
    "welcome_text": "📝 متن خوشامدگویی",
    "payment_info": "💳 اطلاعات پرداخت",
    "token_transfer_fee_percent": "💎 کارمزد انتقال Token (%)",
    "referral_cashback_percent": "👥 درصد پاداش رفرال (کش‌بک معرف)",
    "token_purchase_price": "🪙 قیمت خرید هر Token (تومان)",
    "shop_category_button_columns": "📂 چیدمان دکمه دسته‌بندی (۱/۲)",
    "shop_product_button_columns": "🛍 چیدمان دکمه محصول (۱/۲)",
    "join_bonus_amount": "🎁 مقدار پاداش عضویت (Token)",
    "referral_invite_bonus_amount": "🤝 مقدار پاداش دعوت دوست (Token)",
    "daily_checkin_amount": "📅 مقدار پاداش چک-این روزانه (Token)",
    "weekly_leaderboard_reward_top1": "🥇 جایزه نفر اول لیدربرد هفتگی",
    "weekly_leaderboard_reward_top2": "🥈 جایزه نفر دوم لیدربرد هفتگی",
    "weekly_leaderboard_reward_top3": "🥉 جایزه نفر سوم لیدربرد هفتگی",
    "sticker_welcome": "🎉 استیکر خوش‌آمدگویی (/start)",
    "sticker_checkin": "📅 استیکر چک-این روزانه",
    "sticker_purchase_success": "✅ استیکر خرید موفق",
    "icon_shop": "🛍 آیکون پریمیوم دکمه فروشگاه",
    "icon_wallet": "💰 آیکون پریمیوم دکمه کیف پول",
    "icon_checkin": "📅 آیکون پریمیوم دکمه چک-این",
    "icon_leaderboard": "🏆 آیکون پریمیوم دکمه لیدربرد",
    "support_contact": "🎧 آیدی/لینک پشتیبانی",
}



def admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    """
    پنل ادمین گروه‌بندی‌شده، دوستونه، و با رنگ‌های واقعی تلگرام (Bot API 9.4):
    قرمز = نیازمند رسیدگی فوری، سبز = مدیریت کاتالوگ، آبی = بقیه‌ی موارد.
    """
    rows = [
        [InlineKeyboardButton(text="📊 آمار فروش", callback_data="admin:stats", style=ButtonStyle.PRIMARY)],
        [
            InlineKeyboardButton(text="🛍 محصولات", callback_data="admin:products", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text="📂 دسته‌بندی‌ها", callback_data="admin:categories", style=ButtonStyle.SUCCESS),
        ],
        [
            InlineKeyboardButton(text="📦 سفارش‌های در انتظار", callback_data="admin:orders", style=ButtonStyle.DANGER),
            InlineKeyboardButton(text="💳 درخواست‌های شارژ", callback_data="admin:deposits", style=ButtonStyle.DANGER),
        ],
        [
            InlineKeyboardButton(text="🎟 کدهای تخفیف", callback_data="admin:coupons", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text="👤 مدیریت کاربران", callback_data="admin:users", style=ButtonStyle.PRIMARY),
        ],
        [
            InlineKeyboardButton(text="📢 عضویت اجباری", callback_data="admin:channels", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text="🏆 تورنومنت‌ها", callback_data="admin:tournaments", style=ButtonStyle.PRIMARY),
        ],
        [
            InlineKeyboardButton(text="🔐 پنل‌های VPN", callback_data="admin:vpn_panels", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text="₮ پرداخت ارز دیجیتال", callback_data="admin:payment_providers", style=ButtonStyle.PRIMARY),
        ],
        [
            InlineKeyboardButton(text="📣 پیام همگانی", callback_data="admin:broadcast", style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin:settings", style=ButtonStyle.PRIMARY),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


def admin_category_style_keyboard(category_id: int, current: str | None = None) -> InlineKeyboardMarkup:
    current = (current or "success").lower()
    def mark(style: str) -> str:
        return "✅ " if current == style else ""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{mark('primary')}🔵 آبی", callback_data=f"admin:category:style:{category_id}:primary", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(text=f"{mark('success')}🟢 سبز", callback_data=f"admin:category:style:{category_id}:success", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton(text=f"{mark('danger')}🔴 قرمز", callback_data=f"admin:category:style:{category_id}:danger", style=ButtonStyle.DANGER),
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:categories")],
        ]
    )


def admin_product_style_keyboard(product_id: int, current: str | None = None) -> InlineKeyboardMarkup:
    current = (current or "primary").lower()
    def mark(style: str) -> str:
        return "✅ " if current == style else ""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{mark('primary')}🔵 آبی", callback_data=f"admin:product:style:{product_id}:primary", style=ButtonStyle.PRIMARY),
                InlineKeyboardButton(text=f"{mark('success')}🟢 سبز", callback_data=f"admin:product:style:{product_id}:success", style=ButtonStyle.SUCCESS),
                InlineKeyboardButton(text=f"{mark('danger')}🔴 قرمز", callback_data=f"admin:product:style:{product_id}:danger", style=ButtonStyle.DANGER),
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
            [InlineKeyboardButton(
                text=("🔐 تحویل خودکار VPN: فعال (تنظیم)" if product.is_vpn_product else "🔐 فعال‌سازی تحویل خودکار VPN"),
                callback_data=f"admin:product:vpn:{product.id}",
                style=ButtonStyle.SUCCESS if product.is_vpn_product else ButtonStyle.PRIMARY,
            )],
            [InlineKeyboardButton(text="🗑 حذف محصول", callback_data=f"admin:product:del:{product.id}", style=ButtonStyle.DANGER)],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:products", style=ButtonStyle.DANGER)],
        ]
    )


def admin_product_vpn_keyboard(product) -> InlineKeyboardMarkup:
    toggle_text = "⛔️ غیرفعال کردن تحویل خودکار VPN" if product.is_vpn_product else "✅ فعال کردن تحویل خودکار VPN"
    limit_text = f"📶 حجم: {product.vpn_data_limit_gb} GB" if product.vpn_data_limit_gb else "📶 حجم: نامحدود (تغییر)"
    duration_text = f"📅 مدت: {product.vpn_duration_days} روز" if product.vpn_duration_days else "📅 مدت: نامحدود (تغییر)"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:product:vpn:toggle:{product.id}")],
            [InlineKeyboardButton(text=limit_text, callback_data=f"admin:product:vpn:limit:{product.id}")],
            [InlineKeyboardButton(text=duration_text, callback_data=f"admin:product:vpn:duration:{product.id}")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data=f"admin:product:view:{product.id}")],
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


def admin_settings_keyboard(
    report_enabled: bool = True,
    join_bonus_enabled: bool = False,
    referral_cashback_enabled: bool = True,
    referral_invite_bonus_enabled: bool = False,
    daily_checkin_enabled: bool = False,
    weekly_leaderboard_reward_enabled: bool = False,
) -> InlineKeyboardMarkup:
    # مقادیر قابل‌ویرایش (متن/عدد)، دوستونه، آبی (چون همیشه یک اکشن خنثی هستند)
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"admin:setting:edit:{key}", style=ButtonStyle.PRIMARY)
        for key, label in EDITABLE_SETTINGS.items()
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    # کلیدهای فعال/غیرفعال‌سازی، دوستونه؛ رنگ دکمه (سبز/قرمز) خودش نشانگر
    # وضعیت روشن/خاموش است، ایموجی هم برای وضوح بیشتر نگه داشته شده.
    def _toggle_style(enabled: bool) -> ButtonStyle:
        return ButtonStyle.SUCCESS if enabled else ButtonStyle.DANGER

    report_mark = "🟢" if report_enabled else "🔴"
    join_mark = "🟢" if join_bonus_enabled else "🔴"
    cashback_mark = "🟢" if referral_cashback_enabled else "🔴"
    invite_mark = "🟢" if referral_invite_bonus_enabled else "🔴"
    checkin_mark = "🟢" if daily_checkin_enabled else "🔴"
    leaderboard_mark = "🟢" if weekly_leaderboard_reward_enabled else "🔴"

    rows.append([
        InlineKeyboardButton(text=f"📢 گزارش سفارش {report_mark}", callback_data="admin:setting:toggle_report", style=_toggle_style(report_enabled)),
        InlineKeyboardButton(text=f"🎁 پاداش عضویت {join_mark}", callback_data="admin:setting:toggle_join_bonus", style=_toggle_style(join_bonus_enabled)),
    ])
    rows.append([
        InlineKeyboardButton(text=f"👥 کش‌بک رفرال {cashback_mark}", callback_data="admin:setting:toggle_referral_cashback", style=_toggle_style(referral_cashback_enabled)),
        InlineKeyboardButton(text=f"🤝 پاداش دعوت {invite_mark}", callback_data="admin:setting:toggle_referral_invite_bonus", style=_toggle_style(referral_invite_bonus_enabled)),
    ])
    rows.append([
        InlineKeyboardButton(text=f"📅 چک-این روزانه {checkin_mark}", callback_data="admin:setting:toggle_daily_checkin", style=_toggle_style(daily_checkin_enabled)),
        InlineKeyboardButton(text=f"🏆 لیدربرد هفتگی {leaderboard_mark}", callback_data="admin:setting:toggle_weekly_leaderboard", style=_toggle_style(weekly_leaderboard_reward_enabled)),
    ])

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


HEALTH_ICONS = {
    "ONLINE": "🟢",
    "DEGRADED": "🟡",
    "OFFLINE": "🔴",
    "UNKNOWN": "⚪️",
}


def admin_vpn_panels_keyboard(panels) -> InlineKeyboardMarkup:
    rows = []
    for panel in panels:
        status_mark = "🟢" if panel.status == "ACTIVE" else "⛔️"
        health_mark = HEALTH_ICONS.get(panel.last_health_status, "⚪️")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{status_mark}{health_mark} {panel.name} ({panel.panel_type})",
                    callback_data=f"admin:vpn_panel:view:{panel.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ افزودن پنل VPN", callback_data="admin:vpn_panel:add")])
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_vpn_panel_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Marzban", callback_data="admin:vpn_panel:add:type:MARZBAN")],
            [InlineKeyboardButton(text="Sanaei / 3x-UI", callback_data="admin:vpn_panel:add:type:SANAEI")],
            [InlineKeyboardButton(text="🔙 انصراف", callback_data="admin:vpn_panels")],
        ]
    )


def admin_vpn_panel_detail_keyboard(panel) -> InlineKeyboardMarkup:
    toggle_text = "⛔️ غیرفعال کن" if panel.status == "ACTIVE" else "🟢 فعال کن"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 تست اتصال", callback_data=f"admin:vpn_panel:test:{panel.id}")],
            [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:vpn_panel:toggle:{panel.id}")],
            [InlineKeyboardButton(text="🗑 حذف پنل", callback_data=f"admin:vpn_panel:del:{panel.id}")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:vpn_panels")],
        ]
    )


def admin_vpn_panel_delete_confirm_keyboard(panel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ بله، حذف کن", callback_data=f"admin:vpn_panel:delyes:{panel_id}"),
                InlineKeyboardButton(text="❌ انصراف", callback_data=f"admin:vpn_panel:view:{panel_id}"),
            ]
        ]
    )


# ---------- Payment Providers (ماژول اضافه: TRON PAYMENT) ----------


def admin_payment_providers_keyboard(configs, unconfigured_types: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for config in configs:
        status_mark = "🟢" if config.status == "ACTIVE" else "⛔️"
        health_mark = HEALTH_ICONS.get(config.last_health_status, "⚪️")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{status_mark}{health_mark} {config.provider_type}",
                    callback_data=f"admin:payment_provider:view:{config.id}",
                )
            ]
        )
    for provider_type in unconfigured_types:
        rows.append(
            [InlineKeyboardButton(text=f"➕ افزودن {provider_type}", callback_data=f"admin:payment_provider:add:{provider_type}")]
        )
    rows.append([InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payment_provider_detail_keyboard(config) -> InlineKeyboardMarkup:
    toggle_text = "⛔️ غیرفعال کن" if config.status == "ACTIVE" else "🟢 فعال کن"
    auto_verify_text = f"🔁 Auto Verify: {'🟢 روشن' if config.auto_verify else '🔴 خاموش'}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 تست اتصال", callback_data=f"admin:payment_provider:test:{config.id}")],
            [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:payment_provider:toggle:{config.id}")],
            [InlineKeyboardButton(text=auto_verify_text, callback_data=f"admin:payment_provider:toggle_auto:{config.id}")],
            [
                InlineKeyboardButton(text="✏️ ویرایش API URL", callback_data=f"admin:payment_provider:edit_url:{config.id}"),
                InlineKeyboardButton(text="✏️ ویرایش API Key", callback_data=f"admin:payment_provider:edit_key:{config.id}"),
            ],
            [InlineKeyboardButton(text="🗑 حذف", callback_data=f"admin:payment_provider:del:{config.id}")],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin:payment_providers")],
        ]
    )


def admin_payment_provider_delete_confirm_keyboard(config_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ بله، حذف کن", callback_data=f"admin:payment_provider:delyes:{config_id}"),
                InlineKeyboardButton(text="❌ انصراف", callback_data=f"admin:payment_provider:view:{config_id}"),
            ]
        ]
    )


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
