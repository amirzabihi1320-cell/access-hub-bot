"""add discount_coupons table and orders.coupon_code

Revision ID: 0015_discount_coupons
Revises: 0014_daily_checkin
Create Date: 2026-08-23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015_discount_coupons"
down_revision: Union[str, None] = "0014_daily_checkin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "discount_coupons" not in existing_tables:
        op.create_table(
            "discount_coupons",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("discount_percent", sa.Integer(), nullable=False),
            sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("used_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("used_order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_admin_id", sa.BigInteger(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_discount_coupons_code", "discount_coupons", ["code"], unique=True)

    order_columns = {c["name"] for c in inspector.get_columns("orders")}
    if "coupon_code" not in order_columns:
        op.add_column("orders", sa.Column("coupon_code", sa.String(length=32), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    order_columns = {c["name"] for c in inspector.get_columns("orders")}
    if "coupon_code" in order_columns:
        op.drop_column("orders", "coupon_code")

    existing_tables = set(inspector.get_table_names())
    if "discount_coupons" in existing_tables:
        op.drop_index("ix_discount_coupons_code", table_name="discount_coupons")
        op.drop_table("discount_coupons")
