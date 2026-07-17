"""add_quota_bytes_to_user_storage_node

Revision ID: cce3c1ccd7ef
Revises: ee1f2c3d4e5f
Create Date: 2024-06-22 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cce3c1ccd7ef'
down_revision = 'ee1f2c3d4e5f'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('user_storage_nodes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quota_bytes', sa.Numeric(precision=20, scale=0), nullable=True))

def downgrade():
    with op.batch_alter_table('user_storage_nodes', schema=None) as batch_op:
        batch_op.drop_column('quota_bytes')
