"""
ابزار عمومی چیدمان دکمه‌های شیشه‌ای (Inline Keyboard).

هدف: امکان انتخاب «تعداد دکمه در هر ردیف» از تنظیمات ادمین، تا وقتی
متن دکمه‌ها (مثلاً نام محصول) نسبتاً طولانی است، ادمین بتواند تعداد
ستون را کم کند (مثلاً ۱ در هر ردیف) تا دکمه‌ها کوچک/فشرده نشوند، یا
برای متن‌های کوتاه تعداد ستون را زیاد کند تا فضای کمتری اشغال شود.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton

DEFAULT_COLUMNS = 1
MIN_COLUMNS = 1
MAX_COLUMNS = 2


def clamp_columns(value: int | str | None) -> int:
    """مقدار خام تنظیمات را به یک عدد معتبر بین ۱ تا ۲ تبدیل می‌کند."""
    try:
        columns = int(value)
    except (TypeError, ValueError):
        return DEFAULT_COLUMNS
    return max(MIN_COLUMNS, min(MAX_COLUMNS, columns))


def chunk_buttons(buttons: list[InlineKeyboardButton], columns: int = DEFAULT_COLUMNS) -> list[list[InlineKeyboardButton]]:
    """یک لیست تخت از دکمه‌ها را به ردیف‌هایی با طول `columns` تقسیم می‌کند."""
    columns = clamp_columns(columns)
    return [buttons[i : i + columns] for i in range(0, len(buttons), columns)]


# کاراکتر بریلِ خالی (U+2800): در اکثر فونت‌ها کاملاً نامرئی است ولی عرض
# واقعی دارد، برخلاف space معمولی که تلگرام در انتهای خط حذفش می‌کند.
_WIDTH_PAD_CHAR = "\u2800"


def pad_message_width(text: str, min_chars: int = 60) -> str:
    """
    عرض حبابِ پیام (و در نتیجه عرض دکمه‌های شیشه‌ای چسبیده به آن) در
    تلگرام بر اساس عرضِ متنِ پیام تعیین می‌شود، نه عرض صفحه گوشی. برای
    پیام‌های کوتاه (مثلاً فقط عنوان یک دسته‌بندی)، حباب کوچک می‌ماند و
    دکمه‌ها هم به همان اندازه‌ی کوچکِ حباب محدود می‌شوند — حتی اگر هرکدام
    در ردیف مستقل خودشان باشند.

    این تابع یک خط نامرئیِ انتهایی به «متن پیام» اضافه می‌کند تا عرض
    حباب به حداقلِ لازم برسد و دکمه‌ها واقعاً تمام‌عرض دربیایند. باید روی
    متنِ پیام اعمال شود، نه متنِ دکمه (که تأثیری روی عرض حباب ندارد).
    """
    text = text or ""
    return f"{text}\n{_WIDTH_PAD_CHAR * min_chars}"
