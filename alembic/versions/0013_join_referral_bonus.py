"""add join bonus and referral invite bonus tracking flags to users

Revision ID: 0013_join_referral_bonus
Revises: 0012_button_styles
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_join_referral_bonus"
down_revision: Union[str, None] = "0012_button_styles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {c["name"] for c in inspector.get_columns("users")}

    if "join_bonus_claimed" not in user_columns:
        op.add_column(
            "users",
            sa.Column("join_bonus_claimed", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if "referral_bonus_paid" not in user_columns:
        op.add_column(
            "users",
            sa.Column("referral_bonus_paid", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {c["name"] for c in inspector.get_columns("users")}

    if "referral_bonus_paid" in user_columns:
        op.drop_column("users", "referral_bonus_paid")

    if "join_bonus_claimed" in user_columns:
        op.drop_column("users", "join_bonus_claimed")
