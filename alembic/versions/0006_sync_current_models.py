"""sync current models with database

Revision ID: 0006_sync_current_models
Revises: 0005_access_hub_games
Create Date: 2026-08-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_sync_current_models"
down_revision: Union[str, None] = "0005_access_hub_games"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # DepositRequest: Access Token deposit support
    #
    # These columns may already exist because the previous
    # migration attempt completed them before SQLite rejected
    # the UNIQUE constraint operation.
    # ---------------------------------------------------------

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    deposit_columns = {
        column["name"]
        for column in inspector.get_columns("deposit_requests")
    }

    if "deposit_type" not in deposit_columns:
        op.add_column(
            "deposit_requests",
            sa.Column(
                "deposit_type",
                sa.String(length=16),
                nullable=False,
                server_default="RIAL",
            ),
        )

    if "token_amount" not in deposit_columns:
        op.add_column(
            "deposit_requests",
            sa.Column(
                "token_amount",
                sa.BigInteger(),
                nullable=True,
            ),
        )

    # ---------------------------------------------------------
    # Wallet: one wallet per user
    #
    # SQLite does not support ALTER TABLE ADD CONSTRAINT.
    # batch_alter_table uses SQLite's copy-and-move strategy.
    # ---------------------------------------------------------

    wallet_indexes = inspector.get_indexes("wallets")
    wallet_unique_constraints = inspector.get_unique_constraints("wallets")

    has_wallet_unique = any(
        constraint.get("name") == "uq_wallets_user_id"
        or constraint.get("column_names") == ["user_id"]
        for constraint in wallet_unique_constraints
    )

    has_wallet_unique_index = any(
        index.get("unique") and index.get("column_names") == ["user_id"]
        for index in wallet_indexes
    )

    if not has_wallet_unique and not has_wallet_unique_index:
        with op.batch_alter_table("wallets") as batch_op:
            batch_op.create_unique_constraint(
                "uq_wallets_user_id",
                ["user_id"],
            )

    # ---------------------------------------------------------
    # Platform token transactions
    #
    # game_id is already UNIQUE in SQLite through the table's
    # auto-generated unique constraint. The current model also
    # requests an explicit unique index because it uses
    # index=True. Create that index if it does not exist.
    # ---------------------------------------------------------

    inspector = sa.inspect(bind)

    platform_indexes = inspector.get_indexes(
        "platform_token_transactions"
    )

    if not any(
        index.get("name") == "ix_platform_token_transactions_game_id"
        for index in platform_indexes
    ):
        op.create_index(
            "ix_platform_token_transactions_game_id",
            "platform_token_transactions",
            ["game_id"],
            unique=True,
        )

    # ---------------------------------------------------------
    # Products: remove obsolete category index
    # ---------------------------------------------------------

    inspector = sa.inspect(bind)

    product_indexes = inspector.get_indexes("products")

    if any(
        index.get("name") == "ix_products_category_id"
        for index in product_indexes
    ):
        op.drop_index(
            "ix_products_category_id",
            table_name="products",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    product_indexes = inspector.get_indexes("products")

    if not any(
        index.get("name") == "ix_products_category_id"
        for index in product_indexes
    ):
        op.create_index(
            "ix_products_category_id",
            "products",
            ["category_id"],
        )

    with op.batch_alter_table("wallets") as batch_op:
        try:
            batch_op.drop_constraint(
                "uq_wallets_user_id",
                type_="unique",
            )
        except Exception:
            pass

    inspector = sa.inspect(bind)

    deposit_columns = {
        column["name"]
        for column in inspector.get_columns("deposit_requests")
    }

    if "token_amount" in deposit_columns:
        op.drop_column(
            "deposit_requests",
            "token_amount",
        )

    if "deposit_type" in deposit_columns:
        op.drop_column(
            "deposit_requests",
            "deposit_type",
        )
