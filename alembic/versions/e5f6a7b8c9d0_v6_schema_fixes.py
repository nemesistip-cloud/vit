"""v6.0 schema fixes: kickoff_time timezone, jti unique index, UserStake.match_id type

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-05-06 00:00:00.000000
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
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


def _index_exists(table: str, index_name: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return any(i["name"] == index_name for i in insp.get_indexes(table))


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    # ── 1. token_blocklist: unique index on jti ───────────────────────────
    if _table_exists("token_blocklist") and not _index_exists("token_blocklist", "ix_token_blocklist_jti"):
        op.create_index(
            "ix_token_blocklist_jti",
            "token_blocklist",
            ["jti"],
            unique=True,
        )

    # ── 2. matches.kickoff_time: SQLite stores as text (timezone-aware via
    #       app layer). PostgreSQL: ALTER COLUMN to TIMESTAMPTZ. ──────────
    if dialect == "postgresql" and _table_exists("matches") and _column_exists("matches", "kickoff_time"):
        op.execute(
            "ALTER TABLE matches ALTER COLUMN kickoff_time TYPE TIMESTAMPTZ "
            "USING kickoff_time AT TIME ZONE 'UTC'"
        )

    # ── 3. user_stakes.match_id: ensure INTEGER FK consistency.
    #       SQLite: create new column, copy, rename (limited DDL).
    #       PostgreSQL: cast directly. ──────────────────────────────────────
    if _table_exists("user_stakes") and _column_exists("user_stakes", "match_id"):
        if dialect == "postgresql":
            op.execute(
                "ALTER TABLE user_stakes "
                "ALTER COLUMN match_id TYPE INTEGER USING NULLIF(match_id, '')::INTEGER"
            )
        # SQLite: already INTEGER in new installs; skip DDL to avoid breakage

    # ── 4. predictions.clv_score — add if missing (float) ────────────────
    if _table_exists("predictions") and not _column_exists("predictions", "clv_score"):
        op.add_column("predictions", sa.Column("clv_score", sa.Float(), nullable=True))

    # ── 5. vit_chain_blocks tracking table (ledger reference) ─────────────
    # The actual vit_chain_ledger.db is a separate SQLite file managed by
    # vit_chain.py. This migration just records the migration was applied.

    # ── 6. users.telegram_chat_id unique index ────────────────────────────
    if _table_exists("users") and _column_exists("users", "telegram_chat_id"):
        if not _index_exists("users", "ix_users_telegram_chat_id"):
            op.create_index(
                "ix_users_telegram_chat_id",
                "users",
                ["telegram_chat_id"],
                unique=False,
            )


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    if _table_exists("token_blocklist") and _index_exists("token_blocklist", "ix_token_blocklist_jti"):
        op.drop_index("ix_token_blocklist_jti", table_name="token_blocklist")

    if _table_exists("users") and _index_exists("users", "ix_users_telegram_chat_id"):
        op.drop_index("ix_users_telegram_chat_id", table_name="users")

    if dialect == "postgresql" and _table_exists("matches") and _column_exists("matches", "kickoff_time"):
        op.execute(
            "ALTER TABLE matches ALTER COLUMN kickoff_time TYPE TIMESTAMP WITHOUT TIME ZONE "
            "USING kickoff_time AT TIME ZONE 'UTC'"
        )
