"""
تورنومنت رفرال/فروش (بخش جدید).

جایزه‌ی هر تورنومنت مقدار/توضیح ثابتی است که ادمین از قبل تعیین می‌کند؛
هرگز از پول شرکت‌کننده‌های دیگر تأمین نمی‌شود (جزئیات در tournament_service.py).
"""
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.reply_menu import TOURNAMENTS, home_reply_keyboard
from app.bot.keyboards.tournament import (
    METRIC_LABELS,
    admin_tournament_detail_keyboard,
    admin_tournament_metric_keyboard,
    admin_tournaments_keyboard,
    tournament_board_back_keyboard,
    tournament_detail_keyboard,
    tournaments_list_keyboard,
)
from app.bot.states.tournament_states import TournamentStates
from app.config.settings import get_settings
from app.database.base import get_session
from app.services.tournament_service import (
    AlreadyJoinedError,
    AlreadySettledError,
    TournamentError,
    TournamentNotActiveError,
    TournamentService,
)
from app.utils.message_manager import MessageManager

router = Router(name="tournament")
router.message.filter(F.chat.type == "private")
settings = get_settings()


def _is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


def _name(user) -> str:
    if user.username:
        return f"@{user.username}"
    return user.first_name or str(user.telegram_id)


def _time_left_text(end_at: datetime) -> str:
    now = datetime.now(timezone.utc)
    end = end_at if end_at.tzinfo else end_at.replace(tzinfo=timezone.utc)
    remaining = end - now
    if remaining.total_seconds() <= 0:
        return "پایان یافته"
    days = remaining.days
    hours = remaining.seconds // 3600
    if days > 0:
        return f"{days} روز و {hours} ساعت"
    return f"{hours} ساعت"


def _tournament_text(tournament) -> str:
    metric_label = METRIC_LABELS.get(tournament.metric, tournament.metric)
    entry_text = f"{tournament.entry_fee:,} تومان" if tournament.entry_fee > 0 else "رایگان"
    status_labels = {
        "ACTIVE": "🟢 فعال",
        "ENDED": "🟠 پایان‌یافته (در انتظار تسویه)",
        "SETTLED": "✅ تسویه‌شده",
        "CANCELLED": "🔴 لغوشده",
    }
    lines = [
        f"🏆 <b>{tournament.title}</b>",
        "",
        f"📊 معیار: {metric_label}",
        f"💰 ورودی: {entry_text}",
        f"🎁 جایزه: {tournament.prize_description}",
        f"وضعیت: {status_labels.get(tournament.status, tournament.status)}",
    ]
    if tournament.status == "ACTIVE":
        lines.append(f"⏱ زمان باقی‌مانده: {_time_left_text(tournament.end_at)}")
    if tournament.winner_user_id:
        lines.append("🥇 برنده مشخص شده است.")
    return "\n".join(lines)


def _leaderboard_text(tournament, rows: list[tuple]) -> str:
    metric_unit = "دعوت" if tournament.metric == "REFERRALS" else "خرید"
    text = f"📊 <b>جدول رده‌بندی — {tournament.title}</b>\n\n"
    if not rows:
        return text + "هنوز شرکت‌کننده‌ای امتیازی کسب نکرده است."
    medals = ["🥇", "🥈", "🥉"]
    for i, (user, score) in enumerate(rows, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        text += f"{medal} {_name(user)} — {score} {metric_unit}\n"
    return text


# ==================== کاربر ====================


@router.message(F.text == TOURNAMENTS)
async def handle_tournaments_entry(message: Message, state: FSMContext) -> None:
    sent = await message.answer("🏠", reply_markup=home_reply_keyboard())
    try:
        await message.bot.delete_message(message.chat.id, sent.message_id)
    except Exception:
        pass

    manager = MessageManager(message.bot, message.chat.id, state)
    async with get_session() as session:
        tournaments = await TournamentService(session).list_active()

    if not tournaments:
        await manager.send("فعلاً تورنومنت فعالی وجود ندارد.")
        return

    await manager.send("🏆 تورنومنت‌های فعال:", reply_markup=tournaments_list_keyboard(tournaments))


@router.callback_query(F.data == "tournament:list")
async def handle_tournament_list_back(callback: CallbackQuery) -> None:
    async with get_session() as session:
        tournaments = await TournamentService(session).list_active()
    if not tournaments:
        await callback.message.edit_text("فعلاً تورنومنت فعالی وجود ندارد.")
        await callback.answer()
        return
    await callback.message.edit_text("🏆 تورنومنت‌های فعال:", reply_markup=tournaments_list_keyboard(tournaments))
    await callback.answer()


@router.callback_query(F.data.startswith("tournament:view:"))
async def handle_tournament_view(callback: CallbackQuery) -> None:
    tournament_id = int(callback.data.split(":")[2])
    async with get_session() as session:
        service = TournamentService(session)
        tournament = await service.get(tournament_id)
        if not tournament:
            await callback.answer("تورنومنت پیدا نشد.", show_alert=True)
            return
        joined = await service.is_participant(tournament_id, callback.from_user.id)

    await callback.message.edit_text(
        _tournament_text(tournament), reply_markup=tournament_detail_keyboard(tournament_id, joined)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tournament:join:"))
async def handle_tournament_join(callback: CallbackQuery) -> None:
    tournament_id = int(callback.data.split(":")[2])
    async with get_session() as session:
        service = TournamentService(session)
        try:
            await service.join(tournament_id, callback.from_user.id)
        except (AlreadyJoinedError, TournamentNotActiveError, TournamentError) as e:
            await callback.answer(str(e), show_alert=True)
            return
        tournament = await service.get(tournament_id)

    await callback.answer("✅ با موفقیت ثبت‌نام شدید!")
    await callback.message.edit_text(
        _tournament_text(tournament), reply_markup=tournament_detail_keyboard(tournament_id, joined=True)
    )


@router.callback_query(F.data.startswith("tournament:board:"))
async def handle_tournament_board(callback: CallbackQuery) -> None:
    tournament_id = int(callback.data.split(":")[2])
    async with get_session() as session:
        service = TournamentService(session)
        tournament = await service.get(tournament_id)
        if not tournament:
            await callback.answer("تورنومنت پیدا نشد.", show_alert=True)
            return
        rows = await service.leaderboard(tournament_id)

    await callback.message.edit_text(
        _leaderboard_text(tournament, rows), reply_markup=tournament_board_back_keyboard(tournament_id)
    )
    await callback.answer()


# ==================== ادمین ====================


@router.callback_query(F.data == "admin:tournaments")
async def handle_admin_tournaments(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    async with get_session() as session:
        tournaments = await TournamentService(session).list_all()
    await callback.message.edit_text("🏆 <b>تورنومنت‌ها</b>", reply_markup=admin_tournaments_keyboard(tournaments))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tournament:view:"))
async def handle_admin_tournament_view(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    tournament_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        tournament = await TournamentService(session).get(tournament_id)
    if not tournament:
        await callback.answer("تورنومنت پیدا نشد.", show_alert=True)
        return
    await callback.message.edit_text(
        _tournament_text(tournament), reply_markup=admin_tournament_detail_keyboard(tournament)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tournament:board:"))
async def handle_admin_tournament_board(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    tournament_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        service = TournamentService(session)
        tournament = await service.get(tournament_id)
        if not tournament:
            await callback.answer("تورنومنت پیدا نشد.", show_alert=True)
            return
        rows = await service.leaderboard(tournament_id, limit=20)
    await callback.message.edit_text(
        _leaderboard_text(tournament, rows), reply_markup=admin_tournament_detail_keyboard(tournament)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tournament:end:"))
async def handle_admin_tournament_end(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    tournament_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        service = TournamentService(session)
        try:
            tournament = await service.end_now(tournament_id)
        except TournamentError as e:
            await callback.answer(str(e), show_alert=True)
            return
    await callback.answer("⏹ تورنومنت پایان یافت.")
    await callback.message.edit_text(
        _tournament_text(tournament), reply_markup=admin_tournament_detail_keyboard(tournament)
    )


@router.callback_query(F.data.startswith("admin:tournament:cancel:"))
async def handle_admin_tournament_cancel(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    tournament_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        service = TournamentService(session)
        try:
            await service.cancel(tournament_id)
        except TournamentError as e:
            await callback.answer(str(e), show_alert=True)
            return
        tournament = await service.get(tournament_id)
    await callback.answer("❌ تورنومنت لغو و ورودی‌ها بازگردانده شد.")
    await callback.message.edit_text(
        _tournament_text(tournament), reply_markup=admin_tournament_detail_keyboard(tournament)
    )


@router.callback_query(F.data.startswith("admin:tournament:settle:"))
async def handle_admin_tournament_settle(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    tournament_id = int(callback.data.split(":")[3])
    async with get_session() as session:
        service = TournamentService(session)
        try:
            tournament, winner, score = await service.settle(tournament_id)
        except AlreadySettledError as e:
            await callback.answer(str(e), show_alert=True)
            return
        except TournamentError as e:
            await callback.answer(str(e), show_alert=True)
            return

    if winner:
        credit_text = (
            f"\n💳 {tournament.prize_wallet_credit:,} تومان به کیف‌پولش واریز شد."
            if tournament.prize_wallet_credit
            else "\n📌 جایزه غیرنقدی است؛ لطفاً دستی برای برنده ارسال کنید."
        )
        result_text = _tournament_text(tournament) + f"\n\n🥇 برنده: {_name(winner)} ({score} امتیاز){credit_text}"
        try:
            prize_note = (
                f"مبلغ {tournament.prize_wallet_credit:,} تومان به کیف‌پول شما واریز شد."
                if tournament.prize_wallet_credit
                else "به‌زودی جایزه از طرف پشتیبانی برایتان ارسال می‌شود."
            )
            await callback.bot.send_message(
                winner.telegram_id,
                f"🎉 <b>تبریک! شما در تورنومنت «{tournament.title}» برنده شدید.</b>\n\n"
                f"🎁 جایزه: {tournament.prize_description}\n{prize_note}",
            )
        except Exception:
            pass
    else:
        result_text = _tournament_text(tournament) + "\n\nهیچ شرکت‌کننده‌ای امتیازی کسب نکرد؛ برنده‌ای تعیین نشد."

    await callback.answer("✅ تسویه انجام شد.")
    await callback.message.edit_text(result_text, reply_markup=admin_tournament_detail_keyboard(tournament))


# ---------- ساخت تورنومنت جدید (FSM) ----------


@router.callback_query(F.data == "admin:tournament:add")
async def handle_admin_tournament_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔️ شما دسترسی ادمین ندارید.", show_alert=True)
        return
    await state.set_state(TournamentStates.WAITING_TITLE)
    await callback.message.edit_text("📝 عنوان تورنومنت را بفرستید:")
    await callback.answer()


@router.message(TournamentStates.WAITING_TITLE, F.text)
async def handle_admin_tournament_title(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(TournamentStates.WAITING_METRIC)
    await message.answer("📊 معیار برنده‌شدن را انتخاب کنید:", reply_markup=admin_tournament_metric_keyboard())


@router.callback_query(TournamentStates.WAITING_METRIC, F.data.startswith("admin:tournament:metric:"))
async def handle_admin_tournament_metric(callback: CallbackQuery, state: FSMContext) -> None:
    metric = callback.data.split(":")[3]
    await state.update_data(metric=metric)
    await state.set_state(TournamentStates.WAITING_ENTRY_FEE)
    await callback.message.edit_text("💰 مبلغ ورودی به تومان را وارد کنید (۰ برای رایگان):")
    await callback.answer()


@router.message(TournamentStates.WAITING_ENTRY_FEE, F.text)
async def handle_admin_tournament_entry_fee(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    value = message.text.strip()
    if not value.isdigit():
        await message.answer("❗️ فقط عدد وارد کنید (۰ برای رایگان).")
        return
    await state.update_data(entry_fee=int(value))
    await state.set_state(TournamentStates.WAITING_DURATION)
    await message.answer("⏱ تورنومنت چند روز طول بکشد؟ (عدد روز را وارد کنید)")


@router.message(TournamentStates.WAITING_DURATION, F.text)
async def handle_admin_tournament_duration(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    value = message.text.strip()
    if not value.isdigit() or int(value) <= 0:
        await message.answer("❗️ فقط یک عدد مثبت (روز) وارد کنید.")
        return
    await state.update_data(duration_days=int(value))
    await state.set_state(TournamentStates.WAITING_PRIZE_DESCRIPTION)
    await message.answer("🎁 توضیح جایزه را بنویسید (مثلاً: «۱۰۰٪ تخفیف خرید بعدی»):")


@router.message(TournamentStates.WAITING_PRIZE_DESCRIPTION, F.text)
async def handle_admin_tournament_prize_description(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.update_data(prize_description=message.text.strip())
    await state.set_state(TournamentStates.WAITING_PRIZE_CREDIT)
    await message.answer(
        "💳 اگر می‌خواهید جایزه خودکار به کیف‌پول برنده واریز شود، مبلغ را به تومان بفرستید.\n"
        "برای جایزه‌ی غیرنقدی (که خودتان دستی می‌دهید)، عدد ۰ را بفرستید."
    )


@router.message(TournamentStates.WAITING_PRIZE_CREDIT, F.text)
async def handle_admin_tournament_prize_credit(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    value = message.text.strip()
    if not value.isdigit():
        await message.answer("❗️ فقط عدد وارد کنید (۰ برای جایزه‌ی غیرنقدی).")
        return
    prize_credit = int(value) or None

    data = await state.get_data()
    async with get_session() as session:
        tournament = await TournamentService(session).create(
            title=data["title"],
            metric=data["metric"],
            entry_fee=data["entry_fee"],
            prize_description=data["prize_description"],
            duration_days=data["duration_days"],
            admin_id=message.from_user.id,
            prize_wallet_credit=prize_credit,
        )
    await state.clear()
    await message.answer(
        "✅ تورنومنت ساخته شد و الان فعاله.\n\n" + _tournament_text(tournament),
        reply_markup=admin_tournament_detail_keyboard(tournament),
    )
