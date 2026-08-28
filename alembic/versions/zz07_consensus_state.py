"""Persist node-facing consensus state."""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "zz07_consensus_state"
down_revision: Union[str, Sequence[str], None] = "zz06_wallet_transaction_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("consensus_states"):
        op.create_table(
            "consensus_states",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("node_id", sa.String(length=255), nullable=False),
            sa.Column("height", sa.Integer(), nullable=False),
            sa.Column("round", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("state_type", sa.String(length=20), nullable=False),
            sa.Column("block_hash", sa.String(length=66), nullable=False),
            sa.Column("validator_id", sa.String(length=255), nullable=True),
            sa.Column("certificate", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_consensus_states_node_id", "consensus_states", ["node_id"])
        op.create_index("ix_consensus_states_height", "consensus_states", ["height"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("consensus_states"):
        op.drop_index("ix_consensus_states_height", table_name="consensus_states")
        op.drop_index("ix_consensus_states_node_id", table_name="consensus_states")
        op.drop_table("consensus_states")
