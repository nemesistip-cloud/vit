"""add_rbac_fields_to_users

Revision ID: 739d5e62d691
Revises: 22c85e91a8d9
Create Date: 2026-04-18 12:46:08.628267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '739d5e62d691'
down_revision: Union[str, None] = '22c85e91a8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    from sqlalchemy import inspect, text
    conn = op.get_bind()
    try:
        result = conn.execute(text(f"PRAGMA table_info({table})"))
        columns = [row[1] for row in result.fetchall()]
        return column in columns
    except Exception:
        return False


def _index_exists(index_name: str) -> bool:
    from sqlalchemy import text
    conn = op.get_bind()
    try:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"), {"n": index_name})
        return result.fetchone() is not None
    except Exception:
        return False


def upgrade() -> None:
    # Add RBAC columns to users (SQLite-safe: only ADD COLUMN, no ALTER COLUMN)
    if not _column_exists("users", "admin_role"):
        op.add_column("users", sa.Column("admin_role", sa.String(length=20), nullable=True))
    if not _column_exists("users", "subscription_tier"):
        op.add_column("users", sa.Column("subscription_tier", sa.String(length=20), nullable=True))
    if not _column_exists("users", "is_banned"):
        op.add_column("users", sa.Column("is_banned", sa.Boolean(), nullable=True, server_default="0"))

    # Safely create indexes (skip if already exist)
    if not _index_exists("ix_users_id"):
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    if not _index_exists("ix_users_email"):
        # try/except in case unique constraint already exists
        try:
            op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        except Exception:
            pass
    if not _index_exists("ix_users_username"):
        try:
            op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
        except Exception:
            pass


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN pre-3.35; use pass for safety
    pass
