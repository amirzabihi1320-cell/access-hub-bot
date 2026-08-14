"""add Access Hub Token and Game System

Revision ID: 0005_access_hub_games
Revises: 0004_phase4_orders
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005_access_hub_games"
down_revision: Union[str, None] = "0004_phase4_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("users", sa.Column("token_balance", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("total_tokens_purchased", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("total_tokens_spent", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("total_tokens_won", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("total_game_fees_paid", sa.BigInteger(), nullable=False, server_default="0"))

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.String(36), nullable=False, unique=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("creator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opponent_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("entry_amount", sa.BigInteger(), nullable=False),
        sa.Column("total_pot", sa.BigInteger(), nullable=False),
        sa.Column("fee", sa.BigInteger(), nullable=False),
        sa.Column("winner_reward", sa.BigInteger(), nullable=False),
        sa.Column("winner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("loser_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("reaction_ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reaction_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_games_chat_id", "games", ["chat_id"])
    op.create_index("ix_games_creator_id", "games", ["creator_id"])
    op.create_index("ix_games_opponent_id", "games", ["opponent_id"])
    op.create_index("ix_games_winner_id", "games", ["winner_id"])
    op.create_index("ix_games_loser_id", "games", ["loser_id"])
    op.create_index("ix_games_status", "games", ["status"])
    op.create_index("ix_games_expires_at", "games", ["expires_at"])

    op.create_table(
        "token_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("balance_before", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("reference_id", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_token_transactions_user_id", "token_transactions", ["user_id"])
    op.create_index("ix_token_transactions_type", "token_transactions", ["type"])
    op.create_index("ix_token_transactions_reference_id", "token_transactions", ["reference_id"])

    op.create_table(
        "platform_token_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.String(36), nullable=False, unique=True),
        sa.Column("type", sa.String(32), nullable=False, server_default="game_fee"),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "game_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("event_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_game_events_game_id", "game_events", ["game_id"])
    op.create_index("ix_game_events_user_id", "game_events", ["user_id"])
    op.create_index("ix_game_events_event_type", "game_events", ["event_type"])

    op.create_table(
        "game_reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.String(36), sa.ForeignKey("games.game_id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reacted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reaction_ms", sa.Integer(), nullable=False),
        sa.UniqueConstraint("game_id", "user_id", name="uq_game_reaction_user"),
    )
    op.create_index("ix_game_reactions_game_id", "game_reactions", ["game_id"])
    op.create_index("ix_game_reactions_user_id", "game_reactions", ["user_id"])

def downgrade() -> None:
    op.drop_index("ix_game_reactions_user_id", table_name="game_reactions")
    op.drop_index("ix_game_reactions_game_id", table_name="game_reactions")
    op.drop_table("game_reactions")
    op.drop_index("ix_game_events_event_type", table_name="game_events")
    op.drop_index("ix_game_events_user_id", table_name="game_events")
    op.drop_index("ix_game_events_game_id", table_name="game_events")
    op.drop_table("game_events")
    op.drop_table("platform_token_transactions")
    op.drop_index("ix_token_transactions_reference_id", table_name="token_transactions")
    op.drop_index("ix_token_transactions_type", table_name="token_transactions")
    op.drop_index("ix_token_transactions_user_id", table_name="token_transactions")
    op.drop_table("token_transactions")
    for col in ["total_game_fees_paid","total_tokens_won","total_tokens_spent","total_tokens_purchased","token_balance"]:
        op.drop_column("users", col)
    op.drop_column("games", "reaction_ready_at")
    op.drop_index("ix_games_expires_at", table_name="games")
    op.drop_index("ix_games_status", table_name="games")
    op.drop_index("ix_games_loser_id", table_name="games")
    op.drop_index("ix_games_winner_id", table_name="games")
    op.drop_index("ix_games_opponent_id", table_name="games")
    op.drop_index("ix_games_creator_id", table_name="games")
    op.drop_index("ix_games_chat_id", table_name="games")
    op.drop_table("games")
