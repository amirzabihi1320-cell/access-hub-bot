"""add per category and product button columns

Revision ID: 0008_add_button_columns
Revises: 0007_add_platform_game_index
Create Date: 2026-08-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_add_button_columns"
down_revision: Union[str, None] = "0007_add_platform_game_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    category_columns = {
        column["name"]
        for column in inspector.get_columns("categories")
    }

    if "button_columns" not in category_columns:
        op.add_column(
            "categories",
            sa.Column(
                "button_columns",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )

    product_columns = {
        column["name"]
        for column in inspector.get_columns("products")
    }

    if "button_columns" not in product_columns:
        op.add_column(
            "products",
            sa.Column(
                "button_columns",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    product_columns = {
        column["name"]
        for column in inspector.get_columns("products")
    }

    if "button_columns" in product_columns:
        op.drop_column("products", "button_columns")

    category_columns = {
        column["name"]
        for column in inspector.get_columns("categories")
    }

    if "button_columns" in category_columns:
        op.drop_column("categories", "button_columns")
