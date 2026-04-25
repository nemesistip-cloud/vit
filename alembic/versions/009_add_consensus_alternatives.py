"""Add model_consensus + alternative_bets columns to predictions

Revision ID: 009_consensus_alts
Revises: 008_ah_cs_markets
Create Date: 2026-04-25 14:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_consensus_alts"
down_revision: Union[str, None] = "008_ah_cs_markets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    return column in [c["name"] for c in insp.get_columns(table)]


_NEW_COLS = [
    ("model_consensus", sa.JSON()),
    ("alternative_bets", sa.JSON()),
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
