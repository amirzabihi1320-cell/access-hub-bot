from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_order_deliver_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ تحویل شد", callback_data=f"admin:order:deliver:{order_id}")]
        ]
    )
