"""Add missing CLV and auto_demoted columns to model_metadata

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-05-14 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return any(c["name"] == column for c in insp.get_columns(table))


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return table in insp.get_table_names()


def upgrade() -> None:
    if not _table_exists("model_metadata"):
        return

    if not _column_exists("model_metadata", "clv_score"):
        op.add_column("model_metadata", sa.Column("clv_score", sa.Float(), nullable=True))

    if not _column_exists("model_metadata", "clv_samples"):
        op.add_column("model_metadata", sa.Column("clv_samples", sa.Integer(), nullable=True, server_default="0"))

    if not _column_exists("model_metadata", "clv_negative_streak_days"):
        op.add_column("model_metadata", sa.Column("clv_negative_streak_days", sa.Integer(), nullable=True, server_default="0"))

    if not _column_exists("model_metadata", "last_clv_check_at"):
        op.add_column("model_metadata", sa.Column("last_clv_check_at", sa.DateTime(timezone=True), nullable=True))

    if not _column_exists("model_metadata", "auto_demoted"):
        op.add_column("model_metadata", sa.Column("auto_demoted", sa.Boolean(), nullable=True, server_default="false"))

    if not _column_exists("model_metadata", "league_accuracy"):
        op.add_column("model_metadata", sa.Column("league_accuracy", sa.JSON(), nullable=True))

    if not _column_exists("model_metadata", "calibrated"):
        op.add_column("model_metadata", sa.Column("calibrated", sa.Boolean(), nullable=True, server_default="false"))


def downgrade() -> None:
    if not _table_exists("model_metadata"):
        return
    for col in ["calibrated", "league_accuracy", "auto_demoted", "last_clv_check_at",
                "clv_negative_streak_days", "clv_samples", "clv_score"]:
        if _column_exists("model_metadata", col):
            op.drop_column("model_metadata", col)
