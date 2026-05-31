"""Add TOTP 2FA columns to users table

Revision ID: c2d3e4f5a6b7
Revises: b1a2c3d4e5f6
Create Date: 2026-05-01 00:01:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if not _column_exists("users", "totp_secret"):
        op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    if not _column_exists("users", "totp_enabled"):
        op.add_column(
            "users",
            sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _column_exists("users", "totp_enabled"):
        op.drop_column("users", "totp_enabled")
    if _column_exists("users", "totp_secret"):
        op.drop_column("users", "totp_secret")
