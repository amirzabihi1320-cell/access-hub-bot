"""add tournaments tables

Revision ID: 0009_tournaments
Revises: 0008_add_button_columns
Create Date: 2026-08-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009_tournaments"
down_revision: Union[str, None] = "0008_add_button_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "tournaments" not in existing_tables:
        op.create_table(
            "tournaments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=128), nullable=False),
            sa.Column("metric", sa.String(length=16), nullable=False, server_default="REFERRALS"),
            sa.Column("entry_fee", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("prize_description", sa.Text(), nullable=False),
            sa.Column("prize_wallet_credit", sa.BigInteger(), nullable=True),
            sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
            sa.Column("winner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_admin_id", sa.BigInteger(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "tournament_participants" not in existing_tables:
        op.create_table(
            "tournament_participants",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id"), nullable=False, index=True
            ),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("tournament_participants")
    op.drop_table("tournaments")
