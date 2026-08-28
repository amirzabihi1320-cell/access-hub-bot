"""add product_id to vpn_services (needed for Auto-Renew)

Revision ID: 0018_vpn_service_product_id
Revises: 0017_product_vpn_fields
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_vpn_service_product_id"
down_revision: Union[str, None] = "0017_product_vpn_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("vpn_services")}
    if "product_id" not in existing_columns:
        op.add_column(
            "vpn_services",
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("vpn_services", "product_id")
