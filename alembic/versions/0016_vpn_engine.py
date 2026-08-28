"""add vpn_panels and vpn_services tables (Provider/VPN Engine)

Revision ID: 0016_vpn_engine
Revises: 0015_discount_coupons
Create Date: 2026-08-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_vpn_engine"
down_revision: Union[str, None] = "0015_discount_coupons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "vpn_panels" not in existing_tables:
        op.create_table(
            "vpn_panels",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("panel_type", sa.String(length=32), nullable=False, server_default="MARZBAN"),
            sa.Column("base_url", sa.String(length=255), nullable=False),
            sa.Column("username", sa.String(length=128), nullable=False),
            sa.Column("password_encrypted", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("max_users", sa.Integer(), nullable=True),
            sa.Column("last_health_status", sa.String(length=16), nullable=False, server_default="UNKNOWN"),
            sa.Column("last_health_detail", sa.String(length=255), nullable=True),
            sa.Column("last_health_checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "vpn_services" not in existing_tables:
        op.create_table(
            "vpn_services",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("panel_id", sa.Integer(), sa.ForeignKey("vpn_panels.id"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
            sa.Column("remote_username", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
            sa.Column("data_limit_bytes", sa.BigInteger(), nullable=True),
            sa.Column("used_traffic_bytes", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("expire_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("subscription_url", sa.String(length=500), nullable=True),
            sa.Column("config_links", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_vpn_services_user_id", "vpn_services", ["user_id"])
        op.create_index("ix_vpn_services_order_id", "vpn_services", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_vpn_services_order_id", table_name="vpn_services")
    op.drop_index("ix_vpn_services_user_id", table_name="vpn_services")
    op.drop_table("vpn_services")
    op.drop_table("vpn_panels")
