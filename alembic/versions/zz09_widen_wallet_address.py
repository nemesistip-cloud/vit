"""Support native VIT Chain wallet addresses.

Native VIT addresses are 43 characters (``VIT`` plus 40 hexadecimal
characters). The previous 42-character column was sized for EVM addresses
only and caused genesis user creation to fail.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "zz09_widen_wallet_address"
down_revision: Union[str, Sequence[str], None] = "zz08_provider_evid_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("users"):
        return

    columns = {column["name"]: column for column in inspector.get_columns("users")}
    wallet_column = columns.get("wallet_address")
    if wallet_column is None:
        op.add_column("users", sa.Column("wallet_address", sa.String(length=64), nullable=True))
        return

    current_length = getattr(wallet_column["type"], "length", None)
    if current_length is not None and current_length >= 64:
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column(
            "wallet_address",
            existing_type=wallet_column["type"],
            type_=sa.String(length=64),
            existing_nullable=wallet_column.get("nullable", True),
        )


def downgrade() -> None:
    # Do not shrink this column: valid native VIT addresses would be lost.
    pass