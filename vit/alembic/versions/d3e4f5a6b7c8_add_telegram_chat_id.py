"""add telegram_chat_id to notification_preferences

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-05-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "d3e4f5a6b7c8"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notification_preferences") as batch_op:
        batch_op.add_column(
            sa.Column("telegram_chat_id", sa.String(64), nullable=True, default=None)
        )


def downgrade() -> None:
    with op.batch_alter_table("notification_preferences") as batch_op:
        batch_op.drop_column("telegram_chat_id")
