"""Add social intelligence tables

Revision ID: zz05_social_intelligence_tables
Revises: zz04_identity_member_tables, ff00aabbccdd
Create Date: 2026-08-16 18:50:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "zz05_social_intelligence_tables"
down_revision: Union[str, Sequence[str]] = ("zz04_identity_member_tables", "ff00aabbccdd")
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("social_signals"):
        op.create_table(
            "social_signals",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("source", sa.String(length=100), nullable=False),
            sa.Column("url", sa.String(length=500), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("topic", sa.String(length=100), nullable=True),
            sa.Column("entities", sa.JSON(), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=True),
            sa.Column("freshness_seconds", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("confidence", sa.Float(), nullable=True, server_default="1.0"),
            sa.Column("verification_status", sa.String(length=50), nullable=True, server_default="VERIFIED"),
            sa.Column("deduplication_key", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("deduplication_key")
        )
        op.create_index(op.f("ix_social_signals_id"), "social_signals", ["id"], unique=False)
        op.create_index(op.f("ix_social_signals_source"), "social_signals", ["source"], unique=False)
        op.create_index(op.f("ix_social_signals_topic"), "social_signals", ["topic"], unique=False)

    if not insp.has_table("social_opportunities"):
        op.create_table(
            "social_opportunities",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("signal_id", sa.String(length=36), nullable=False),
            sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("score_breakdown", sa.JSON(), nullable=True),
            sa.Column("reasoning", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True, server_default="1.0"),
            sa.Column("priority", sa.String(length=20), nullable=True, server_default="MEDIUM"),
            sa.Column("risk_flags", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["signal_id"], ["social_signals.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id")
        )
        op.create_index(op.f("ix_social_opportunities_id"), "social_opportunities", ["id"], unique=False)
        op.create_index(op.f("ix_social_opportunities_signal_id"), "social_opportunities", ["signal_id"], unique=False)

    if not insp.has_table("social_candidates"):
        op.create_table(
            "social_candidates",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("opportunity_id", sa.String(length=36), nullable=False),
            sa.Column("generated_content", sa.Text(), nullable=False),
            sa.Column("content_format", sa.String(length=50), nullable=True, server_default="TEXT"),
            sa.Column("provenance", sa.JSON(), nullable=True),
            sa.Column("risk_flags", sa.JSON(), nullable=True),
            sa.Column("state", sa.String(length=50), nullable=False, server_default="NEW"),
            sa.Column("review_history", sa.JSON(), nullable=True),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("reviewed_by", sa.String(length=100), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["opportunity_id"], ["social_opportunities.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id")
        )
        op.create_index(op.f("ix_social_candidates_id"), "social_candidates", ["id"], unique=False)
        op.create_index(op.f("ix_social_candidates_opportunity_id"), "social_candidates", ["opportunity_id"], unique=False)
        op.create_index(op.f("ix_social_candidates_state"), "social_candidates", ["state"], unique=False)

    if not insp.has_table("social_publication_records"):
        op.create_table(
            "social_publication_records",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("candidate_id", sa.String(length=36), nullable=False),
            sa.Column("platform", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
            sa.Column("external_ref", sa.String(length=255), nullable=True),
            sa.Column("url", sa.String(length=500), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            sa.ForeignKeyConstraint(["candidate_id"], ["social_candidates.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("candidate_id", "platform", name="uq_candidate_platform_publication")
        )
        op.create_index(op.f("ix_social_publication_records_id"), "social_publication_records", ["id"], unique=False)
        op.create_index(op.f("ix_social_publication_records_candidate_id"), "social_publication_records", ["candidate_id"], unique=False)
        op.create_index(op.f("ix_social_publication_records_platform"), "social_publication_records", ["platform"], unique=False)
        op.create_index(op.f("ix_social_publication_records_status"), "social_publication_records", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("social_publication_records")
    op.drop_table("social_candidates")
    op.drop_table("social_opportunities")
    op.drop_table("social_signals")
