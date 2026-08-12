"""phase 4: orders + inventory_codes

Revision ID: 0004_phase4_orders
Revises: 0003_phase3_wallet
Create Date: 2026-08-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_phase4_orders"
down_revision: Union[str, None] = "0003_phase3_wallet"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_number", sa.String(length=32), nullable=True, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.BigInteger(), nullable=False),
        sa.Column("final_price", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("delivery_type", sa.String(length=16), nullable=False, server_default="MANUAL"),
        sa.Column("delivery_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])

    op.create_table(
        "inventory_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="AVAILABLE"),
        sa.Column("assigned_order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_inventory_codes_product_id", "inventory_codes", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_codes_product_id", table_name="inventory_codes")
    op.drop_table("inventory_codes")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
