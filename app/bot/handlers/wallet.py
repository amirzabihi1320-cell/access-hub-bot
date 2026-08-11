"""
فاز ۳: کیف پول کامل + Ledger + شارژ دستی + تأیید/رد ادمین.

جریان شارژ:
  کاربر مبلغ را می‌فرستد → اطلاعات پرداخت (شماره کارت و ...) نمایش داده
  می‌شود → کاربر رسید را به‌صورت عکس می‌فرستد → یک DepositRequest ساخته
  می‌شود و برای همه‌ی ادمین‌ها (ADMIN_IDS) ارسال می‌شود → ادمین تأیید/رد
  می‌کند → در صورت تأیید موجودی از طریق WalletService افزایش می‌یابد.

طبق اصل ۹ و ۵۸ سند: تأیید دوباره یک درخواست غیرممکن است (بررسی status
داخل DepositService با قفل ردیف)، و موجودی هرگز بدون Ledger تغییر نمی‌کند.
"""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.wallet import (
    admin_deposit_decision_keyboard,
    deposit_cancel_keyboard,
    wallet_back_keyboard,
    wallet_menu_keyboard,
)
from app.bot.states.wallet_states import DepositStates
from app.config.settings import get_settings
from app.core.enums import WalletTransactionType
from app.database.base import get_session
from app.models.user import User
from app.services.deposit_service import DepositAlreadyDecidedError, DepositService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.services.wallet_service import WalletService

router = Router(name="wallet")
settings = get_settings()

TX_LABELS = {
    WalletTransactionType.DEPOSIT.value: "➕ شارژ",
    WalletTransactionType.PURCHASE.value: "🛒 خرید",
    WalletTransactionType.REFUND.value: "↩️ استرداد",
    WalletTransactionType.BONUS.value: "🎁 پاداش",
    WalletTransactionType.ADMIN_ADJUSTMENT.value: "⚙️ اصلاح ادمین",
    WalletTransactionType.WITHDRAWAL.value: "➖ برداشت",
}


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


async def _get_user(session: AsyncSession, tg_user) -> User:
    return await UserService(session).get_or_create(
        tg_user.id, tg_user.username, tg_user.first_name, tg_user.last_name
    )


async def build_wallet_view(session: AsyncSession, tg_user) -> tuple[str, InlineKeyboardMarkup]:
    user = await _get_user(session, tg_user)
    text = (
        "💰 <b>کیف پول من</b>\n\n"
        f"موجودی فعلی:\n<b>{user.wallet.balance:,} تومان</b>"
    )
    return text, wallet_menu_keyboard()


# ---------- نمایش کیف پول ----------


@router.callback_query(F.data == "wallet:menu")
async def handle_wallet_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with get_session() as session:
        text, keyboard = await build_wallet_view(session, callback.from_user)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "wallet:history")
async def handle_wallet_history(callback: CallbackQuery) -> None:
    async with get_session() as session:
        user = await _get_user(session, callback.from_user)
        transactions = await WalletService(session).list_transactions(user.id, limit=10)

    if not transactions:
        text = "📜 <b>تاریخچه تراکنش‌ها</b>\n\nهنوز تراکنشی ثبت نشده."
    else:
        lines = ["📜 <b>۱۰ تراکنش اخیر</b>\n"]
        for tx in transactions:
            label = TX_LABELS.get(tx.type, tx.type)
            sign = "+" if tx.amount >= 0 else ""
            lines.append(f"{label}: {sign}{tx.amount:,} تومان → مانده: {tx.balance_after:,} تومان")
        text = "\n".join(lines)

    await callback.message.edit_text(text, reply_markup=wallet_back_keyboard())
    await callback.answer()


# ---------- شارژ دستی ----------


@router.callback_query(F.data == "wallet:deposit:start")
async def handle_deposit_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DepositStates.WAITING_AMOUNT)
    await callback.message.edit_text(
        "➕ <b>شارژ کیف پول</b>\n\nمبلغ مورد نظر را به تومان وارد کنید (فقط عدد):\n\nمثال: <code>500000</code>",
        reply_markup=deposit_cancel_keyboard(),
    )
    await callback.answer()


@router.message(DepositStates.WAITING_AMOUNT, F.text)
async def handle_deposit_amount(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", "").replace("٬", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("❗️ لطفاً فقط یک عدد صحیح و مثبت وارد کنید. مثال: 500000")
        return

    amount = int(raw)
    await state.update_data(amount=amount)
    await state.set_state(DepositStates.WAITING_RECEIPT)

    async with get_session() as session:
        settings_service = SettingsService(session)
        card_number = await settings_service.get("card_number") or "ثبت نشده"
        card_holder = await settings_service.get("card_holder_name") or "ثبت نشده"
        description = await settings_service.get("payment_description") or ""

    text = (
        "💳 <b>اطلاعات پرداخت</b>\n\n"
        f"مبلغ:\n<b>{amount:,} تومان</b>\n\n"
        f"شماره کارت:\n<code>{card_number}</code>\n\n"
        f"به نام:\n{card_holder}\n"
    )
    if description:
        text += f"\nتوضیحات:\n{description}\n"
    text += "\n📤 بعد از واریز، عکس رسید پرداخت را همینجا ارسال کنید."

    await message.answer(text, reply_markup=deposit_cancel_keyboard())


@router.message(DepositStates.WAITING_RECEIPT, F.photo)
async def handle_deposit_receipt(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    amount = data.get("amount")
    if not amount:
        await state.clear()
        await message.answer("❗️ مشکلی پیش آمد، لطفاً دوباره از کیف پول شروع کنید.")
        return

    file_id = message.photo[-1].file_id

    async with get_session() as session:
        user = await _get_user(session, message.from_user)
        deposit_service = DepositService(session)
        request = await deposit_service.create_request(user.id, amount)
        await deposit_service.attach_receipt(request.id, file_id)

    await state.clear()
    await message.answer(
        "✅ رسید شما دریافت شد.\n\nدرخواست شارژ کیف پول برای بررسی برای ادمین ارسال شد. "
        "به‌محض تأیید، موجودی شما به‌روزرسانی و به شما اطلاع داده می‌شود.",
        reply_markup=wallet_back_keyboard(),
    )

    username = f"@{message.from_user.username}" if message.from_user.username else "—"
    caption = (
        "💰 <b>درخواست شارژ کیف پول</b>\n\n"
        f"کاربر: {username}\n"
        f"Telegram ID: <code>{message.from_user.id}</code>\n\n"
        f"مبلغ: <b>{amount:,} تومان</b>\n"
        f"شماره درخواست: #{request.id}"
    )
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=caption,
                reply_markup=admin_deposit_decision_keyboard(request.id),
            )
        except Exception:
            # اگر ادمین بات را استارت نکرده باشد یا پیام قابل ارسال نباشد،
            # نباید کل فرآیند کاربر را متوقف کند.
            continue


@router.message(DepositStates.WAITING_RECEIPT)
async def handle_deposit_receipt_wrong_type(message: Message) -> None:
    await message.answer("📤 لطفاً رسید پرداخت را به‌صورت «عکس» ارسال کنید.")


# ---------- تصمیم ادمین ----------


@router.callback_query(F.data.startswith("admin:deposit:approve:"))
async def handle_admin_approve(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[3])

    async with get_session() as session:
        deposit_service = DepositService(session)
        try:
            request = await deposit_service.approve(request_id, callback.from_user.id)
        except DepositAlreadyDecidedError:
            await callback.answer("این درخواست قبلاً بررسی شده است.", show_alert=True)
            return

        new_balance = await WalletService(session).get_balance(request.user_id)
        target_user = await session.get(User, request.user_id)

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>تأیید شد</b>",
        reply_markup=None,
    )
    await callback.answer("تأیید شد ✅")

    if target_user:
        try:
            await callback.bot.send_message(
                chat_id=target_user.telegram_id,
                text=(
                    "✅ <b>شارژ کیف پول تأیید شد</b>\n\n"
                    f"مبلغ {request.amount:,} تومان به کیف پول شما اضافه شد.\n"
                    f"موجودی جدید: <b>{new_balance:,} تومان</b>"
                ),
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("admin:deposit:reject:"))
async def handle_admin_reject(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[3])

    async with get_session() as session:
        deposit_service = DepositService(session)
        try:
            request = await deposit_service.reject(request_id, callback.from_user.id)
        except DepositAlreadyDecidedError:
            await callback.answer("این درخواست قبلاً بررسی شده است.", show_alert=True)
            return
        target_user = await session.get(User, request.user_id)

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>رد شد</b>",
        reply_markup=None,
    )
    await callback.answer("رد شد ❌")

    if target_user:
        try:
            await callback.bot.send_message(
                chat_id=target_user.telegram_id,
                text=(
                    "❌ <b>درخواست شارژ کیف پول رد شد</b>\n\n"
                    f"مبلغ: {request.amount:,} تومان\n"
                    "در صورت اشتباه، با پشتیبانی تماس بگیرید."
                ),
            )
        except Exception:
            pass
