from aiogram import F, Router
from aiogram.types import Message

from app.bot.handlers.account import build_account_view
from app.bot.handlers.shop import build_categories_view
from app.bot.keyboards.reply_menu import (
    ACCOUNT,
    CHANNEL,
    DISCOUNTS,
    HOME,
    ORDERS,
    SHOP,
    SUPPORT,
    WALLET,
    home_reply_keyboard,
    main_reply_keyboard,
)
from app.config.settings import get_settings
from app.database.base import get_session

router = Router(name="main_menu")
settings = get_settings()


async def _switch_to_home_keyboard(message: Message) -> None:
    """کیبورد ثابت را فقط به دکمه‌ی «منوی اصلی» تغییر می‌دهد."""
    await message.answer("🏠 برای بازگشت، از دکمه پایین استفاده کنید.", reply_markup=home_reply_keyboard())


@router.message(F.text == SHOP)
async def handle_shop_entry(message: Message) -> None:
    await _switch_to_home_keyboard(message)
    async with get_session() as session:
        view = await build_categories_view(session)

    if not view:
        await message.answer("فعلاً محصولی ثبت نشده.")
        return

    text, keyboard = view
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == ACCOUNT)
async def handle_account_entry(message: Message) -> None:
    await _switch_to_home_keyboard(message)
    async with get_session() as session:
        text, keyboard = await build_account_view(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == WALLET)
async def handle_wallet_entry(message: Message) -> None:
    await _switch_to_home_keyboard(message)
    await message.answer("💰 کیف پول در فاز بعدی فعال می‌شود.")


@router.message(F.text == ORDERS)
async def handle_orders_entry(message: Message) -> None:
    await _switch_to_home_keyboard(message)
    await message.answer("📦 سفارش‌های من در فاز بعدی فعال می‌شود.")


@router.message(F.text == DISCOUNTS)
async def handle_discounts_entry(message: Message) -> None:
    await _switch_to_home_keyboard(message)
    await message.answer("🎁 تخفیف‌ها در فاز بعدی فعال می‌شود.")


@router.message(F.text == SUPPORT)
async def handle_support_entry(message: Message) -> None:
    await _switch_to_home_keyboard(message)
    await message.answer("🎧 پشتیبانی در فاز بعدی فعال می‌شود.")


@router.message(F.text == CHANNEL)
async def handle_channel_entry(message: Message) -> None:
    # این یک لینک ساده است، نیازی به تغییر کیبورد ثابت ندارد.
    await message.answer(f"📢 کانال ما:\nhttps://t.me/{settings.main_channel_id.lstrip('@')}")


@router.message(F.text == HOME)
async def handle_home(message: Message) -> None:
    await message.answer(
        "🌐 <b>Access Hub</b>\n\nمنوی اصلی:",
        reply_markup=main_reply_keyboard(),
    )
