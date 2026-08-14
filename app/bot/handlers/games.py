from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from app.config.settings import get_settings
from app.database.base import get_session
from app.models.user import User
from app.services.user_service import UserService
from app.services.game_service import GameService, TokenService, GameError, InsufficientTokenError, GameClosedError, NotCreatorError

router = Router(name="games")
settings = get_settings()

def _name(user):
    if user.username:
        return f"@{user.username}"
    return user.first_name or str(user.telegram_id)

def _entry(text):
    raw = text.strip().lower().replace(",", "").replace("٬", "")
    if raw.startswith("بازی"):
        parts = raw.split()
        for p in parts:
            if p.isdigit():
                return int(p)
    if raw.isdigit():
        return int(raw)
    return None

@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def handle_game_creation(message: Message):
    entry = _entry(message.text or "")
    if entry is None:
        return
    if settings.game_chat_id is not None and message.chat.id != settings.game_chat_id:
        return
    challenge = await message.reply("⏳ در حال ساخت بازی...")
    async with get_session() as session:
        try:
            await UserService(session).get_or_create(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            game = await GameService(session).create_game(
                message.from_user.id, message.chat.id, challenge.message_id, entry
            )
        except InsufficientTokenError:
            await challenge.edit_text("❌ موجودی Token شما برای ایجاد این بازی کافی نیست.")
            return
        except GameError as e:
            await challenge.edit_text(str(e))
            return
    await _refresh(bot=message.bot, game_id=game.game_id)

@router.callback_query(F.data.startswith("game:join:"))
async def join_game(callback: CallbackQuery):
    game_id = callback.data.split(":", 2)[2]
    async with get_session() as session:
        try:
            game = await GameService(session).join_game(game_id, callback.from_user.id)
        except InsufficientTokenError:
            await callback.answer("❌ موجودی Token شما برای ورود به این بازی کافی نیست.", show_alert=True)
            return
        except GameClosedError as e:
            await callback.answer(str(e), show_alert=True)
            return
        except GameError as e:
            await callback.answer(str(e), show_alert=True)
            return
    await callback.answer("🎮 وارد بازی شدید!")
    await _refresh(callback.bot, game.game_id)

@router.callback_query(F.data.startswith("game:cancel:"))
async def cancel_game(callback: CallbackQuery):
    game_id = callback.data.split(":", 2)[2]
    async with get_session() as session:
        try:
            game = await GameService(session).cancel_game(game_id, callback.from_user.id)
        except NotCreatorError:
            await callback.answer("❌ فقط سازنده این بازی می‌تواند آن را لغو کند.", show_alert=True)
            return
        except GameClosedError as e:
            await callback.answer(str(e), show_alert=True)
            return
        except GameError as e:
            await callback.answer(str(e), show_alert=True)
            return
    await callback.answer("بازی لغو شد و Token برگشت داده شد. ✅")
    await _refresh(callback.bot, game.game_id)

@router.callback_query(F.data.startswith("game:react:"))
async def react(callback: CallbackQuery):
    game_id = callback.data.split(":", 2)[2]
    async with get_session() as session:
        try:
            result = await GameService(session).react(game_id, callback.from_user.id)
        except GameClosedError as e:
            await callback.answer(str(e), show_alert=True)
            return
        except GameError as e:
            await callback.answer(str(e), show_alert=True)
            return
    game, ms = result
    await callback.answer(f"⚡ واکنش ثبت شد: {ms}ms")
    await _refresh(callback.bot, game.game_id)

async def _refresh(bot, game_id):
    from app.services.game_service import refresh_game_message
    await refresh_game_message(bot, game_id)

@router.message(Command("tokens"))
async def tokens(message: Message):
    async with get_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
    if not user:
        await message.answer("ابتدا /start را بزنید.")
        return
    await message.answer(f"🪙 <b>Access Token</b>\n\nموجودی: <b>{user.token_balance:,}</b> 🪙")

@router.message(Command("profile"))
async def profile(message: Message):
    async with get_session() as session:
        data = await GameService(session).profile(message.from_user.id)
    if not data:
        await message.answer("ابتدا /start را بزنید.")
        return
    user, played, wins, losses, tokens_lost, rank = data
    rate = (wins / played * 100) if played else 0
    await message.answer(
        f"🎮 <b>Access Hub Profile</b>\n\n👤 <b>{_name(user)}</b>\n\n"
        f"🏆 Wins: <b>{wins}</b>\n💀 Losses: <b>{losses}</b>\n"
        f"📊 Win Rate: <b>{rate:.1f}%</b>\n🪙 Balance: <b>{user.token_balance:,}</b>\n"
        f"💰 Tokens Won: <b>{user.total_tokens_won:,}</b>\n"
        f"📉 Tokens Lost: <b>{tokens_lost:,}</b>\n"
        f"💎 Fees Paid: <b>{user.total_game_fees_paid:,}</b>\n"
        f"🏅 Rank: <b>#{rank}</b>"
    )

@router.message(Command("leaderboard"))
async def leaderboard(message: Message):
    args = (message.text or "").split()
    period = args[1].lower() if len(args) > 1 else "all"
    if period not in {"daily", "weekly", "monthly", "all"}:
        period = "all"
    labels = {"daily": "روزانه", "weekly": "هفتگی", "monthly": "ماهانه", "all": "All Time"}
    async with get_session() as session:
        rows = await GameService(session).leaderboard(period)
    text = f"🏆 <b>Top Players | {labels[period]}</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows, 1):
        username = f"@{row.username}" if row.username else f"User {row.id}"
        medal = medals[i-1] if i <= 3 else f"{i}."
        text += f"{medal} {username} — <b>{row.wins}</b> Wins\n"
    await message.answer(text if rows else text + "هنوز بازی ثبت نشده است.")

@router.message(Command("token_add"))
async def token_add(message: Message):
    if message.from_user.id not in settings.admin_ids:
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("فرمت: /token_add TELEGRAM_ID AMOUNT")
        return
    try:
        telegram_id, amount = int(parts[1]), int(parts[2])
    except ValueError:
        await message.answer("❌ Telegram ID و مبلغ باید عدد باشند.")
        return
    async with get_session() as session:
        try:
            user = await TokenService(session).admin_adjust(telegram_id, amount, message.from_user.id)
            await session.commit()
        except Exception as e:
            await message.answer(f"❌ {e}")
            return
    await message.answer(f"✅ موجودی Token کاربر به‌روزرسانی شد.\n🪙 موجودی جدید: {user.token_balance:,}")

@router.message(Command("game_stats"))
async def game_stats(message: Message):
    if message.from_user.id not in settings.admin_ids:
        return
    from sqlalchemy import func
    from app.models.game import Game, PlatformTokenTransaction
    async with get_session() as session:
        total_games = await session.scalar(select(func.count(Game.id)))
        completed = await session.scalar(select(func.count(Game.id)).where(Game.status == "completed"))
        waiting = await session.scalar(select(func.count(Game.id)).where(Game.status == "waiting"))
        fees = await session.scalar(select(func.coalesce(func.sum(PlatformTokenTransaction.amount), 0)))
    await message.answer(
        "📊 <b>Game System Stats</b>\n\n"
        f"🎮 Total Games: <b>{int(total_games or 0):,}</b>\n"
        f"🏆 Completed: <b>{int(completed or 0):,}</b>\n"
        f"⏳ Waiting: <b>{int(waiting or 0):,}</b>\n"
        f"💎 Access Hub Fees: <b>{int(fees or 0):,}</b> 🪙"
    )

@router.message(Command("token_history"))
async def token_history(message: Message):
    async with get_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
        if not user:
            await message.answer("ابتدا /start را بزنید.")
            return
        from app.models.game import TokenTransaction
        rows = (await session.execute(select(TokenTransaction).where(TokenTransaction.user_id == user.id)
            .order_by(TokenTransaction.created_at.desc()).limit(10))).scalars().all()
    text = "📜 <b>آخرین تراکنش‌های Token</b>\n\n"
    for tx in rows:
        sign = "+" if tx.amount > 0 else ""
        text += f"{sign}{tx.amount:,} 🪙 | {tx.type}\n"
    await message.answer(text if rows else text + "تراکنشی وجود ندارد.")
