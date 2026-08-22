"""add daily check-in tracking columns to users

Revision ID: 0014_daily_checkin
Revises: 0013_join_referral_bonus
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_daily_checkin"
down_revision: Union[str, None] = "0013_join_referral_bonus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {c["name"] for c in inspector.get_columns("users")}

    if "last_checkin_date" not in user_columns:
        op.add_column(
            "users",
            sa.Column("last_checkin_date", sa.Date(), nullable=True),
        )

    if "checkin_streak" not in user_columns:
        op.add_column(
            "users",
            sa.Column("checkin_streak", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {c["name"] for c in inspector.get_columns("users")}

    if "checkin_streak" in user_columns:
        op.drop_column("users", "checkin_streak")

    if "last_checkin_date" in user_columns:
        op.drop_column("users", "last_checkin_date")
