"""add explicit platform game index

Revision ID: 0007_add_platform_game_index
Revises: 0006_sync_current_models
Create Date: 2026-08-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_add_platform_game_index"
down_revision: Union[str, None] = "0006_sync_current_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = inspector.get_indexes(
        "platform_token_transactions"
    )

    if not any(
        index.get("name")
        == "ix_platform_token_transactions_game_id"
        for index in indexes
    ):
        op.create_index(
            "ix_platform_token_transactions_game_id",
            "platform_token_transactions",
            ["game_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    indexes = inspector.get_indexes(
        "platform_token_transactions"
    )

    if any(
        index.get("name")
        == "ix_platform_token_transactions_game_id"
        for index in indexes
    ):
        op.drop_index(
            "ix_platform_token_transactions_game_id",
            table_name="platform_token_transactions",
        )
