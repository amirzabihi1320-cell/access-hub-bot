"""init tables

Revision ID: 0001_init_tables
Revises:
Create Date: 2026-08-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_init_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # users
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("telegram_id", sa.BigInteger(), nullable=False),
            sa.Column("username", sa.String(length=64), nullable=True),
            sa.Column("first_name", sa.String(length=128), nullable=True),
            sa.Column("last_name", sa.String(length=128), nullable=True),
            sa.Column("language", sa.String(length=8), nullable=False, server_default="fa"),
            sa.Column("total_purchases", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_spent", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("referral_code", sa.String(length=32), nullable=False),
            sa.Column("referred_by", sa.Integer(), nullable=True),
            sa.Column("vip_level", sa.String(length=32), nullable=False, server_default="NONE"),
            sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

        op.create_index(
            "ix_users_telegram_id",
            "users",
            ["telegram_id"],
            unique=True,
        )

        op.create_index(
            "ix_users_referral_code",
            "users",
            ["referral_code"],
            unique=True,
        )

    # wallets
    if "wallets" not in tables:
        op.create_table(
            "wallets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
                unique=True,
            ),
            sa.Column("balance", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # wallet_transactions
    if "wallet_transactions" not in tables:
        op.create_table(
            "wallet_transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("amount", sa.BigInteger(), nullable=False),
            sa.Column("balance_before", sa.BigInteger(), nullable=False),
            sa.Column("balance_after", sa.BigInteger(), nullable=False),
            sa.Column("type", sa.String(length=32), nullable=False),
            sa.Column("reference_id", sa.String(length=64), nullable=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("admin_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        op.create_index(
            "ix_wallet_transactions_user_id",
            "wallet_transactions",
            ["user_id"],
        )

        op.create_index(
            "ix_wallet_transactions_reference_id",
            "wallet_transactions",
            ["reference_id"],
        )

    # settings
    if "settings" not in tables:
        op.create_table(
            "settings",
            sa.Column("key", sa.String(length=128), primary_key=True),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    # text_templates
    if "text_templates" not in tables:
        op.create_table(
            "text_templates",
            sa.Column("key", sa.String(length=128), primary_key=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "text_templates" in tables:
        op.drop_table("text_templates")

    if "settings" in tables:
        op.drop_table("settings")

    if "wallet_transactions" in tables:
        try:
            op.drop_index(
                "ix_wallet_transactions_reference_id",
                table_name="wallet_transactions",
            )
        except Exception:
            pass

        try:
            op.drop_index(
                "ix_wallet_transactions_user_id",
                table_name="wallet_transactions",
            )
        except Exception:
            pass

        op.drop_table("wallet_transactions")

    if "wallets" in tables:
        op.drop_table("wallets")

    if "users" in tables:
        try:
            op.drop_index(
                "ix_users_referral_code",
                table_name="users",
            )
        except Exception:
            pass

        try:
            op.drop_index(
                "ix_users_telegram_id",
                table_name="users",
            )
        except Exception:
            pass

        op.drop_table("users")
