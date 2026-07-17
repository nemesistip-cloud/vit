"""add webhook_events table

Revision ID: a1b2c3d4e5f6
Revises: ee1f2c3d4e5f
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'ee1f2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('provider', sa.String(32), nullable=False),
        sa.Column('event_type', sa.String(128), nullable=True),
        sa.Column('reference', sa.String(256), nullable=True),
        sa.Column('amount', sa.Numeric(20, 8), nullable=True),
        sa.Column('currency', sa.String(16), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='received'),
        sa.Column('sig_verified', sa.Boolean(), nullable=True),
        sa.Column('outcome', sa.String(64), nullable=True),
        sa.Column('error_msg', sa.Text(), nullable=True),
        sa.Column('payload_summary', sa.JSON(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_webhook_events_provider', 'webhook_events', ['provider'])
    op.create_index('idx_webhook_events_reference', 'webhook_events', ['reference'])
    op.create_index('idx_webhook_events_received_at', 'webhook_events', ['received_at'])
    op.create_index('idx_webhook_events_provider_received', 'webhook_events', ['provider', 'received_at'])


def downgrade() -> None:
    op.drop_index('idx_webhook_events_provider_received', table_name='webhook_events')
    op.drop_index('idx_webhook_events_received_at', table_name='webhook_events')
    op.drop_index('idx_webhook_events_reference', table_name='webhook_events')
    op.drop_index('idx_webhook_events_provider', table_name='webhook_events')
    op.drop_table('webhook_events')
