"""phase 3: deposit_requests (manual wallet top-up)

Revision ID: 0003_phase3_wallet
Revises: 0002_phase1_shop
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_phase3_wallet"
down_revision: Union[str, None] = "0002_phase1_shop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deposit_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("receipt_file_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_admin_id", sa.BigInteger(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_deposit_requests_user_id", "deposit_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_deposit_requests_user_id", table_name="deposit_requests")
    op.drop_table("deposit_requests")
