"""Create persistence tables for the existing developer application lifecycle."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "zz12_developer_app_registry"
down_revision: Union[str, Sequence[str], None] = "zz11_prediction_settlement"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _create_indexes(table_name: str, indexes: tuple[tuple[str, tuple[str, ...]], ...]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {item["name"] for item in inspector.get_indexes(table_name)}
    for name, columns in indexes:
        if name not in existing:
            op.create_index(name, table_name, list(columns))


def upgrade() -> None:
    if _has_table("dev_api_keys"):
        columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("dev_api_keys")}
        if "app_id" not in columns:
            op.add_column("dev_api_keys", sa.Column("app_id", sa.String(length=64), nullable=True))
        if "scopes" not in columns:
            op.add_column("dev_api_keys", sa.Column("scopes", sa.JSON(), nullable=False, server_default="[]"))
        _create_indexes("dev_api_keys", (("ix_dev_api_keys_app_id", ("app_id",)),))

    if not _has_table("dev_apps"):
        op.create_table(
            "dev_apps",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("app_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("icon", sa.String(length=512), nullable=True),
            sa.Column("category", sa.String(length=64), nullable=False),
            sa.Column("dev_url", sa.String(length=512), nullable=True),
            sa.Column("prod_url", sa.String(length=512), nullable=True),
            sa.Column("requested_scopes", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("app_id"),
        )
    _create_indexes("dev_apps", (("ix_dev_apps_app_id", ("app_id",)), ("idx_dev_apps_user_id", ("user_id",)), ("idx_dev_apps_status", ("status",))))

    if not _has_table("dev_app_sandbox_configs"):
        op.create_table(
            "dev_app_sandbox_configs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("app_id", sa.Integer(), nullable=False),
            sa.Column("is_sandbox_enabled", sa.Boolean(), nullable=False),
            sa.Column("sandbox_api_key_id", sa.Integer(), nullable=True),
            sa.Column("endpoint_url", sa.String(length=512), nullable=True),
            sa.Column("test_fixtures", sa.JSON(), nullable=False),
            sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["app_id"], ["dev_apps.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["sandbox_api_key_id"], ["dev_api_keys.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("app_id"),
        )
        _create_indexes("dev_app_sandbox_configs", (("ix_dev_app_sandbox_configs_id", ("id",)),))

    if not _has_table("dev_app_releases"):
        op.create_table(
            "dev_app_releases",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("app_id", sa.Integer(), nullable=False),
            sa.Column("version", sa.String(length=32), nullable=False),
            sa.Column("changelog", sa.Text(), nullable=True),
            sa.Column("metadata_snapshot", sa.JSON(), nullable=False),
            sa.Column("review_status", sa.String(length=32), nullable=False),
            sa.Column("reviewer_notes", sa.Text(), nullable=True),
            sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["app_id"], ["dev_apps.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_indexes("dev_app_releases", (("ix_dev_app_releases_id", ("id",)), ("idx_dev_releases_app_id", ("app_id",)), ("idx_dev_releases_review_status", ("review_status",))))

    if not _has_table("dev_app_audit_logs"):
        op.create_table(
            "dev_app_audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("app_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["app_id"], ["dev_apps.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        _create_indexes("dev_app_audit_logs", (("ix_dev_app_audit_logs_id", ("id",)), ("idx_dev_app_audit_app_id", ("app_id",)), ("idx_dev_app_audit_created", ("created_at",)), ("ix_dev_app_audit_logs_user_id", ("user_id",))))


def downgrade() -> None:
    op.drop_table("dev_app_audit_logs")
    op.drop_table("dev_app_releases")
    op.drop_table("dev_app_sandbox_configs")
    op.drop_table("dev_apps")
    if _has_table("dev_api_keys"):
        inspector = sa.inspect(op.get_bind())
        indexes = {item["name"] for item in inspector.get_indexes("dev_api_keys")}
        if "ix_dev_api_keys_app_id" in indexes:
            op.drop_index("ix_dev_api_keys_app_id", table_name="dev_api_keys")
        columns = {column["name"] for column in inspector.get_columns("dev_api_keys")}
        if "scopes" in columns:
            op.drop_column("dev_api_keys", "scopes")
        if "app_id" in columns:
            op.drop_column("dev_api_keys", "app_id")