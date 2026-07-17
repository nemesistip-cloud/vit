"""Add raw_content + submitted_by to ai_predictions

Revision ID: 007_ai_source_raw
Revises: 1ea9f5fca66d
Create Date: 2026-04-25 12:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_ai_source_raw"
down_revision: Union[str, None] = "1ea9f5fca66d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "ai_predictions", "raw_content"):
        op.add_column(
            "ai_predictions",
            sa.Column("raw_content", sa.Text(), nullable=True),
        )
    if not _has_column(bind, "ai_predictions", "submitted_by"):
        op.add_column(
            "ai_predictions",
            sa.Column("submitted_by", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "ai_predictions", "submitted_by"):
        with op.batch_alter_table("ai_predictions") as batch:
            batch.drop_column("submitted_by")
    if _has_column(bind, "ai_predictions", "raw_content"):
        with op.batch_alter_table("ai_predictions") as batch:
            batch.drop_column("raw_content")
