"""add per category and product button styles

Revision ID: 0012_button_styles
Revises: 0011_token_product_purchase
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_button_styles"
down_revision: Union[str, None] = "0011_token_product_purchase"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    category_columns = {c["name"] for c in inspector.get_columns("categories")}
    if "button_style" not in category_columns:
        op.add_column(
            "categories",
            sa.Column("button_style", sa.String(length=16), nullable=False, server_default="success"),
        )

    product_columns = {c["name"] for c in inspector.get_columns("products")}
    if "button_style" not in product_columns:
        op.add_column(
            "products",
            sa.Column("button_style", sa.String(length=16), nullable=False, server_default="primary"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    product_columns = {c["name"] for c in inspector.get_columns("products")}
    if "button_style" in product_columns:
        op.drop_column("products", "button_style")

    category_columns = {c["name"] for c in inspector.get_columns("categories")}
    if "button_style" in category_columns:
        op.drop_column("categories", "button_style")
