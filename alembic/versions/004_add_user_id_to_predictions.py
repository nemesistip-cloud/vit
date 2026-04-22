"""Add user_id to predictions table and fix related schema gaps

Revision ID: 004_add_user_id_to_predictions
Revises: fab045ad4db1
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = '004_add_user_id_to_predictions'
down_revision = '739d5e62d691'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id to predictions (nullable for backward compat)
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

    # Add user_id FK index
    op.create_index('idx_predictions_user_id', 'predictions', ['user_id'])

    # Add kyc fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('kyc_status', sa.String(20), server_default='none', nullable=True))
        batch_op.add_column(sa.Column('kyc_submitted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('kyc_data', sa.JSON(), nullable=True))

    # Add streak tracking to users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_streak', sa.Integer(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('best_streak', sa.Integer(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('total_xp', sa.Integer(), server_default='0', nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.drop_column('user_id')
    op.drop_index('idx_predictions_user_id', 'predictions')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('kyc_status')
        batch_op.drop_column('kyc_submitted_at')
        batch_op.drop_column('kyc_data')
        batch_op.drop_column('current_streak')
        batch_op.drop_column('best_streak')
        batch_op.drop_column('total_xp')
