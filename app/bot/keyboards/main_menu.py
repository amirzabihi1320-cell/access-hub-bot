from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    در فازهای بعد، متن دکمه‌ها هم از دیتابیس (text_templates) خوانده می‌شود.
    فعلاً برای فاز ۰ به‌صورت ثابت است تا ربات قابل اجرا باشد.
    """
    buttons = [
        [InlineKeyboardButton(text="🛍 فروشگاه", callback_data="menu:shop")],
        [InlineKeyboardButton(text="💰 کیف پول", callback_data="menu:wallet")],
        [InlineKeyboardButton(text="📦 سفارش‌های من", callback_data="menu:orders")],
        [InlineKeyboardButton(text="🎁 تخفیف‌ها", callback_data="menu:discounts")],
        [
            InlineKeyboardButton(text="👤 حساب کاربری", callback_data="menu:account"),
            InlineKeyboardButton(text="🎧 پشتیبانی", callback_data="menu:support"),
        ],
        [InlineKeyboardButton(text="📢 کانال ما", url="https://t.me/AccessHubMarket")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
