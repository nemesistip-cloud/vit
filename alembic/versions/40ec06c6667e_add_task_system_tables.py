# alembic/script.py.mako
"""Add task system tables

Revision ID: 40ec06c6667e
Revises: 739d5e62d691
Create Date: 2026-04-24 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40ec06c6667e'
down_revision: Union[str, None] = '739d5e62d691'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    ts = 'CURRENT_TIMESTAMP' if is_sqlite else 'now()'

    # Create task_categories table
    op.create_table('task_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_task_categories_name', 'task_categories', ['name'], unique=True)
    op.create_index('idx_task_categories_active', 'task_categories', ['is_active'], unique=False)

    # Create tasks table
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('task_type', sa.Enum('ONE_TIME', 'DAILY', 'WEEKLY', 'MONTHLY', 'PROGRESS', name='tasktype'), nullable=False),
        sa.Column('vit_reward', sa.Float(), nullable=False, default=0),
        sa.Column('xp_reward', sa.Integer(), nullable=False, default=0),
        sa.Column('max_progress', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_admin_only', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['task_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_tasks_category', 'tasks', ['category_id'], unique=False)
    op.create_index('idx_tasks_type', 'tasks', ['task_type'], unique=False)
    op.create_index('idx_tasks_active', 'tasks', ['is_active'], unique=False)

    # Create user_task_completions table
    op.create_table('user_task_completions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('current_progress', sa.Integer(), nullable=False, default=0),
        sa.Column('is_completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_reset_at', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text(ts), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_task_completions_user_task', 'user_task_completions', ['user_id', 'task_id'], unique=True)
    op.create_index('idx_user_task_completions_completed', 'user_task_completions', ['is_completed'], unique=False)
    op.create_index('idx_user_task_completions_reset', 'user_task_completions', ['last_reset_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('user_task_completions')
    op.drop_table('tasks')
    op.drop_table('task_categories')