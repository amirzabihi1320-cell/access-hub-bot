"""add default_inbound_id to vpn_panels (needed for Sanaei/X-UI provider)

Revision ID: 0019_vpn_panel_inbound_id
Revises: 0018_vpn_service_product_id
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019_vpn_panel_inbound_id"
down_revision: Union[str, None] = "0018_vpn_service_product_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("vpn_panels")}
    if "default_inbound_id" not in existing_columns:
        op.add_column("vpn_panels", sa.Column("default_inbound_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("vpn_panels", "default_inbound_id")
