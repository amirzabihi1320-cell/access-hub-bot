"""add external payment transactions

Revision ID: 0020_payment_transactions
Revises: 0019_vpn_panel_inbound_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020_payment_transactions"
down_revision: Union[str, None] = "0019_vpn_panel_inbound_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("purpose", sa.String(length=32), nullable=False, server_default="WALLET_DEPOSIT"),
        sa.Column("amount_toman", sa.BigInteger(), nullable=False),
        sa.Column("paid_toman", sa.BigInteger(), nullable=True),
        sa.Column("asset", sa.String(length=16), nullable=False, server_default="TRX"),
        sa.Column("asset_amount", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("transaction_id", sa.String(length=128), nullable=True),
        sa.Column("payment_url", sa.String(length=1000), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("payment_id", name="uq_payment_transactions_payment_id"),
        sa.UniqueConstraint("provider_reference", name="uq_payment_transactions_provider_reference"),
    )
    op.create_index("ix_payment_transactions_user_id", "payment_transactions", ["user_id"])
    op.create_index("ix_payment_transactions_payment_id", "payment_transactions", ["payment_id"])
    op.create_index("ix_payment_transactions_provider_reference", "payment_transactions", ["provider_reference"])


def downgrade() -> None:
    op.drop_index("ix_payment_transactions_provider_reference", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_payment_id", table_name="payment_transactions")
    op.drop_index("ix_payment_transactions_user_id", table_name="payment_transactions")
    op.drop_table("payment_transactions")
