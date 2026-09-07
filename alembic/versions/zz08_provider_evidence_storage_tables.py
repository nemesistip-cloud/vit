"""Create provider contribution, evidence, and storage verification tables."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision = "zz08_provider_evidence_storage_tables"
down_revision: Union[str, Sequence[str], None] = "zz07_consensus_state"
branch_labels = None
depends_on = None


def _create_table(name: str, *columns: sa.Column, constraints=()) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(name):
        op.create_table(name, *columns, *constraints)


def upgrade() -> None:
    _create_table(
        "node_activities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("node_id", sa.String(255), nullable=False),
        sa.Column("node_name", sa.String(100), nullable=False),
        sa.Column("node_type", sa.String(20), nullable=False),
        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("contribution_score", sa.Float(), nullable=True, server_default="1.0"),
        sa.Column("activity_meta", sa.JSON(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )
    _create_table(
        "network_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("total_nodes", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("active_nodes", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("total_contributions", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("oracle_submissions", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("validator_predictions", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("network_health_score", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("growth_rate_24h", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("top_nodes", sa.JSON(), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )
    _create_table(
        "evidence_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_completeness_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_data", sa.JSON(), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_critical_inputs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    _create_table(
        "market_requirement_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evidence_snapshot_id", sa.Integer(), sa.ForeignKey("evidence_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("market_key", sa.String(50), nullable=False),
        sa.Column("requirements_met", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    _create_table(
        "content_hash_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_hash", sa.String(66), nullable=False),
        sa.Column("ipfs_cid", sa.String(120), nullable=True),
        sa.Column("arweave_id", sa.String(120), nullable=True),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ref_type", sa.String(80), nullable=True),
        sa.Column("ref_id", sa.Integer(), nullable=True),
        sa.Column("replication_factor", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("availability_score", sa.Numeric(5, 4), nullable=True, server_default="1"),
        sa.Column("is_public", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("pinned", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("anchor_block", sa.Integer(), nullable=True),
        sa.Column("anchor_tx", sa.String(66), nullable=True),
        sa.Column("registered_at", sa.DateTime(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("is_tachyon", sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column("tachyon_shards", sa.Integer(), nullable=True),
        sa.Column("tachyon_parity_shards", sa.Integer(), nullable=True),
        sa.Column("quantum_state_hash", sa.String(66), nullable=True),
        constraints=(sa.UniqueConstraint("content_hash"),),
    )
    _create_table(
        "storage_proofs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_hash_registry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prover_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("node_address", sa.String(200), nullable=False),
        sa.Column("proof_type", sa.String(60), nullable=True, server_default="merkle"),
        sa.Column("proof_data", sa.Text(), nullable=False),
        sa.Column("proof_hash", sa.String(66), nullable=False),
        sa.Column("status", sa.String(32), nullable=True, server_default="PENDING"),
        sa.Column("stake_locked", sa.Numeric(20, 6), nullable=True, server_default="0"),
        sa.Column("reward_earned", sa.Numeric(20, 6), nullable=True, server_default="0"),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        constraints=(sa.UniqueConstraint("proof_hash"),),
    )
    _create_table(
        "storage_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("proof_id", sa.Integer(), sa.ForeignKey("storage_proofs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("challenger_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("challenge_nonce", sa.String(66), nullable=False),
        sa.Column("expected_response_hash", sa.String(66), nullable=False),
        sa.Column("actual_response_hash", sa.String(66), nullable=True),
        sa.Column("status", sa.String(32), nullable=True, server_default="OPEN"),
        sa.Column("slash_amount", sa.Numeric(20, 6), nullable=True, server_default="0"),
        sa.Column("response_deadline", sa.DateTime(), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        constraints=(sa.UniqueConstraint("proof_id"),),
    )
    _create_table(
        "data_availability_attestations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_id", sa.Integer(), sa.ForeignKey("content_hash_registry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attestor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("signature", sa.String(200), nullable=False),
        sa.Column("attested_at", sa.DateTime(), nullable=True),
        constraints=(sa.UniqueConstraint("content_id", "attestor_user_id"),),
    )
    _create_table(
        "tachyon_manifests",
        sa.Column("file_id", sa.String(36), primary_key=True),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("fragment_names", sa.JSON(), nullable=False),
        sa.Column("provider_mapping", sa.JSON(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    _create_table(
        "user_storage_nodes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("alias", sa.String(128), nullable=False),
        sa.Column("config_key", sa.String(256), nullable=False),
        sa.Column("status", sa.String(32), nullable=True, server_default="pending"),
        sa.Column("gb_contributed", sa.Numeric(14, 4), nullable=True, server_default="0"),
        sa.Column("quota_bytes", sa.Numeric(20, 0), nullable=True, server_default="0"),
        sa.Column("gb_used", sa.Numeric(14, 4), nullable=True, server_default="0"),
        sa.Column("tsc_earned", sa.Numeric(20, 8), nullable=True, server_default="0"),
        sa.Column("tsc_pending", sa.Numeric(20, 8), nullable=True, server_default="0"),
        sa.Column("reliability_score", sa.Numeric(5, 4), nullable=True, server_default="1.0000"),
        sa.Column("verification_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("verification_pass", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        constraints=(sa.UniqueConstraint("config_key"),),
    )

    inspector = sa.inspect(op.get_bind())
    indexes = {
        "node_activities": [("ix_node_activities_node_id", ["node_id"]), ("ix_node_activities_activity_type", ["activity_type"]), ("ix_node_activities_recorded_at", ["recorded_at"])],
        "network_snapshots": [("ix_network_snapshots_snapshot_at", ["snapshot_at"])],
        "evidence_snapshots": [("ix_evidence_snapshots_match_id", ["match_id"])],
        "market_requirement_results": [("ix_market_requirement_results_evidence_snapshot_id", ["evidence_snapshot_id"]), ("ix_market_requirement_results_market_key", ["market_key"])],
    }
    for table, table_indexes in indexes.items():
        existing = {index["name"] for index in inspector.get_indexes(table)}
        for index_name, columns in table_indexes:
            if index_name not in existing:
                op.create_index(index_name, table, columns)


def downgrade() -> None:
    # These tables were absent from the migration history; only remove them when
    # they exist, leaving unrelated application tables untouched.
    inspector = sa.inspect(op.get_bind())
    for table in (
        "user_storage_nodes",
        "tachyon_manifests",
        "data_availability_attestations",
        "storage_challenges",
        "storage_proofs",
        "content_hash_registry",
        "market_requirement_results",
        "evidence_snapshots",
        "network_snapshots",
        "node_activities",
    ):
        if inspector.has_table(table):
            op.drop_table(table)
