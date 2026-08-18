"""add product discount columns

Revision ID: 0010_product_discount
Revises: 0009_tournaments
Create Date: 2026-08-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_product_discount"
down_revision: Union[str, None] = "0009_tournaments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {c["name"] for c in inspector.get_columns("products")}

    if "discount_percent" not in existing_columns:
        op.add_column("products", sa.Column("discount_percent", sa.Integer(), nullable=True))
    if "discount_expires_at" not in existing_columns:
        op.add_column("products", sa.Column("discount_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "discount_expires_at")
    op.drop_column("products", "discount_percent")
