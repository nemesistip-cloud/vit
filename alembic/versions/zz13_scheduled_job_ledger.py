"""Add durable GitHub Actions scheduled job run ledger."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zz13_scheduled_job_ledger"
down_revision: Union[str, Sequence[str], None] = "zz12_developer_app_registry"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("scheduled_job_runs"):
        op.create_table(
            "scheduled_job_runs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("job_name", sa.String(length=80), nullable=False),
            sa.Column("schedule_key", sa.String(length=100), nullable=False),
            sa.Column("dry_run", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("status", sa.String(length=20), server_default="queued", nullable=False),
            sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
            sa.Column("current_attempt", sa.Integer(), nullable=True),
            sa.Column("claimed_by", sa.String(length=100), nullable=True),
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("job_name", "schedule_key", name="uq_scheduled_job_period"),
        )
        op.create_index("ix_scheduled_job_runs_id", "scheduled_job_runs", ["id"])
        op.create_index("ix_scheduled_job_runs_status", "scheduled_job_runs", ["status"])
        op.create_index(
            "idx_scheduled_job_claim",
            "scheduled_job_runs",
            ["status", "next_attempt_at", "lease_expires_at"],
        )

    if not _has_table("scheduled_job_attempts"):
        op.create_table(
            "scheduled_job_attempts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=False),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("runner_id", sa.String(length=100), nullable=False),
            sa.Column("claim_token_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=20), server_default="running", nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_code", sa.String(length=80), nullable=True),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(["run_id"], ["scheduled_job_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("run_id", "attempt_number", name="uq_scheduled_job_attempt"),
        )
        op.create_index("ix_scheduled_job_attempts_id", "scheduled_job_attempts", ["id"])
        op.create_index("ix_scheduled_job_attempts_run_id", "scheduled_job_attempts", ["run_id"])


def downgrade() -> None:
    if _has_table("scheduled_job_attempts"):
        op.drop_table("scheduled_job_attempts")
    if _has_table("scheduled_job_runs"):
        op.drop_table("scheduled_job_runs")
