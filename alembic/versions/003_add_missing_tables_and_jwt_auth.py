# alembic/versions/003_add_missing_tables_and_jwt_auth.py
"""Add users, training_jobs, training_guide_steps
(bankroll_states, decision_logs, teams, subscription_plans,
user_subscriptions, audit_logs, training_datasets were already
created by create_all — this migration adds only the new tables)

Revision ID: 003
Revises: fab045ad4db1
Create Date: 2026-04-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = 'fab045ad4db1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts(is_sqlite: bool) -> str:
    return 'CURRENT_TIMESTAMP' if is_sqlite else 'now()'


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    ts = _ts(is_sqlite)

    # ── users ──────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), server_default='user'),
        sa.Column('is_active', sa.Boolean(), server_default='1' if is_sqlite else 'true'),
        sa.Column('is_verified', sa.Boolean(), server_default='0' if is_sqlite else 'false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(ts)),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('email', name='uq_users_email'),
        sa.UniqueConstraint('username', name='uq_users_username'),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])

    # ── training_jobs (Module D1) ──────────────────────────────────────
    op.create_table(
        'training_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.String(64), nullable=False),
        sa.Column('status', sa.String(20), server_default='queued'),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('training_prompt', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(100), server_default='system'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(ts)),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('job_id', name='uq_training_jobs_job_id'),
    )
    op.create_index('idx_training_jobs_status', 'training_jobs', ['status'])

    # ── training_guide_steps (Module D1) ──────────────────────────────
    op.create_table(
        'training_guide_steps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id_fk', sa.Integer(), sa.ForeignKey('training_jobs.id'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(ts)),
    )


def downgrade() -> None:
    op.drop_table('training_guide_steps')
    op.drop_table('training_jobs')
    op.drop_index('idx_users_role', 'users')
    op.drop_index('idx_users_email', 'users')
    op.drop_table('users')
