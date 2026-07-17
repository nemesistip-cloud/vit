"""Add match source/fingerprint and model version history

Revision ID: 005
Revises: fab045ad4db1
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004_add_user_id_to_predictions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    matches_cols = {c["name"] for c in insp.get_columns("matches")}
    if "source" not in matches_cols:
        op.add_column("matches", sa.Column("source", sa.String(length=32), nullable=True, server_default="unknown"))
        op.create_index("idx_matches_source", "matches", ["source"], unique=False)
    if "fingerprint" not in matches_cols:
        op.add_column("matches", sa.Column("fingerprint", sa.String(length=255), nullable=True))
        op.create_index("idx_matches_fingerprint", "matches", ["fingerprint"], unique=False)

    if insp.has_table("model_metadata"):
        meta_cols = {c["name"] for c in insp.get_columns("model_metadata")}
        if "active_version" not in meta_cols:
            op.add_column("model_metadata", sa.Column("active_version", sa.String(length=32), nullable=True))
        if "version_history" not in meta_cols:
            op.add_column("model_metadata", sa.Column("version_history", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("model_metadata"):
        meta_cols = {c["name"] for c in insp.get_columns("model_metadata")}
        if "version_history" in meta_cols:
            op.drop_column("model_metadata", "version_history")
        if "active_version" in meta_cols:
            op.drop_column("model_metadata", "active_version")

    matches_cols = {c["name"] for c in insp.get_columns("matches")}
    if "fingerprint" in matches_cols:
        op.drop_index("idx_matches_fingerprint", table_name="matches")
        op.drop_column("matches", "fingerprint")
    if "source" in matches_cols:
        op.drop_index("idx_matches_source", table_name="matches")
        op.drop_column("matches", "source")
