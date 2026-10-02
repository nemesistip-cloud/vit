"""Persist provider-reported match statistics for auditable features."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zz10_match_statistics"
down_revision: Union[str, Sequence[str], None] = "zz09_widen_wallet_address"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("matches"):
        columns = {column["name"] for column in inspector.get_columns("matches")}
        if "statistics" not in columns:
            op.add_column("matches", sa.Column("statistics", sa.JSON(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("matches"):
        columns = {column["name"] for column in inspector.get_columns("matches")}
        if "statistics" in columns:
            op.drop_column("matches", "statistics")