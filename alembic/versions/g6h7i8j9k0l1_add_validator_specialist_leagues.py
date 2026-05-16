"""add specialist_leagues to validator_profiles

Revision ID: g6h7i8j9k0l1
Revises: fab045ad4db1
Create Date: 2026-05-16 22:55:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'g6h7i8j9k0l1'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('validator_profiles', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('specialist_leagues', sa.String(length=255), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('validator_profiles', schema=None) as batch_op:
        batch_op.drop_column('specialist_leagues')
