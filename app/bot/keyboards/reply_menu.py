from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SHOP = "🛍 فروشگاه"
WALLET = "💰 کیف پول"
ORDERS = "📦 سفارش‌های من"
DISCOUNTS = "🎁 تخفیف‌ها"
TOURNAMENTS = "🏆 تورنومنت‌ها"
ACCOUNT = "👤 حساب کاربری"
SUPPORT = "🎧 پشتیبانی"
CHANNEL = "📢 کانال ما"
HOME = "🏠 منوی اصلی"


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SHOP), KeyboardButton(text=WALLET)],
            [KeyboardButton(text=ORDERS), KeyboardButton(text=DISCOUNTS)],
            [KeyboardButton(text=TOURNAMENTS), KeyboardButton(text=ACCOUNT)],
            [KeyboardButton(text=SUPPORT), KeyboardButton(text=CHANNEL)],
        ],
        resize_keyboard=True,
    )


def home_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=HOME)],
        ],
        resize_keyboard=True,
    )
