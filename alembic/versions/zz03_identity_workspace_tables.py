"""Add identity organizations and workspace settings tables

Revision ID: zz03_identity_workspace_tables
Revises: zz02_add_chain_and_slash_tables
Create Date: 2026-07-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "zz03_identity_workspace_tables"
down_revision = "zz02_add_chain_and_slash_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("identity_organizations"):
        op.create_table(
            "identity_organizations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_identity_organizations_slug"), "identity_organizations", ["slug"], unique=True)

    if not insp.has_table("identity_teams"):
        op.create_table(
            "identity_teams",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["organization_id"], ["identity_organizations.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_identity_teams_slug"), "identity_teams", ["slug"], unique=True)
        op.create_index(op.f("ix_identity_teams_organization_id"), "identity_teams", ["organization_id"], unique=False)

    if not insp.has_table("identity_workspace_settings"):
        op.create_table(
            "identity_workspace_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("value", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "key", name="uq_identity_workspace_setting_user_key"),
        )
        op.create_index(op.f("ix_identity_workspace_settings_key"), "identity_workspace_settings", ["key"], unique=False)
        op.create_index(op.f("ix_identity_workspace_settings_user_id"), "identity_workspace_settings", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("identity_workspace_settings"):
        op.drop_index(op.f("ix_identity_workspace_settings_user_id"), table_name="identity_workspace_settings")
        op.drop_index(op.f("ix_identity_workspace_settings_key"), table_name="identity_workspace_settings")
        op.drop_table("identity_workspace_settings")

    if insp.has_table("identity_teams"):
        op.drop_index(op.f("ix_identity_teams_organization_id"), table_name="identity_teams")
        op.drop_index(op.f("ix_identity_teams_slug"), table_name="identity_teams")
        op.drop_table("identity_teams")

    if insp.has_table("identity_organizations"):
        op.drop_index(op.f("ix_identity_organizations_slug"), table_name="identity_organizations")
        op.drop_table("identity_organizations")
