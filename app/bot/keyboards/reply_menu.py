from aiogram.enums import ButtonStyle
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SHOP = "🛍 فروشگاه"
WALLET = "💰 کیف پول"
ORDERS = "📦 سفارش‌های من"
LEADERBOARD = "🏆 لیدربرد"
TOURNAMENTS = "🎫 تورنومنت‌ها"
ACCOUNT = "👤 حساب کاربری"
SUPPORT = "🎧 پشتیبانی"
CHANNEL = "📢 کانال ما"
HOME = "🏠 منوی اصلی"
CHECKIN = "📅 چک-این روزانه"


def main_reply_keyboard(icons: dict[str, str] | None = None) -> ReplyKeyboardMarkup:
    # از استایل واقعی تلگرام (Bot API 9.4) استفاده می‌کنیم: سه رنگ رسمی
    # danger (قرمز)، success (سبز) و primary (آبی). فروشگاه (مهم‌ترین ورودی)
    # تمام‌عرض و آبیه؛ کیف‌پول/چک-این (ارزش‌آفرین) سبزن؛ بقیه رنگ پیش‌فرض تم.
    #
    # icons (اختیاری): آیدی ایموجی پریمیوم، کلیدها: icon_shop/icon_wallet/
    # icon_checkin/icon_leaderboard. فقط وقتی سازنده‌ی ربات Premium داشته باشد
    # واقعاً نمایش داده می‌شود (محدودیت خودِ تلگرام).
    icons = icons or {}
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SHOP, style=ButtonStyle.PRIMARY, icon_custom_emoji_id=icons.get("icon_shop"))],
            [
                KeyboardButton(text=WALLET, style=ButtonStyle.SUCCESS, icon_custom_emoji_id=icons.get("icon_wallet")),
                KeyboardButton(text=CHECKIN, style=ButtonStyle.SUCCESS, icon_custom_emoji_id=icons.get("icon_checkin")),
            ],
            [KeyboardButton(text=ORDERS), KeyboardButton(text=LEADERBOARD, style=ButtonStyle.SUCCESS, icon_custom_emoji_id=icons.get("icon_leaderboard"))],
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
