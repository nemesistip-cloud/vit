"""Add missing User model columns and merge all divergent heads.

Revision ID: ff00aabbccdd
Revises: fab045ad4db1, a1b2c3d4e5f6, e7f1a9c2b3d4, c2d3e4f5a6b7, 71b62dcde5da
Create Date: 2026-07-11 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect

revision: str = "ff00aabbccdd"
down_revision: Union[str, tuple, None] = (
    "fab045ad4db1",
    "a1b2c3d4e5f6",
    "e7f1a9c2b3d4",
    "c2d3e4f5a6b7",
    "71b62dcde5da",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col(table: str, col: str) -> bool:
    """Return True if *col* already exists in *table* (cross-dialect)."""
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns(table)]
    return col in cols


def _add(table: str, col: str, ddl: str) -> None:
    """Add column only if it does not already exist."""
    conn = op.get_bind()
    if not _col(table, col):
        if conn.dialect.name == "sqlite":
            clean_ddl = ddl.replace("JSONB DEFAULT '[]'::jsonb", "JSON DEFAULT '[]'")
            clean_ddl = clean_ddl.replace("JSONB", "JSON")
            clean_ddl = clean_ddl.replace("TIMESTAMPTZ", "DATETIME")
            clean_ddl = clean_ddl.replace("BOOLEAN NOT NULL DEFAULT false", "INTEGER NOT NULL DEFAULT 0")
            clean_ddl = clean_ddl.replace("BOOLEAN NOT NULL DEFAULT true", "INTEGER NOT NULL DEFAULT 1")
            op.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {clean_ddl}"))
        else:
            op.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))


def upgrade() -> None:
    _add("users", "totp_secret_pending", "VARCHAR(64)")
    _add("users", "university",               "VARCHAR(255)")
    _add("users", "faculty",                  "VARCHAR(255)")
    _add("users", "department",               "VARCHAR(255)")
    _add("users", "study_level",              "VARCHAR(20)")
    _add("users", "matric_number",            "VARCHAR(50)")
    _add("users", "student_skills",           "JSONB DEFAULT '[]'::jsonb")
    _add("users", "student_interests",        "JSONB DEFAULT '[]'::jsonb")
    _add("users", "student_country",          "VARCHAR(100)")
    _add("users", "is_student_verified",      "BOOLEAN NOT NULL DEFAULT false")
    _add("users", "student_profile_completed","BOOLEAN NOT NULL DEFAULT false")

    _add("users", "current_streak", "INTEGER NOT NULL DEFAULT 0")
    _add("users", "best_streak",    "INTEGER NOT NULL DEFAULT 0")
    _add("users", "total_xp",       "INTEGER NOT NULL DEFAULT 0")

    _add("users", "is_active",            "BOOLEAN NOT NULL DEFAULT true")
    _add("users", "is_verified",          "BOOLEAN NOT NULL DEFAULT false")
    _add("users", "is_banned",            "BOOLEAN NOT NULL DEFAULT false")
    _add("users", "withdrawals_frozen",   "BOOLEAN NOT NULL DEFAULT false")
    _add("users", "is_flagged",           "BOOLEAN NOT NULL DEFAULT false")
    _add("users", "wallet_address",       "VARCHAR(42)")
    _add("users", "company_name",         "VARCHAR(255)")
    _add("users", "phone",                "VARCHAR(50)")
    _add("users", "telegram_username",    "VARCHAR(255)")
    _add("users", "last_login",           "TIMESTAMPTZ")
    _add("users", "kyc_status",           "VARCHAR(20) DEFAULT 'none'")
    _add("users", "kyc_submitted_at",     "TIMESTAMPTZ")
    _add("users", "kyc_data",             "JSONB")
    _add("users", "admin_role",           "VARCHAR(20)")
    _add("users", "subscription_tier",    "VARCHAR(20) DEFAULT 'viewer'")
    _add("users", "google_id",            "VARCHAR(255)")
    _add("users", "telegram_id",          "VARCHAR(255)")
    _add("users", "updated_at",           "TIMESTAMPTZ")

    conn = op.get_bind()
    for idx, tbl, col in [
        ("ix_users_university", "users", "university"),
        ("ix_users_faculty",    "users", "faculty"),
        ("ix_users_department", "users", "department"),
    ]:
        if conn.dialect.name == "postgresql":
            exists = conn.execute(
                text("SELECT 1 FROM pg_indexes WHERE indexname = :i"),
                {"i": idx},
            ).fetchone()
            if not exists:
                try:
                    op.create_index(idx, tbl, [col])
                except Exception:
                    pass
        else:
            try:
                op.create_index(idx, tbl, [col])
            except Exception:
                pass


def downgrade() -> None:
    pass
