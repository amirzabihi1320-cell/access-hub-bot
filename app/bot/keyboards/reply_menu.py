from aiogram.enums import ButtonStyle
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

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


def _plain_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """
    نسخه‌ی بدون رنگ/آیکون، فقط برای Fallback: اگر ارسال کیبورد رنگی به هر
    دلیلی (مثلاً یک مشکل موقت سمت تلگرام با استایل دکمه) با خطا مواجه شد،
    حداقل خودِ منو (بدون تزئین) برای کاربر نمایش داده می‌شود.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SHOP)],
            [KeyboardButton(text=WALLET), KeyboardButton(text=CHECKIN)],
            [KeyboardButton(text=ORDERS), KeyboardButton(text=LEADERBOARD)],
            [KeyboardButton(text=TOURNAMENTS), KeyboardButton(text=ACCOUNT)],
            [KeyboardButton(text=SUPPORT), KeyboardButton(text=CHANNEL)],
        ],
        resize_keyboard=True,
    )


async def answer_with_main_menu(message: Message, text: str, icons: dict[str, str] | None = None) -> Message:
    """
    جایگزین امن ``message.answer(text, reply_markup=main_reply_keyboard(...))``:
    اول نسخه‌ی رنگی/با‌آیکون را امتحان می‌کند؛ اگر تلگرام آن را رد کرد
    (TelegramBadRequest)، بدون کرش کردن، همان لحظه با نسخه‌ی ساده دوباره
    امتحان می‌کند تا کاربر همیشه منو را ببیند.
    """
    try:
        return await message.answer(text, reply_markup=main_reply_keyboard(icons))
    except TelegramBadRequest:
        return await message.answer(text, reply_markup=_plain_main_reply_keyboard())


def home_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=HOME)],
        ],
        resize_keyboard=True,
    )
