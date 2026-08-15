"""add_missing_performance_indexes

Revision ID: zz01_add_missing_indexes
Revises: ee1f2c3d4e5f
Create Date: 2026-07-18 00:00:00.000000

Adds composite and single-column indexes on hot query paths that were
missing from earlier migrations. All CREATE INDEX statements use
IF NOT EXISTS and inspect table columns before creation so this migration
is safe to re-run and idempotent.
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


def _create_index_if_cols_exist(conn, insp, index_name, table_name, col_names):
    if not insp.has_table(table_name):
        return
    existing_cols = [c["name"] for c in insp.get_columns(table_name)]
    if all(col in existing_cols for col in col_names):
        cols_str = ", ".join(col_names)
        conn.execute(sa.text(
            f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({cols_str})"
        ))


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # --- predictions table ---
    _create_index_if_cols_exist(conn, insp, "idx_predictions_match_user", "predictions", ["match_id", "user_id"])
    _create_index_if_cols_exist(conn, insp, "idx_predictions_user_id", "predictions", ["user_id"])
    _create_index_if_cols_exist(conn, insp, "idx_predictions_match_id", "predictions", ["match_id"])
    _create_index_if_cols_exist(conn, insp, "idx_predictions_timestamp", "predictions", ["timestamp"])
    _create_index_if_cols_exist(conn, insp, "idx_predictions_was_correct", "predictions", ["was_correct"])

    # --- clv_entries table ---
    _create_index_if_cols_exist(conn, insp, "idx_clv_entries_prediction_id", "clv_entries", ["prediction_id"])
    _create_index_if_cols_exist(conn, insp, "idx_clv_entries_match_id", "clv_entries", ["match_id"])
    _create_index_if_cols_exist(conn, insp, "idx_clv_entries_user_id", "clv_entries", ["user_id"])

    # --- ai_predictions table ---
    _create_index_if_cols_exist(conn, insp, "idx_ai_predictions_is_certified", "ai_predictions", ["is_certified"])
    _create_index_if_cols_exist(conn, insp, "idx_ai_predictions_match_source", "ai_predictions", ["match_id", "source"])

    # --- matches table ---
    _create_index_if_cols_exist(conn, insp, "idx_matches_external_id", "matches", ["external_id"])
    _create_index_if_cols_exist(conn, insp, "idx_matches_status", "matches", ["status"])
    _create_index_if_cols_exist(conn, insp, "idx_matches_kickoff_status", "matches", ["kickoff_time", "status"])

    # --- audit_logs table ---
    _create_index_if_cols_exist(conn, insp, "idx_audit_logs_resource_id", "audit_logs", ["resource_id"])

    # --- users table ---
    _create_index_if_cols_exist(conn, insp, "idx_users_is_active", "users", ["is_active"])
    _create_index_if_cols_exist(conn, insp, "idx_users_last_login", "users", ["last_login"])


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    indexes = [
        ("idx_predictions_match_user", "predictions"),
        ("idx_predictions_user_id", "predictions"),
        ("idx_predictions_match_id", "predictions"),
        ("idx_predictions_timestamp", "predictions"),
        ("idx_predictions_was_correct", "predictions"),
        ("idx_clv_entries_prediction_id", "clv_entries"),
        ("idx_clv_entries_match_id", "clv_entries"),
        ("idx_clv_entries_user_id", "clv_entries"),
        ("idx_ai_predictions_is_certified", "ai_predictions"),
        ("idx_ai_predictions_match_source", "ai_predictions"),
        ("idx_matches_external_id", "matches"),
        ("idx_matches_status", "matches"),
        ("idx_matches_kickoff_status", "matches"),
        ("idx_audit_logs_resource_id", "audit_logs"),
        ("idx_users_is_active", "users"),
        ("idx_users_last_login", "users"),
    ]
    for idx_name, table_name in indexes:
        if insp.has_table(table_name):
            try:
                op.drop_index(idx_name, table_name=table_name)
            except Exception:
                pass
