from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.account import build_account_view, build_referral_view
from app.bot.handlers.orders import build_orders_view
from app.bot.handlers.shop import build_categories_view
from app.bot.handlers.wallet import build_wallet_view
from app.bot.keyboards.reply_menu import (
    ACCOUNT,
    CHANNEL,
    DISCOUNTS,
    HOME,
    ORDERS,
    REFERRAL,
    SHOP,
    SUPPORT,
    WALLET,
    home_reply_keyboard,
    main_reply_keyboard,
)
from app.config.settings import get_settings
from app.database.base import get_session
from app.services.settings_service import SettingsService
from app.utils.message_manager import MessageManager

router = Router(name="main_menu")
settings = get_settings()


async def _switch_to_home_keyboard(message: Message) -> None:
    """
    کیبورد ثابت پایین صفحه را فقط به دکمه‌ی «منوی اصلی» تغییر می‌دهد.
    تلگرام برای تغییر کیبورد ثابت نیاز به ارسال یک پیام دارد، اما خودِ آن
    پیام («🏠») چیزی نیست که کاربر باید ببیند؛ به همین دلیل بلافاصله بعد
    از ارسال حذف می‌شود. حذف پیام، کیبورد ثابتی که همین پیام تنظیم کرده را
    از پایین صفحه پاک نمی‌کند (رفتار استاندارد تلگرام است).
    """
    sent = await message.answer("🏠", reply_markup=home_reply_keyboard())
    try:
        await message.bot.delete_message(message.chat.id, sent.message_id)
    except Exception:
        pass


async def _welcome_text() -> str:
    async with get_session() as session:
        shop_name = await SettingsService(session).get("shop_name")
        welcome_text = await SettingsService(session).get("welcome_text") or ""
    try:
        welcome_text = welcome_text.format(shop_name=shop_name)
    except (KeyError, IndexError):
        pass
    return f"🌐 <b>{shop_name}</b>\n\n{welcome_text}" if welcome_text else f"🌐 <b>{shop_name}</b>"


@router.message(F.text == SHOP)
async def handle_shop_entry(message: Message, state: FSMContext) -> None:
    await _switch_to_home_keyboard(message)
    manager = MessageManager(message.bot, message.chat.id, state)
    async with get_session() as session:
        view = await build_categories_view(session)

    if not view:
        await manager.send("فعلاً محصولی ثبت نشده.")
        return

    text, keyboard = view
    await manager.send(text, reply_markup=keyboard)


@router.message(F.text == ACCOUNT)
async def handle_account_entry(message: Message, state: FSMContext) -> None:
    await _switch_to_home_keyboard(message)
    manager = MessageManager(message.bot, message.chat.id, state)
    async with get_session() as session:
        text = await build_account_view(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    await manager.send(text)


@router.message(F.text == REFERRAL)
async def handle_referral_entry(message: Message, state: FSMContext) -> None:
    await _switch_to_home_keyboard(message)
    manager = MessageManager(message.bot, message.chat.id, state)
    async with get_session() as session:
        text = await build_referral_view(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    await manager.send(text)


@router.message(F.text == WALLET)
async def handle_wallet_entry(message: Message, state: FSMContext) -> None:
    await _switch_to_home_keyboard(message)
    manager = MessageManager(message.bot, message.chat.id, state)
    async with get_session() as session:
        text, keyboard = await build_wallet_view(session, message.from_user)
    await manager.send(text, reply_markup=keyboard)


@router.message(F.text == ORDERS)
async def handle_orders_entry(message: Message, state: FSMContext) -> None:
    await _switch_to_home_keyboard(message)
    manager = MessageManager(message.bot, message.chat.id, state)
    async with get_session() as session:
        text = await build_orders_view(session, message.from_user)
    await manager.send(text)


@router.message(F.text == DISCOUNTS)
async def handle_discounts_entry(message: Message, state: FSMContext) -> None:
    await _switch_to_home_keyboard(message)
    manager = MessageManager(message.bot, message.chat.id, state)
    await manager.send("🎁 تخفیف‌ها در فاز بعدی فعال می‌شود.")


@router.message(F.text == SUPPORT)
async def handle_support_entry(message: Message, state: FSMContext) -> None:
    await _switch_to_home_keyboard(message)
    manager = MessageManager(message.bot, message.chat.id, state)
    await manager.send("🎧 پشتیبانی در فاز بعدی فعال می‌شود.")


@router.message(F.text == CHANNEL)
async def handle_channel_entry(message: Message) -> None:
    # این یک لینک ساده است، نیازی به تغییر کیبورد ثابت ندارد.
    await message.answer(f"📢 کانال ما:\nhttps://t.me/{settings.main_channel_id.lstrip('@')}")


@router.message(F.text == HOME)
async def handle_home(message: Message, state: FSMContext) -> None:
    manager = MessageManager(message.bot, message.chat.id, state)
    await manager.cleanup_temp()
    text = await _welcome_text()
    await message.answer(text, reply_markup=main_reply_keyboard())
