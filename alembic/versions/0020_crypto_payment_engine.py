"""add crypto payment engine tables (Tron/Tronado module: payment_provider_configs, crypto_wallets, crypto_wallet_transactions, crypto_deposit_orders)

Revision ID: 0020_crypto_payment_engine
Revises: 0019_vpn_panel_inbound_id
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0020_crypto_payment_engine"
down_revision: Union[str, None] = "0019_vpn_panel_inbound_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "payment_provider_configs" not in existing_tables:
        op.create_table(
            "payment_provider_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider_type", sa.String(length=32), nullable=False, unique=True),
            sa.Column("api_url", sa.String(length=255), nullable=True),
            sa.Column("api_key_encrypted", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="DISABLED"),
            sa.Column("auto_verify", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("webhook_url", sa.String(length=255), nullable=True),
            sa.Column("last_health_status", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
            sa.Column("last_health_detail", sa.String(length=255), nullable=True),
            sa.Column("last_health_checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "crypto_wallets" not in existing_tables:
        op.create_table(
            "crypto_wallets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="TRX"),
            sa.Column("balance", sa.Numeric(24, 8), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "currency", name="uq_crypto_wallet_user_currency"),
        )
        op.create_index("ix_crypto_wallets_user_id", "crypto_wallets", ["user_id"])

    if "crypto_wallet_transactions" not in existing_tables:
        op.create_table(
            "crypto_wallet_transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=False),
            sa.Column("amount", sa.Numeric(24, 8), nullable=False),
            sa.Column("balance_before", sa.Numeric(24, 8), nullable=False),
            sa.Column("balance_after", sa.Numeric(24, 8), nullable=False),
            sa.Column("type", sa.String(length=32), nullable=False),
            sa.Column("reference_id", sa.String(length=64), nullable=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("admin_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("reference_id", "type", name="uq_crypto_wallet_tx_reference"),
        )
        op.create_index("ix_crypto_wallet_transactions_user_id", "crypto_wallet_transactions", ["user_id"])
        op.create_index("ix_crypto_wallet_transactions_reference_id", "crypto_wallet_transactions", ["reference_id"])

    if "crypto_deposit_orders" not in existing_tables:
        op.create_table(
            "crypto_deposit_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.String(length=64), nullable=False, unique=True),
            sa.Column("idempotency_key", sa.String(length=64), nullable=False, unique=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("provider_type", sa.String(length=32), nullable=False, server_default="TRONADO"),
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="TRX"),
            sa.Column("toman_amount", sa.Integer(), nullable=True),
            sa.Column("crypto_amount", sa.Numeric(24, 8), nullable=True),
            sa.Column("provider_order_id", sa.String(length=128), nullable=True),
            sa.Column("provider_reference", sa.String(length=128), nullable=True),
            sa.Column("expected_wallet_address", sa.String(length=128), nullable=True),
            sa.Column("payment_url", sa.String(length=512), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="CREATED"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_crypto_deposit_orders_user_id", "crypto_deposit_orders", ["user_id"])
        op.create_index("ix_crypto_deposit_orders_provider_order_id", "crypto_deposit_orders", ["provider_order_id"])


def downgrade() -> None:
    op.drop_index("ix_crypto_deposit_orders_provider_order_id", table_name="crypto_deposit_orders")
    op.drop_index("ix_crypto_deposit_orders_user_id", table_name="crypto_deposit_orders")
    op.drop_table("crypto_deposit_orders")

    op.drop_index("ix_crypto_wallet_transactions_reference_id", table_name="crypto_wallet_transactions")
    op.drop_index("ix_crypto_wallet_transactions_user_id", table_name="crypto_wallet_transactions")
    op.drop_table("crypto_wallet_transactions")

    op.drop_index("ix_crypto_wallets_user_id", table_name="crypto_wallets")
    op.drop_table("crypto_wallets")

    op.drop_table("payment_provider_configs")
