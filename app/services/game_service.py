import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.base import get_session
from app.config.settings import get_settings
from app.models.game import Game, GameEvent, GameReaction, PlatformTokenTransaction, TokenTransaction
from app.models.user import User

settings = get_settings()
logger = logging.getLogger("access_hub.games")

class GameError(Exception): pass
class InsufficientTokenError(GameError): pass
class GameNotFoundError(GameError): pass
class GameAlreadyJoinedError(GameError): pass
class GameClosedError(GameError): pass
class NotCreatorError(GameError): pass

def utcnow():
    return datetime.now(timezone.utc)

class TokenService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _locked_user(self, user_id: int) -> User:
        user = await self.session.scalar(select(User).where(User.id == user_id).with_for_update())
        if not user:
            raise GameError("کاربر پیدا نشد.")
        return user

    async def _record(self, user: User, type_: str, amount: int, reference_id: str | None, description: str):
        before = user.token_balance
        after = before + amount
        if after < 0:
            raise InsufficientTokenError("موجودی Token کافی نیست.")
        user.token_balance = after
        if type_ == "purchase":
            user.total_tokens_purchased += amount
        elif type_ == "game_entry":
            user.total_tokens_spent += -amount
        elif type_ == "game_win":
            user.total_tokens_won += amount
        elif type_ == "game_fee":
            user.total_game_fees_paid += -amount
        tx = TokenTransaction(user_id=user.id, type=type_, amount=amount,
                              balance_before=before, balance_after=after,
                              reference_id=reference_id, description=description)
        self.session.add(tx)
        return tx

    async def credit(self, user_id: int, amount: int, type_: str = "purchase",
                     reference_id: str | None = None, description: str = ""):
        if amount <= 0: raise ValueError("amount must be positive")
        user = await self._locked_user(user_id)
        return await self._record(user, type_, amount, reference_id, description)

    async def debit(self, user_id: int, amount: int, type_: str = "game_entry",
                    reference_id: str | None = None, description: str = ""):
        if amount <= 0: raise ValueError("amount must be positive")
        user = await self._locked_user(user_id)
        if user.token_balance < amount:
            raise InsufficientTokenError("موجودی Token شما برای ورود به این بازی کافی نیست.")
        return await self._record(user, type_, -amount, reference_id, description)

    async def admin_adjust(self, telegram_id: int, amount: int, admin_id: int, reference_id: str | None = None):
        user = await self.session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
        if not user: raise GameError("کاربر پیدا نشد.")
        before = user.token_balance
        after = before + amount
        if after < 0: raise InsufficientTokenError("موجودی Token کافی نیست.")
        user.token_balance = after
        tx = TokenTransaction(user_id=user.id, type="admin_adjustment", amount=amount,
                              balance_before=before, balance_after=after,
                              reference_id=reference_id or f"admin:{admin_id}",
                              description=f"Admin adjustment by {admin_id}")
        self.session.add(tx)
        return user

class GameService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _event(self, game_id, event_type, user_id=None, data=None):
        self.session.add(GameEvent(game_id=game_id, user_id=user_id, event_type=event_type,
                                   event_data=json.dumps(data, ensure_ascii=False) if data else None))

    async def create_game(self, telegram_id: int, chat_id: int, message_id: int, entry: int):
        if entry < settings.game_min_entry or entry > settings.game_max_entry:
            raise GameError(f"مبلغ بازی باید بین {settings.game_min_entry:,} و {settings.game_max_entry:,} Token باشد.")
        if settings.game_chat_id is not None and chat_id != settings.game_chat_id:
            raise GameError("این بازی فقط در گپ رسمی Access Hub فعال است.")
        creator = await self.session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
        if not creator:
            raise GameError("ابتدا ربات را با /start فعال کنید.")
        game_uuid = str(uuid.uuid4())
        total = entry * 2
        fee = total // 10
        reward = total - fee
        await TokenService(self.session).debit(creator.id, entry, "game_entry", game_uuid, "Reaction Battle entry")
        game = Game(game_id=game_uuid, chat_id=chat_id, message_id=message_id, creator_id=creator.id,
                    entry_amount=entry, total_pot=total, fee=fee, winner_reward=reward,
                    status="waiting",
                    expires_at=utcnow() + timedelta(seconds=settings.game_expiration_seconds))
        self.session.add(game)
        await self._event(game_uuid, "game_created", creator.id, {"entry": entry})
        await self.session.commit()
        return game

    async def join_game(self, game_id: str, telegram_id: int):
        game = await self.session.scalar(select(Game).where(Game.game_id == game_id).with_for_update())
        if not game: raise GameNotFoundError()
        if game.status != "waiting": raise GameClosedError("⚠️ این بازی قبلاً توسط یک بازیکن دیگر شروع شده است.")
        opponent = await self.session.scalar(select(User).where(User.telegram_id == telegram_id).with_for_update())
        if not opponent: raise GameError("ابتدا ربات را با /start فعال کنید.")
        creator = await self.session.scalar(select(User).where(User.id == game.creator_id))
        if opponent.id == game.creator_id:
            raise GameError("❌ سازنده نمی‌تواند به بازی خودش بپیوندد.")
        await TokenService(self.session).debit(opponent.id, game.entry_amount, "game_entry", game.game_id, "Reaction Battle entry")
        game.opponent_id = opponent.id
        game.status = "active"
        game.reaction_ready_at = utcnow() + timedelta(seconds=settings.game_reaction_delay_seconds)
        game.reaction_started_at = None
        game.expires_at = utcnow() + timedelta(seconds=settings.game_active_timeout_seconds)
        await self._event(game.game_id, "player_joined", opponent.id)
        await self.session.commit()
        return game

    async def cancel_game(self, game_id: str, telegram_id: int):
        game = await self.session.scalar(select(Game).where(Game.game_id == game_id).with_for_update())
        if not game: raise GameNotFoundError()
        creator = await self.session.scalar(select(User).where(User.id == game.creator_id))
        if not creator or creator.telegram_id != telegram_id: raise NotCreatorError()
        if game.status != "waiting": raise GameClosedError("⚠️ این بازی دیگر قابل لغو نیست.")
        await TokenService(self.session).credit(creator.id, game.entry_amount, "game_refund", game.game_id, "Cancelled game refund")
        game.status = "cancelled"
        game.completed_at = utcnow()
        await self._event(game.game_id, "game_cancelled", creator.id)
        await self.session.commit()
        return game

    async def start_reaction(self, game_id: str):
        game = await self.session.scalar(select(Game).where(Game.game_id == game_id).with_for_update())
        if not game or game.status != "active" or game.reaction_started_at is not None:
            return None
        game.reaction_started_at = utcnow()
        await self._event(game.game_id, "reaction_started")
        await self.session.commit()
        return game

    async def react(self, game_id: str, telegram_id: int):
        game = await self.session.scalar(select(Game).where(Game.game_id == game_id).with_for_update())
        if not game or game.status != "active" or game.reaction_started_at is None:
            raise GameClosedError("⚠️ این مرحله بازی دیگر فعال نیست.")
        user = await self.session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user or user.id not in (game.creator_id, game.opponent_id):
            raise GameError("❌ شما بازیکن این بازی نیستید.")
        existing = await self.session.scalar(select(GameReaction).where(GameReaction.game_id == game_id, GameReaction.user_id == user.id))
        if existing:
            raise GameError("واکنش شما قبلاً ثبت شده است.")
        ms = max(0, int((utcnow() - game.reaction_started_at).total_seconds() * 1000))
        reaction = GameReaction(game_id=game.game_id, user_id=user.id, reaction_ms=ms)
        self.session.add(reaction)
        await self._event(game.game_id, "player_reacted", user.id, {"reaction_ms": ms})
        await self.session.flush()

        reactions = (await self.session.execute(
            select(GameReaction).where(GameReaction.game_id == game.game_id)
            .order_by(GameReaction.reaction_ms.asc())
        )).scalars().all()

        if len(reactions) >= 2:
            # هر دو بازیکن باید واکنش بدهند. زمان واکنش از ساعت سرور محاسبه می‌شود.
            winner = reactions[0]
            loser_id = game.opponent_id if winner.user_id == game.creator_id else game.creator_id
            game.winner_id = winner.user_id
            game.loser_id = loser_id
            game.status = "completed"
            game.completed_at = utcnow()

            token = TokenService(self.session)
            await token.credit(
                winner.user_id, game.winner_reward, "game_win",
                game.game_id, "Reaction Battle reward"
            )

            # کارمزد از Pot کسر شده و دوباره از موجودی هیچ بازیکنی کم نمی‌شود.
            self.session.add(PlatformTokenTransaction(
                game_id=game.game_id, type="game_fee", amount=game.fee,
                description="Access Hub game fee"
            ))

            creator = await self.session.scalar(select(User).where(User.id == game.creator_id).with_for_update())
            opponent = await self.session.scalar(select(User).where(User.id == game.opponent_id).with_for_update())
            if creator and opponent:
                creator.total_game_fees_paid += game.fee // 2
                opponent.total_game_fees_paid += game.fee - (game.fee // 2)

            await self._event(
                game.game_id, "settled", winner.user_id,
                {"winner_reward": game.winner_reward, "fee": game.fee,
                 "winner_reaction_ms": winner.reaction_ms, "loser_id": loser_id}
            )
            await self.session.commit()
            return game, winner.reaction_ms

        await self.session.commit()
        return game, ms

    async def expire_waiting_games(self):
        games = (await self.session.execute(
            select(Game).where(Game.status == "waiting", Game.expires_at <= utcnow()).with_for_update(skip_locked=True)
        )).scalars().all()
        for game in games:
            creator = await self.session.scalar(select(User).where(User.id == game.creator_id).with_for_update())
            if creator:
                await TokenService(self.session).credit(creator.id, game.entry_amount, "game_refund", game.game_id, "Expired game refund")
            game.status = "expired"
            game.completed_at = utcnow()
            await self._event(game.game_id, "game_expired", game.creator_id)
        if games: await self.session.commit()
        return games

    async def expire_active_games(self):
        games = (await self.session.execute(
            select(Game).where(Game.status == "active", Game.expires_at <= utcnow()).with_for_update(skip_locked=True)
        )).scalars().all()
        for game in games:
            # اگر هیچ‌کس واکنش نداده باشد، کل Match refund می‌شود.
            reactions = (await self.session.execute(select(GameReaction).where(GameReaction.game_id == game.game_id))).scalars().all()
            if not reactions:
                await TokenService(self.session).credit(game.creator_id, game.entry_amount, "game_refund", game.game_id, "Active game timeout refund")
                if game.opponent_id:
                    await TokenService(self.session).credit(game.opponent_id, game.entry_amount, "game_refund", game.game_id, "Active game timeout refund")
            else:
                # اگر یکی واکنش داده و دیگری نه، همان بازیکن برنده می‌شود.
                winner = reactions[0]
                game.winner_id = winner.user_id
                game.loser_id = game.opponent_id if winner.user_id == game.creator_id else game.creator_id
                game.status = "completed"
                game.completed_at = utcnow()
                await TokenService(self.session).credit(winner.user_id, game.winner_reward, "game_win", game.game_id, "Reaction Battle timeout reward")
                self.session.add(PlatformTokenTransaction(game_id=game.game_id, type="game_fee", amount=game.fee,
                                                           description="Access Hub game fee"))
                await self._event(game.game_id, "timeout_settlement", winner.user_id)
                continue
            game.status = "expired"
            game.completed_at = utcnow()
            await self._event(game.game_id, "active_timeout_refund")
        if games: await self.session.commit()
        return games

    async def profile(self, telegram_id: int):
        user = await self.session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return None
        played = await self.session.scalar(select(func.count(Game.id)).where(
            Game.status == "completed",
            (Game.creator_id == user.id) | (Game.opponent_id == user.id)
        ))
        wins = await self.session.scalar(select(func.count(Game.id)).where(
            Game.status == "completed", Game.winner_id == user.id
        ))
        losses = (played or 0) - (wins or 0)
        tokens_lost = await self.session.scalar(select(func.coalesce(func.sum(Game.entry_amount), 0)).where(
            Game.status == "completed", Game.loser_id == user.id
        ))
        user_wins = int(wins or 0)
        players_ahead = await self.session.scalar(select(func.count()).select_from(
            select(Game.winner_id, func.count(Game.id).label("wins"))
            .where(Game.status == "completed", Game.winner_id.is_not(None))
            .group_by(Game.winner_id)
            .having(func.count(Game.id) > user_wins)
            .subquery()
        ))
        rank = int(players_ahead or 0) + 1
        return user, int(played or 0), user_wins, int(losses), int(tokens_lost or 0), rank

    async def leaderboard(self, period: str = "all"):
        stmt = select(User.id, User.username, func.count(Game.id).label("wins")).join(Game, Game.winner_id == User.id).where(Game.status == "completed")
        if period in {"daily", "weekly", "monthly"}:
            delta = {"daily": timedelta(days=1), "weekly": timedelta(days=7), "monthly": timedelta(days=30)}[period]
            stmt = stmt.where(Game.completed_at >= utcnow() - delta)
        stmt = stmt.group_by(User.id, User.username).order_by(func.count(Game.id).desc()).limit(10)
        return (await self.session.execute(stmt)).all()

async def scheduler_loop(bot):
    while True:
        try:
            async with get_session() as session:
                service = GameService(session)
                waiting = await service.expire_waiting_games()
                active = await service.expire_active_games()
                # شروع Reaction برای Matchهای active که تازه وارد شده‌اند
                threshold = utcnow() - timedelta(seconds=settings.game_reaction_delay_seconds)
                pending = (await session.execute(
                    select(Game).where(Game.status == "active", Game.reaction_started_at.is_(None),
                                       Game.reaction_ready_at.is_not(None),
                                       Game.reaction_ready_at <= utcnow())
                    .limit(20)
                )).scalars().all()
                for game in pending:
                    await service.start_reaction(game.game_id)
            for game in waiting + active:
                try:
                    await refresh_game_message(bot, game.game_id)
                except Exception:
                    pass
            async with get_session() as session:
                pending = (await session.execute(select(Game).where(Game.status == "active",
                    Game.reaction_started_at.is_not(None), Game.reaction_started_at >= threshold))).scalars().all()
            for game in pending:
                try:
                    await refresh_game_message(bot, game.game_id)
                except Exception:
                    pass
        except Exception:
            logger.exception("Game scheduler iteration failed")
        await asyncio.sleep(settings.game_scheduler_interval)

async def refresh_game_message(bot, game_id: str):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    async with get_session() as session:
        game = await session.scalar(select(Game).where(Game.game_id == game_id))
        if not game: return
        creator = await session.scalar(select(User).where(User.id == game.creator_id))
        opponent = await session.scalar(select(User).where(User.id == game.opponent_id)) if game.opponent_id else None
        winner = await session.scalar(select(User).where(User.id == game.winner_id)) if game.winner_id else None
        def name(u):
            if not u: return "-"
            return f"@{u.username}" if u.username else (u.first_name or str(u.telegram_id))
        if game.status == "waiting":
            text = (f"⚔️ <b>بازی جدید</b>\n\n👤 سازنده: <b>{name(creator)}</b>\n"
                    f"💰 مبلغ ورود: <b>{game.entry_amount:,} 🪙</b>\n"
                    f"🏆 جایزه برنده: <b>{game.winner_reward:,} 🪙</b>\n"
                    f"💎 کارمزد Access Hub: <b>{game.fee:,} 🪙</b>")
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎮 پیوستن به بازی", callback_data=f"game:join:{game.game_id}")],
                [InlineKeyboardButton(text="❌ لغو بازی", callback_data=f"game:cancel:{game.game_id}")]])
        elif game.status == "active" and game.reaction_started_at is None:
            text = f"⚔️ <b>بازی شروع شد!</b>\n\n👤 {name(creator)}\n👤 {name(opponent)}\n\n⏳ آماده باشید..."
            markup = InlineKeyboardMarkup(inline_keyboard=[])
        elif game.status == "active":
            text = f"⚡ <b>واکنش!</b>\n\n👤 {name(creator)}\n👤 {name(opponent)}\n\nاولین واکنش صحیح برنده است."
            markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚡ واکنش!", callback_data=f"game:react:{game.game_id}")]])
        elif game.status == "completed":
            text = (f"🏆 <b>بازی به پایان رسید</b>\n\n👤 بازیکن اول: <b>{name(creator)}</b>\n"
                    f"👤 بازیکن دوم: <b>{name(opponent)}</b>\n👑 برنده: <b>{name(winner)}</b>\n"
                    f"💰 جایزه: <b>{game.winner_reward:,} 🪙</b>\n💎 کارمزد Access Hub: <b>{game.fee:,} 🪙</b>")
            markup = InlineKeyboardMarkup(inline_keyboard=[])
        else:
            text = f"⚠️ <b>این بازی {game.status} شد.</b>\n\n💰 مبلغ {game.entry_amount:,} 🪙 به سازنده برگشت داده شد."
            markup = InlineKeyboardMarkup(inline_keyboard=[])
        try:
            await bot.edit_message_text(text, chat_id=game.chat_id, message_id=game.message_id, reply_markup=markup)
        except Exception:
            pass
