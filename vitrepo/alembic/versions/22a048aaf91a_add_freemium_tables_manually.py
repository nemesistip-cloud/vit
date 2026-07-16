"""Add freemium tables manually

Revision ID: 22a048aaf91a
Revises: a1b2c3d4e5f6
Create Date: 2026-06-12 20:24:21.127475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '22a048aaf91a'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # iq_test_questions
    op.create_table(
        'iq_test_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('q', sa.Text(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=False),
        sa.Column('correct', sa.Integer(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_iq_test_questions_id'), 'iq_test_questions', ['id'], unique=False)

    # user_iq_test_results
    op.create_table(
        'user_iq_test_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('iq_score', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(length=50), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_iq_test_results_id'), 'user_iq_test_results', ['id'], unique=False)
    op.create_index(op.f('ix_user_iq_test_results_user_id'), 'user_iq_test_results', ['user_id'], unique=False)

    # oracle_mic_episodes
    op.create_table(
        'oracle_mic_episodes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('host', sa.String(length=100), nullable=False),
        sa.Column('date', sa.String(length=50), nullable=False),
        sa.Column('length', sa.String(length=20), nullable=False),
        sa.Column('premium', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_oracle_mic_episodes_id'), 'oracle_mic_episodes', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_oracle_mic_episodes_id'), table_name='oracle_mic_episodes')
    op.drop_table('oracle_mic_episodes')
    op.drop_index(op.f('ix_user_iq_test_results_user_id'), table_name='user_iq_test_results')
    op.drop_index(op.f('ix_user_iq_test_results_id'), table_name='user_iq_test_results')
    op.drop_table('user_iq_test_results')
    op.drop_index(op.f('ix_iq_test_questions_id'), table_name='iq_test_questions')
    op.drop_table('iq_test_questions')
