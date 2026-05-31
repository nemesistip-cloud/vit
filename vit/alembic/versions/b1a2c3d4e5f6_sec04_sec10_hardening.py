"""SEC-04 token blocklist + SEC-10 login brute-force columns

Revision ID: b1a2c3d4e5f6
Revises: 71b62dcde5da
Create Date: 2026-05-01 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, None] = "009_consensus_alts"
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
    # ── SEC-10: DB-backed login brute-force columns ───────────────────────
    if not _column_exists("users", "failed_login_count"):
        op.add_column(
            "users",
            sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _column_exists("users", "locked_until"):
        op.add_column(
            "users",
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        )

    # ── 2FA (TOTP) columns ────────────────────────────────────────────────
    if not _column_exists("users", "totp_secret"):
        op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    if not _column_exists("users", "totp_enabled"):
        op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"))

    # ── SEC-03: email_tokens table ────────────────────────────────────────
    if not _table_exists("email_tokens"):
        op.create_table(
            "email_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("token_hash", sa.String(255), nullable=False, unique=True, index=True),
            sa.Column("purpose", sa.String(32), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # ── SEC-04: token_blocklist table ─────────────────────────────────────
    if not _table_exists("token_blocklist"):
        op.create_table(
            "token_blocklist",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("jti", sa.String(64), nullable=False, unique=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("reason", sa.String(100), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if _table_exists("token_blocklist"):
        op.drop_table("token_blocklist")
    if _table_exists("email_tokens"):
        op.drop_table("email_tokens")
    if _column_exists("users", "locked_until"):
        op.drop_column("users", "locked_until")
    if _column_exists("users", "failed_login_count"):
        op.drop_column("users", "failed_login_count")
