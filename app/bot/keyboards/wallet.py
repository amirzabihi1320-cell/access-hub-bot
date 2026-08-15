from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def wallet_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 شارژ ریالی",
                    callback_data="wallet:deposit:rial",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🪙 شارژ توکن",
                    callback_data="wallet:deposit:token",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 تاریخچه تراکنش",
                    callback_data="wallet:history",
                )
            ],
        ]
    )


def wallet_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="wallet:menu",
                )
            ]
        ]
    )


def deposit_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 لغو",
                    callback_data="wallet:menu",
                )
            ]
        ]
    )


def admin_deposit_decision_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید",
                    callback_data=f"admin:deposit:approve:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ رد",
                    callback_data=f"admin:deposit:reject:{request_id}",
                ),
            ]
        ]
    )
