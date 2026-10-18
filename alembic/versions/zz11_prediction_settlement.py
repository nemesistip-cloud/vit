"""Add persisted prediction settlement result."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zz11_prediction_settlement"
down_revision: Union[str, Sequence[str], None] = "zz10_match_statistics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("predictions"):
        return

    columns = {column["name"] for column in inspector.get_columns("predictions")}
    if "was_correct" not in columns:
        op.add_column("predictions", sa.Column("was_correct", sa.Boolean(), nullable=True))

    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_predictions_was_correct ON predictions (was_correct)"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("predictions"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("predictions")}
    if "idx_predictions_was_correct" in indexes:
        op.drop_index("idx_predictions_was_correct", table_name="predictions")

    columns = {column["name"] for column in inspector.get_columns("predictions")}
    if "was_correct" in columns:
        op.drop_column("predictions", "was_correct")