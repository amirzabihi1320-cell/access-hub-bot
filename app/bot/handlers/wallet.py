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
from app.services.deposit_service import (
    DepositAlreadyDecidedError,
    DepositService,
)
from app.services.game_service import TokenService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.services.wallet_service import WalletService

router = Router(name="wallet")
router.message.filter(F.chat.type == "private")
settings = get_settings()


TX_LABELS = {
    WalletTransactionType.DEPOSIT.value: "➕ شارژ ریالی",
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
        tg_user.id,
        tg_user.username,
        tg_user.first_name,
        tg_user.last_name,
    )


async def build_wallet_view(
    session: AsyncSession,
    tg_user,
) -> tuple[str, InlineKeyboardMarkup]:

    user = await _get_user(session, tg_user)

    text = (
        "💰 <b>کیف پول من</b>\n\n"
        f"💳 موجودی ریالی:\n"
        f"<b>{user.wallet.balance:,} تومان</b>\n\n"
        f"🪙 موجودی Access Token:\n"
        f"<b>{user.token_balance:,} Token</b>"
    )

    return text, wallet_menu_keyboard()


# =========================================================
# نمایش کیف پول
# =========================================================


@router.callback_query(F.data == "wallet:menu")
async def handle_wallet_menu(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    await state.clear()

    async with get_session() as session:
        text, keyboard = await build_wallet_view(
            session,
            callback.from_user,
        )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(F.data == "wallet:history")
async def handle_wallet_history(
    callback: CallbackQuery,
) -> None:

    async with get_session() as session:
        user = await _get_user(
            session,
            callback.from_user,
        )

        transactions = await WalletService(
            session
        ).list_transactions(
            user.id,
            limit=10,
        )

    if not transactions:
        text = (
            "📜 <b>تاریخچه تراکنش</b>\n\n"
            "هنوز تراکنشی ثبت نشده."
        )
    else:
        lines = ["📜 <b>۱۰ تراکنش اخیر</b>\n"]

        for tx in transactions:
            label = TX_LABELS.get(
                tx.type,
                tx.type,
            )

            sign = "+" if tx.amount >= 0 else ""

            lines.append(
                f"{label}: "
                f"{sign}{tx.amount:,} تومان\n"
                f"مانده: {tx.balance_after:,} تومان"
            )

        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=wallet_back_keyboard(),
    )

    await callback.answer()


# =========================================================
# شروع شارژ ریالی
# =========================================================


@router.callback_query(F.data == "wallet:deposit:rial")
async def handle_rial_deposit_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    await state.update_data(
        deposit_type="RIAL"
    )

    await state.set_state(
        DepositStates.WAITING_AMOUNT
    )

    await callback.message.edit_text(
        "💳 <b>شارژ ریالی</b>\n\n"
        "مبلغ مورد نظر را به تومان وارد کنید.\n\n"
        "مثال:\n"
        "<code>500000</code>",
        reply_markup=deposit_cancel_keyboard(),
    )

    await callback.answer()


# =========================================================
# شروع شارژ توکن
# =========================================================


@router.callback_query(F.data == "wallet:deposit:token")
async def handle_token_deposit_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    await state.update_data(
        deposit_type="TOKEN"
    )

    await state.set_state(
        DepositStates.WAITING_AMOUNT
    )

    await callback.message.edit_text(
        "🪙 <b>شارژ Access Token</b>\n\n"
        "تعداد Token مورد نظر را وارد کنید.\n\n"
        "💰 هر 500 Token = 20,000 تومان\n"
        "📌 حداقل خرید: 500 Token\n"
        "♾ حداکثر خرید: ندارد\n\n"
        "مثال:\n"
        "<code>1000</code>",
        reply_markup=deposit_cancel_keyboard(),
    )

    await callback.answer()


# =========================================================
# دریافت مبلغ / تعداد Token
# =========================================================


@router.message(
    DepositStates.WAITING_AMOUNT,
    F.text,
)
async def handle_deposit_amount(
    message: Message,
    state: FSMContext,
) -> None:

    raw = (
        message.text
        .strip()
        .replace(",", "")
        .replace("٬", "")
        .replace(" ", "")
    )

    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(
            "❗️ لطفاً فقط یک عدد صحیح و مثبت وارد کنید."
        )
        return

    value = int(raw)

    data = await state.get_data()
    deposit_type = data.get(
        "deposit_type",
        "RIAL",
    )

    if deposit_type == "TOKEN":
        # این مسیر مستقیماً روی صف Access Token/Game Economy (game_service.py)
        # می‌نشیند که قبلاً به‌صراحت گفته شد قابل توسعه/تکمیل نیست؛ برای همین
        # عمداً کرش نمی‌کند ولی درخواست را هم پردازش نمی‌کند.
        await message.answer(
            "❗️ شارژ Access Token در حال حاضر غیرفعال است.\n"
            "برای شارژ کیف پول از «💳 شارژ ریالی» استفاده کنید."
        )
        await state.clear()
        return

    async with get_session() as session:
        payment_info = await SettingsService(session).get("payment_info") or "اطلاعات پرداخت ثبت نشده است."

    await state.update_data(amount=value)
    await state.set_state(DepositStates.WAITING_RECEIPT)

    text = (
        "💳 <b>شارژ ریالی</b>\n\n"
        f"مبلغ:\n<b>{value:,} تومان</b>\n\n"
        "💳 <b>اطلاعات پرداخت</b>\n\n"
        f"{payment_info}\n"
    )
    text += (
        "\n📤 بعد از کارت‌به‌کارت، "
        "عکس رسید پرداخت را همینجا ارسال کنید."
    )

    await message.answer(
        text,
        reply_markup=deposit_cancel_keyboard(),
    )


# =========================================================
# دریافت رسید
# =========================================================


@router.message(
    DepositStates.WAITING_RECEIPT,
    F.photo,
)
async def handle_deposit_receipt(
    message: Message,
    state: FSMContext,
) -> None:

    data = await state.get_data()

    amount = data.get("amount")
    deposit_type = data.get(
        "deposit_type",
        "RIAL",
    )
    token_amount = data.get(
        "token_amount"
    )

    if not amount:
        await state.clear()

        await message.answer(
            "❗️ مشکلی پیش آمد. "
            "لطفاً دوباره از کیف پول شروع کنید."
        )

        return

    if deposit_type == "TOKEN" and not token_amount:
        await state.clear()

        await message.answer(
            "❗️ مقدار Token پیدا نشد. "
            "لطفاً دوباره تلاش کنید."
        )

        return

    file_id = message.photo[-1].file_id

    async with get_session() as session:

        user = await _get_user(
            session,
            message.from_user,
        )

        deposit_service = DepositService(
            session
        )

        request = await deposit_service.create_request(
            user_id=user.id,
            amount=amount,
            deposit_type=deposit_type,
            token_amount=token_amount,
        )

        await deposit_service.attach_receipt(
            request.id,
            file_id,
        )

    await state.clear()

    if deposit_type == "TOKEN":

        user_message = (
            "✅ <b>رسید شارژ Token دریافت شد</b>\n\n"
            f"🪙 تعداد: <b>{token_amount:,} Token</b>\n"
            f"💰 مبلغ: <b>{amount:,} تومان</b>\n\n"
            "درخواست شما برای بررسی به ادمین ارسال شد."
        )

    else:

        user_message = (
            "✅ <b>رسید شارژ ریالی دریافت شد</b>\n\n"
            f"💰 مبلغ: <b>{amount:,} تومان</b>\n\n"
            "درخواست شما برای بررسی به ادمین ارسال شد."
        )

    user_message += (
        "\n\n"
        "پس از تأیید، موجودی شما به‌صورت خودکار "
        "به‌روزرسانی می‌شود."
    )

    await message.answer(
        user_message,
        reply_markup=wallet_back_keyboard(),
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "—"
    )

    if deposit_type == "TOKEN":

        caption = (
            "🪙 <b>درخواست شارژ Access Token</b>\n\n"
            f"کاربر: {username}\n"
            f"Telegram ID: "
            f"<code>{message.from_user.id}</code>\n\n"
            f"Token: <b>{token_amount:,}</b>\n"
            f"مبلغ: <b>{amount:,} تومان</b>\n"
            f"شماره درخواست: #{request.id}"
        )

    else:

        caption = (
            "💳 <b>درخواست شارژ ریالی</b>\n\n"
            f"کاربر: {username}\n"
            f"Telegram ID: "
            f"<code>{message.from_user.id}</code>\n\n"
            f"مبلغ: <b>{amount:,} تومان</b>\n"
            f"شماره درخواست: #{request.id}"
        )

    for admin_id in settings.admin_ids:

        try:
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=caption,
                reply_markup=admin_deposit_decision_keyboard(
                    request.id
                ),
            )
        except Exception:
            continue


@router.message(
    DepositStates.WAITING_RECEIPT
)
async def handle_deposit_receipt_wrong_type(
    message: Message,
) -> None:

    await message.answer(
        "📤 لطفاً رسید پرداخت را به‌صورت «عکس» ارسال کنید."
    )


# =========================================================
# تأیید توسط ادمین
# =========================================================


@router.callback_query(
    F.data.startswith("admin:deposit:approve:")
)
async def handle_admin_approve(
    callback: CallbackQuery,
) -> None:

    if not _is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔️ شما دسترسی ادمین ندارید.",
            show_alert=True,
        )
        return

    request_id = int(
        callback.data.split(":")[3]
    )

    async with get_session() as session:

        deposit_service = DepositService(
            session
        )

        try:

            request = await deposit_service.approve(
                request_id,
                callback.from_user.id,
            )

        except DepositAlreadyDecidedError:

            await callback.answer(
                "این درخواست قبلاً بررسی شده است.",
                show_alert=True,
            )

            return

        except Exception:

            await callback.answer(
                "❌ خطا در تأیید درخواست.",
                show_alert=True,
            )

            return

        target_user = await session.get(
            User,
            request.user_id,
        )

        if request.deposit_type == "TOKEN":

            new_balance = target_user.token_balance

        else:

            new_balance = await WalletService(
                session
            ).get_balance(
                request.user_id
            )

    try:

        if callback.message.caption is not None:

            await callback.message.edit_caption(
                caption=(
                    callback.message.caption
                    + "\n\n✅ <b>تأیید شد</b>"
                ),
                reply_markup=None,
            )

        else:

            await callback.message.edit_text(
                callback.message.text
                + "\n\n✅ <b>تأیید شد</b>",
                reply_markup=None,
            )

    except Exception:
        pass

    await callback.answer(
        "تأیید شد ✅"
    )

    if target_user:

        try:

            if request.deposit_type == "TOKEN":

                await callback.bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=(
                        "✅ <b>شارژ Access Token تأیید شد</b>\n\n"
                        f"🪙 مقدار شارژ: "
                        f"<b>{request.token_amount:,} Token</b>\n"
                        f"موجودی جدید: "
                        f"<b>{new_balance:,} Token</b>"
                    ),
                )

            else:

                await callback.bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=(
                        "✅ <b>شارژ کیف پول تأیید شد</b>\n\n"
                        f"💰 مبلغ: "
                        f"<b>{request.amount:,} تومان</b>\n"
                        f"موجودی جدید: "
                        f"<b>{new_balance:,} تومان</b>"
                    ),
                )

        except Exception:
            pass


# =========================================================
# رد توسط ادمین
# =========================================================


@router.callback_query(
    F.data.startswith("admin:deposit:reject:")
)
async def handle_admin_reject(
    callback: CallbackQuery,
) -> None:

    if not _is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "⛔️ شما دسترسی ادمین ندارید.",
            show_alert=True,
        )
        return

    request_id = int(
        callback.data.split(":")[3]
    )

    async with get_session() as session:

        deposit_service = DepositService(
            session
        )

        try:

            request = await deposit_service.reject(
                request_id,
                callback.from_user.id,
            )

        except DepositAlreadyDecidedError:

            await callback.answer(
                "این درخواست قبلاً بررسی شده است.",
                show_alert=True,
            )

            return

        target_user = await session.get(
            User,
            request.user_id,
        )

    try:

        if callback.message.caption is not None:

            await callback.message.edit_caption(
                caption=(
                    callback.message.caption
                    + "\n\n❌ <b>رد شد</b>"
                ),
                reply_markup=None,
            )

        else:

            await callback.message.edit_text(
                callback.message.text
                + "\n\n❌ <b>رد شد</b>",
                reply_markup=None,
            )

    except Exception:
        pass

    await callback.answer(
        "رد شد ❌"
    )

    if target_user:

        try:

            if request.deposit_type == "TOKEN":

                await callback.bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=(
                        "❌ <b>درخواست شارژ Token رد شد</b>\n\n"
                        f"مقدار: "
                        f"<b>{request.token_amount:,} Token</b>\n"
                        f"مبلغ: "
                        f"<b>{request.amount:,} تومان</b>\n\n"
                        "برای پیگیری با پشتیبانی تماس بگیرید."
                    ),
                )

            else:

                await callback.bot.send_message(
                    chat_id=target_user.telegram_id,
                    text=(
                        "❌ <b>درخواست شارژ ریالی رد شد</b>\n\n"
                        f"مبلغ: "
                        f"<b>{request.amount:,} تومان</b>\n\n"
                        "برای پیگیری با پشتیبانی تماس بگیرید."
                    ),
                )

        except Exception:
            pass
