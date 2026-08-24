from aiogram.enums import ButtonStyle
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
CHECKIN = "📅 چک-این روزانه"


def main_reply_keyboard(icons: dict[str, str] | None = None) -> ReplyKeyboardMarkup:
    # از استایل واقعی تلگرام (Bot API 9.4) استفاده می‌کنیم: سه رنگ رسمی
    # danger (قرمز)، success (سبز) و primary (آبی). دکمه‌های «ارزش‌آفرین»
    # (کیف پول، چک-این، تخفیف‌ها) سبزن تا چشم رو جلب کنن، فروشگاه آبیه
    # چون مهم‌ترین نقطه‌ی ورودیه، بقیه بدون استایل صریح (رنگ تمِ خودِ کاربر).
    #
    # icons (اختیاری): آیدی ایموجی پریمیوم برای هرکدام از ۴ دکمه‌ی بالا،
    # با کلیدهای icon_shop/icon_wallet/icon_checkin/icon_discounts. این
    # فقط وقتی واقعاً روی گوشی کاربر نمایش داده می‌شود که سازنده‌ی ربات
    # اشتراک Telegram Premium داشته باشد (محدودیت خودِ تلگرام)، وگرنه
    # تلگرام بی‌صدا آن را نادیده می‌گیرد.
    icons = icons or {}
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=SHOP, style=ButtonStyle.PRIMARY, icon_custom_emoji_id=icons.get("icon_shop")),
                KeyboardButton(text=WALLET, style=ButtonStyle.SUCCESS, icon_custom_emoji_id=icons.get("icon_wallet")),
            ],
            [
                KeyboardButton(text=CHECKIN, style=ButtonStyle.SUCCESS, icon_custom_emoji_id=icons.get("icon_checkin")),
                KeyboardButton(text=DISCOUNTS, style=ButtonStyle.SUCCESS, icon_custom_emoji_id=icons.get("icon_discounts")),
            ],
            [KeyboardButton(text=ORDERS), KeyboardButton(text=TOURNAMENTS)],
            [KeyboardButton(text=ACCOUNT), KeyboardButton(text=SUPPORT)],
            [KeyboardButton(text=CHANNEL)],
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
