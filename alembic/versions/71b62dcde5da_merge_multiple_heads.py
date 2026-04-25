# alembic/script.py.mako
"""merge multiple heads

Revision ID: 71b62dcde5da
Revises: 006, 40ec06c6667e
Create Date: 2026-04-25 18:40:37.196297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71b62dcde5da'
down_revision: Union[str, None] = ('006', '40ec06c6667e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass