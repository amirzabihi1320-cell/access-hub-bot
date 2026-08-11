from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SHOP = "🛍 فروشگاه"
WALLET = "💰 کیف پول"
ORDERS = "📦 سفارش‌های من"
DISCOUNTS = "🎁 تخفیف‌ها"
ACCOUNT = "👤 حساب کاربری"
SUPPORT = "🎧 پشتیبانی"
CHANNEL = "📢 کانال ما"
HOME = "🏠 منوی اصلی"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد ثابت کامل - فقط توی صفحه‌ی اصلی نمایش داده می‌شود."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SHOP), KeyboardButton(text=WALLET)],
            [KeyboardButton(text=ORDERS), KeyboardButton(text=DISCOUNTS)],
            [KeyboardButton(text=ACCOUNT), KeyboardButton(text=SUPPORT)],
            [KeyboardButton(text=CHANNEL)],
        ],
        resize_keyboard=True,
    )


def home_reply_keyboard() -> ReplyKeyboardMarkup:
    """وقتی کاربر وارد هر بخشی می‌شود، کیبورد ثابت فقط همین یک دکمه را نشان می‌دهد."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=HOME)]],
        resize_keyboard=True,
    )
