"""merge final heads

Revision ID: ee1f2c3d4e5f
Revises: 83df201f3ffa, d3e4f5a6b7c8
Create Date: 2026-06-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee1f2c3d4e5f'
down_revision: Union[str, None] = ('83df201f3ffa', 'd3e4f5a6b7c8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
