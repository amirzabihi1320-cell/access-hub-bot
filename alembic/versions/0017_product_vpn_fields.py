"""add VPN auto-delivery fields to products

Revision ID: 0017_product_vpn_fields
Revises: 0016_vpn_engine
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017_product_vpn_fields"
down_revision: Union[str, None] = "0016_vpn_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("products")}

    if "is_vpn_product" not in existing_columns:
        op.add_column(
            "products",
            sa.Column("is_vpn_product", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "vpn_data_limit_gb" not in existing_columns:
        op.add_column("products", sa.Column("vpn_data_limit_gb", sa.Integer(), nullable=True))
    if "vpn_duration_days" not in existing_columns:
        op.add_column("products", sa.Column("vpn_duration_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "vpn_duration_days")
    op.drop_column("products", "vpn_data_limit_gb")
    op.drop_column("products", "is_vpn_product")
