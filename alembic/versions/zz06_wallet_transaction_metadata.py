"""Add persisted wallet transaction metadata for nonce tracking."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision = "zz06_wallet_transaction_metadata"
down_revision: Union[str, Sequence[str], None] = "zz05_social_intelligence_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("wallets")}
    if "tx_metadata" not in columns:
        op.add_column("wallets", sa.Column("tx_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("wallets")}
    if "tx_metadata" in columns:
        op.drop_column("wallets", "tx_metadata")
