"""Add identity organization & team member tables

Revision ID: zz04_identity_member_tables
Revises: zz03_identity_workspace_tables
Create Date: 2026-08-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "zz04_identity_member_tables"
down_revision = "zz03_identity_workspace_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # identity_organization_members -------------------------------------------
    op.create_table(
        "identity_organization_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_in_org", sa.String(length=50), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["identity_organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_org_member_org_user"
        ),
    )
    op.create_index(
        "idx_org_member_org_id", "identity_organization_members", ["organization_id"]
    )
    op.create_index(
        "idx_org_member_user_id", "identity_organization_members", ["user_id"]
    )

    # identity_team_members ---------------------------------------------------
    op.create_table(
        "identity_team_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_in_team", sa.String(length=50), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["team_id"], ["identity_teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_member_team_user"),
    )
    op.create_index(
        "idx_team_member_team_id", "identity_team_members", ["team_id"]
    )
    op.create_index(
        "idx_team_member_user_id", "identity_team_members", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_team_member_user_id", table_name="identity_team_members")
    op.drop_index("idx_team_member_team_id", table_name="identity_team_members")
    op.drop_table("identity_team_members")

    op.drop_index("idx_org_member_user_id", table_name="identity_organization_members")
    op.drop_index("idx_org_member_org_id", table_name="identity_organization_members")
    op.drop_table("identity_organization_members")
