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
