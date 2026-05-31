"""Add Asian Handicap + Correct Score columns to predictions

Revision ID: 008_ah_cs_markets
Revises: 007_ai_source_raw
Create Date: 2026-04-25 13:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008_ah_cs_markets"
down_revision: Union[str, None] = "007_ai_source_raw"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    cols = [c["name"] for c in insp.get_columns(table)]
    return column in cols


_NEW_COLS = [
    ("ah_line", sa.Float()),
    ("ah_home_prob", sa.Float()),
    ("ah_away_prob", sa.Float()),
    ("ah_lines", sa.JSON()),
    ("cs_probs", sa.JSON()),
    ("top_correct_score", sa.String(length=8)),
    ("top_cs_prob", sa.Float()),
]


def upgrade() -> None:
    bind = op.get_bind()
    for name, type_ in _NEW_COLS:
        if not _has_column(bind, "predictions", name):
            op.add_column("predictions", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    for name, _ in reversed(_NEW_COLS):
        if _has_column(bind, "predictions", name):
            with op.batch_alter_table("predictions") as batch:
                batch.drop_column(name)
