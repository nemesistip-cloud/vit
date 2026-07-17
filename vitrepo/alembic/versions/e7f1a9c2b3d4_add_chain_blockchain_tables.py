"""add_chain_blockchain_tables

Revision ID: e7f1a9c2b3d4
Revises: 22a048aaf91a, cce3c1ccd7ef
Create Date: 2026-07-11 21:00:00.000000

The VIT Chain ORM models (ChainBlock/ChainTransaction/ChainAccount, defined
in vit_chain/storage/db.py against the shared declarative Base) were never
given an Alembic migration. Production only ever relied on
Base.metadata.create_all() running at kernel boot, which silently no-ops
when it races with import order / partial failures, leaving 'chain_blocks'
missing in production Postgres. That produced 'relation chain_blocks does
not exist' on every explorer/blockchain request and cascaded into the
blockchain subsystem reporting UNHEALTHY.

This migration creates the tables explicitly so `alembic upgrade heads`
(already run on every deploy by scripts/start_production.sh) guarantees
they exist, independent of runtime import order.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e7f1a9c2b3d4'
down_revision = ('22a048aaf91a', 'cce3c1ccd7ef')
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade():
    if not _has_table('chain_blocks'):
        op.create_table(
            'chain_blocks',
            sa.Column('height', sa.Integer(), primary_key=True),
            sa.Column('block_hash', sa.String(length=64), nullable=False),
            sa.Column('prev_hash', sa.String(length=64), nullable=True),
            sa.Column('merkle_root', sa.String(length=64), nullable=True),
            sa.Column('state_root', sa.String(length=64), nullable=True),
            sa.Column('timestamp', sa.Integer(), nullable=True),
            sa.Column('validator_id', sa.String(length=64), nullable=True),
            sa.Column('validator_signature', sa.String(length=256), nullable=True),
            sa.Column('tx_count', sa.Integer(), nullable=True),
            sa.Column('total_fees', sa.Numeric(precision=36, scale=18), nullable=True),
            sa.Column('block_reward', sa.Numeric(precision=36, scale=18), nullable=True),
            sa.Column('raw_data', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index('ix_chain_blocks_block_hash', 'chain_blocks', ['block_hash'], unique=True)
        op.create_index('ix_chain_blocks_prev_hash', 'chain_blocks', ['prev_hash'])
        op.create_index('ix_chain_blocks_timestamp', 'chain_blocks', ['timestamp'])
        op.create_index('ix_chain_blocks_validator_id', 'chain_blocks', ['validator_id'])

    if not _has_table('chain_transactions'):
        op.create_table(
            'chain_transactions',
            sa.Column('tx_hash', sa.String(length=64), primary_key=True),
            sa.Column('block_height', sa.Integer(), sa.ForeignKey('chain_blocks.height'), nullable=True),
            sa.Column('from_address', sa.String(length=64), nullable=True),
            sa.Column('to_address', sa.String(length=64), nullable=True),
            sa.Column('amount', sa.Numeric(precision=36, scale=18), nullable=True),
            sa.Column('nonce', sa.Integer(), nullable=True),
            sa.Column('gas_fee', sa.Numeric(precision=36, scale=18), nullable=True),
            sa.Column('tx_type', sa.String(length=20), nullable=True),
            sa.Column('data', sa.JSON(), nullable=True),
            sa.Column('signature', sa.String(length=256), nullable=True),
            sa.Column('timestamp', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
        )
        op.create_index('ix_chain_transactions_block_height', 'chain_transactions', ['block_height'])
        op.create_index('ix_chain_transactions_from_address', 'chain_transactions', ['from_address'])
        op.create_index('ix_chain_transactions_to_address', 'chain_transactions', ['to_address'])
        op.create_index('ix_chain_transactions_timestamp', 'chain_transactions', ['timestamp'])
        op.create_index('ix_chain_transactions_status', 'chain_transactions', ['status'])

    if not _has_table('chain_accounts'):
        op.create_table(
            'chain_accounts',
            sa.Column('address', sa.String(length=64), primary_key=True),
            sa.Column('balance', sa.Numeric(precision=36, scale=18), server_default='0', nullable=True),
            sa.Column('staked', sa.Numeric(precision=36, scale=18), server_default='0', nullable=True),
            sa.Column('nonce', sa.Integer(), server_default='0', nullable=True),
            sa.Column('first_seen_height', sa.Integer(), nullable=True),
            sa.Column('last_active_height', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )


def downgrade():
    if _has_table('chain_transactions'):
        op.drop_table('chain_transactions')
    if _has_table('chain_blocks'):
        op.drop_table('chain_blocks')
    if _has_table('chain_accounts'):
        op.drop_table('chain_accounts')
