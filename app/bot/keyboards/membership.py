from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.required_channel import RequiredChannel


def membership_keyboard(channels: list[RequiredChannel]) -> InlineKeyboardMarkup:
    buttons = []
    for channel in channels:
        url = channel.invite_link or f"https://t.me/{channel.username.lstrip('@')}"
        buttons.append([InlineKeyboardButton(text=f"📢 عضویت در {channel.title}", url=url)])

    buttons.append([InlineKeyboardButton(text="✅ بررسی عضویت", callback_data="membership:check")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
