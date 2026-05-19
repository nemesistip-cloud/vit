"""add user contact and google fields

Revision ID: 83df201f3ffa
Revises: ce54adb1005f
Create Date: 2026-05-19 04:47:49.034855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '83df201f3ffa'
down_revision: Union[str, None] = 'ce54adb1005f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('company_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('phone', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('google_id', sa.String(length=255), nullable=True))
        batch_op.alter_column('hashed_password',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
        batch_op.create_index(batch_op.f('ix_users_google_id'), ['google_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_google_id'))
        batch_op.alter_column('hashed_password',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
        batch_op.drop_column('google_id')
        batch_op.drop_column('phone')
        batch_op.drop_column('company_name')
