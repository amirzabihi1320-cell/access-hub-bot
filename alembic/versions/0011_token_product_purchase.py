"""add token pricing and token-paid order fields

Revision ID: 0011_token_product_purchase
Revises: 0010_product_discount
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_token_product_purchase"
down_revision: Union[str, None] = "0010_product_discount"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    product_columns = {c["name"] for c in inspector.get_columns("products")}
    if "token_price" not in product_columns:
        op.add_column("products", sa.Column("token_price", sa.BigInteger(), nullable=True))

    order_columns = {c["name"] for c in inspector.get_columns("orders")}
    if "payment_method" not in order_columns:
        op.add_column("orders", sa.Column("payment_method", sa.String(length=16), nullable=False, server_default="WALLET"))
    if "token_unit_price" not in order_columns:
        op.add_column("orders", sa.Column("token_unit_price", sa.BigInteger(), nullable=True))
    if "token_total" not in order_columns:
        op.add_column("orders", sa.Column("token_total", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    order_columns = {c["name"] for c in inspector.get_columns("orders")}
    if "token_total" in order_columns:
        op.drop_column("orders", "token_total")
    if "token_unit_price" in order_columns:
        op.drop_column("orders", "token_unit_price")
    if "payment_method" in order_columns:
        op.drop_column("orders", "payment_method")

    product_columns = {c["name"] for c in inspector.get_columns("products")}
    if "token_price" in product_columns:
        op.drop_column("products", "token_price")
