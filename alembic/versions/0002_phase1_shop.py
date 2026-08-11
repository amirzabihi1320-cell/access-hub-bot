"""phase 1: categories, products, required_channels

Revision ID: 0002_phase1_shop
Revises: 0001_init_tables
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_phase1_shop"
down_revision: Union[str, None] = "0001_init_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "required_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("invite_link", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=16), nullable=True),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("product_type", sa.String(length=32), nullable=False, server_default="FIXED"),
        sa.Column("fixed_price", sa.BigInteger(), nullable=True),
        sa.Column("unit_price", sa.BigInteger(), nullable=True),
        sa.Column("min_quantity", sa.Integer(), nullable=True),
        sa.Column("max_quantity", sa.Integer(), nullable=True),
        sa.Column("status", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])


def downgrade() -> None:
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("required_channels")
