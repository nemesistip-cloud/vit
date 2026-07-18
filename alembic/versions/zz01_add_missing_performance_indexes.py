"""add_missing_performance_indexes

Revision ID: zz01_add_missing_indexes
Revises: ee1f2c3d4e5f
Create Date: 2026-07-18 00:00:00.000000

Adds composite and single-column indexes on hot query paths that were
missing from earlier migrations. All CREATE INDEX statements use
IF NOT EXISTS so this migration is safe to re-run and idempotent.
"""
from alembic import op
import sqlalchemy as sa

revision = "zz01_add_missing_indexes"
# Merges all four current heads into a single linear chain
down_revision = (
    "004_add_user_id_to_predictions",
    "a1b2c3d4e5f6",
    "d3e4f5a6b7c8",
    "e7f1a9c2b3d4",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- predictions table ---
    # Composite: match_id + user_id (frequently joined together)
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_predictions_match_user "
        "ON predictions (match_id, user_id)"
    ))
    # user_id alone (user prediction history lookups)
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_predictions_user_id "
        "ON predictions (user_id)"
    ))
    # match_id alone (settlement, CLV lookups)
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_predictions_match_id "
        "ON predictions (match_id)"
    ))
    # timestamp (time-range queries on prediction feeds)
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_predictions_timestamp "
        "ON predictions (timestamp)"
    ))
    # is_settled (pending settlement scans)
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_predictions_is_settled "
        "ON predictions (is_settled)"
    ))

    # --- clv_entries table ---
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_clv_entries_prediction_id "
        "ON clv_entries (prediction_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_clv_entries_match_id "
        "ON clv_entries (match_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_clv_entries_user_id "
        "ON clv_entries (user_id)"
    ))

    # --- ai_predictions table ---
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_ai_predictions_is_certified "
        "ON ai_predictions (is_certified)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_ai_predictions_match_source "
        "ON ai_predictions (match_id, source)"
    ))

    # --- matches table ---
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_matches_external_id "
        "ON matches (external_id)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_matches_status "
        "ON matches (status)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_matches_kickoff_status "
        "ON matches (kickoff_time, status)"
    ))

    # --- audit_logs table ---
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_audit_logs_resource_id "
        "ON audit_logs (resource_id)"
    ))

    # --- users table ---
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_users_is_active "
        "ON users (is_active)"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_users_last_login "
        "ON users (last_login)"
    ))


def downgrade() -> None:
    op.drop_index("idx_predictions_match_user",     table_name="predictions")
    op.drop_index("idx_predictions_user_id",         table_name="predictions")
    op.drop_index("idx_predictions_match_id",        table_name="predictions")
    op.drop_index("idx_predictions_timestamp",       table_name="predictions")
    op.drop_index("idx_predictions_is_settled",      table_name="predictions")
    op.drop_index("idx_clv_entries_prediction_id",   table_name="clv_entries")
    op.drop_index("idx_clv_entries_match_id",        table_name="clv_entries")
    op.drop_index("idx_clv_entries_user_id",         table_name="clv_entries")
    op.drop_index("idx_ai_predictions_is_certified", table_name="ai_predictions")
    op.drop_index("idx_ai_predictions_match_source", table_name="ai_predictions")
    op.drop_index("idx_matches_external_id",         table_name="matches")
    op.drop_index("idx_matches_status",              table_name="matches")
    op.drop_index("idx_matches_kickoff_status",      table_name="matches")
    op.drop_index("idx_audit_logs_resource_id",      table_name="audit_logs")
    op.drop_index("idx_users_is_active",             table_name="users")
    op.drop_index("idx_users_last_login",            table_name="users")
