# alembic/script.py.mako
"""Add AI meta-layer tables

Revision ID: fab045ad4db1
Revises: 002
Create Date: 2026-04-13 06:59:04.484973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fab045ad4db1'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    ts = 'CURRENT_TIMESTAMP' if is_sqlite else 'now()'

    # Add external_id to matches table
    op.add_column('matches', sa.Column('external_id', sa.String(), nullable=True))
    op.create_index('idx_matches_external_id', 'matches', ['external_id'], unique=True)

    # Create ai_predictions table
    op.create_table('ai_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('home_prob', sa.Float(), nullable=False),
        sa.Column('draw_prob', sa.Float(), nullable=False),
        sa.Column('away_prob', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('is_certified', sa.Boolean(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.Column('was_correct', sa.Boolean(), nullable=True),
        sa.Column('calibration_error', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_ai_match_source', 'ai_predictions', ['match_id', 'source'], unique=False)
    op.create_index('idx_ai_timestamp', 'ai_predictions', ['timestamp'], unique=False)

    # Create ai_performances table
    op.create_table('ai_performances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('calibration_score', sa.Float(), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('bias_home_overrate', sa.Float(), nullable=True),
        sa.Column('bias_draw_overrate', sa.Float(), nullable=True),
        sa.Column('bias_away_overrate', sa.Float(), nullable=True),
        sa.Column('league_accuracy', sa.JSON(), nullable=True),
        sa.Column('current_weight', sa.Float(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_predictions', sa.Integer(), nullable=True),
        sa.Column('certified', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source')
    )

    # Create ai_signal_cache table
    op.create_table('ai_signal_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('consensus_home', sa.Float(), nullable=False),
        sa.Column('consensus_draw', sa.Float(), nullable=False),
        sa.Column('consensus_away', sa.Float(), nullable=False),
        sa.Column('disagreement_score', sa.Float(), nullable=False),
        sa.Column('max_confidence', sa.Float(), nullable=False),
        sa.Column('weighted_home', sa.Float(), nullable=False),
        sa.Column('weighted_draw', sa.Float(), nullable=False),
        sa.Column('weighted_away', sa.Float(), nullable=False),
        sa.Column('per_ai_predictions', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_id')
    )
    op.create_index('idx_ai_signal_cache_match', 'ai_signal_cache', ['match_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_ai_signal_cache_match', table_name='ai_signal_cache')
    op.drop_table('ai_signal_cache')
    op.drop_table('ai_performances')
    op.drop_index('idx_ai_timestamp', table_name='ai_predictions')
    op.drop_index('idx_ai_match_source', table_name='ai_predictions')
    op.drop_table('ai_predictions')
    op.drop_index('idx_matches_external_id', table_name='matches')
    op.drop_column('matches', 'external_id')