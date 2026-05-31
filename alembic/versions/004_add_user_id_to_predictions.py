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


def _existing_columns(bind, table: str) -> set:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _existing_indexes(bind, table: str) -> set:
    return {i["name"] for i in sa.inspect(bind).get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()

    pred_cols = _existing_columns(bind, "predictions")
    if "user_id" not in pred_cols:
        with op.batch_alter_table('predictions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))

    if "idx_predictions_user_id" not in _existing_indexes(bind, "predictions"):
        op.create_index('idx_predictions_user_id', 'predictions', ['user_id'])

    user_cols = _existing_columns(bind, "users")
    to_add_users = []
    if "kyc_status" not in user_cols:
        to_add_users.append(sa.Column('kyc_status', sa.String(20), server_default='none', nullable=True))
    if "kyc_submitted_at" not in user_cols:
        to_add_users.append(sa.Column('kyc_submitted_at', sa.DateTime(timezone=True), nullable=True))
    if "kyc_data" not in user_cols:
        to_add_users.append(sa.Column('kyc_data', sa.JSON(), nullable=True))
    if "current_streak" not in user_cols:
        to_add_users.append(sa.Column('current_streak', sa.Integer(), server_default='0', nullable=True))
    if "best_streak" not in user_cols:
        to_add_users.append(sa.Column('best_streak', sa.Integer(), server_default='0', nullable=True))
    if "total_xp" not in user_cols:
        to_add_users.append(sa.Column('total_xp', sa.Integer(), server_default='0', nullable=True))

    if to_add_users:
        with op.batch_alter_table('users', schema=None) as batch_op:
            for col in to_add_users:
                batch_op.add_column(col)


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
