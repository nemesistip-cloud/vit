"""Add validator_status preference column to notification_preferences.

Revision ID: 006
Revises: 005
Create Date: 2026-04-22
"""
from typing import Union

import sqlalchemy as sa
from alembic import op


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notification_preferences") as batch:
        batch.add_column(
            sa.Column(
                "validator_status",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_preferences") as batch:
        batch.drop_column("validator_status")
