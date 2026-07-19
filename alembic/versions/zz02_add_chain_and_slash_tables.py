"""add_chain_and_slash_tables

Revision ID: zz02_add_chain_and_slash_tables
Revises: zz01_add_missing_indexes
Create Date: 2026-07-19 00:00:00.000000

Phase 1 gate migration — creates:
  vit_blocks         — canonical VIT Chain block record
  validator_stakes   — on-chain validator stake registry
  slash_events       — immutable slashing log (DOUBLE_SIGN / DOWNTIME / INVALID_BLOCK)
  slash_appeals      — validator appeal requests for governance review

All DDL uses IF NOT EXISTS / IF EXISTS so the migration is safe to re-run.
"""
from alembic import op
import sqlalchemy as sa

revision      = "zz02_add_chain_and_slash_tables"
down_revision = "zz01_add_missing_indexes"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    # ── vit_blocks ────────────────────────────────────────────────────────────
    op.create_table(
        "vit_blocks",
        sa.Column("id",          sa.Integer,            primary_key=True,                autoincrement=True),
        sa.Column("height",      sa.Integer,            nullable=False),
        sa.Column("chain_id",    sa.Integer,            nullable=False, server_default="7764"),
        sa.Column("hash",        sa.String(66),         nullable=False),
        sa.Column("parent_hash", sa.String(66),         nullable=False),
        sa.Column("proposer",    sa.String(255),        nullable=True),
        sa.Column("tx_count",    sa.Integer,            server_default="0"),
        sa.Column("extra_data",  sa.Text,               nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()")),
        if_not_exists=True,
    )
    op.create_index("ix_vit_blocks_height",  "vit_blocks", ["height"],  unique=True, if_not_exists=True)
    op.create_index("ix_vit_blocks_hash",    "vit_blocks", ["hash"],    unique=True, if_not_exists=True)
    op.create_index("ix_vit_blocks_proposer","vit_blocks", ["proposer"],              if_not_exists=True)

    # ── validator_stakes ──────────────────────────────────────────────────────
    op.create_table(
        "validator_stakes",
        sa.Column("id",           sa.Integer,            primary_key=True, autoincrement=True),
        sa.Column("address",      sa.String(255),        nullable=False),
        sa.Column("label",        sa.String(100),        nullable=True),
        sa.Column("stake_amount", sa.Integer,            nullable=False, server_default="0"),
        sa.Column("active",       sa.Boolean,            nullable=False, server_default="true"),
        sa.Column("joined_at",    sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at",   sa.DateTime(timezone=True), nullable=True),
        if_not_exists=True,
    )
    op.create_index("ix_validator_stakes_address", "validator_stakes", ["address"], unique=True, if_not_exists=True)
    op.create_index("ix_validator_stakes_active",  "validator_stakes", ["active"],               if_not_exists=True)

    # ── slash_events ──────────────────────────────────────────────────────────
    op.create_table(
        "slash_events",
        sa.Column("id",                   sa.Integer,       primary_key=True, autoincrement=True),
        sa.Column("validator_address",    sa.String(255),   nullable=False),
        sa.Column("reason",               sa.String(32),    nullable=False),
        sa.Column("slash_amount",         sa.Integer,       nullable=False),
        sa.Column("stake_before",         sa.Integer,       nullable=False),
        sa.Column("stake_after",          sa.Integer,       nullable=False),
        sa.Column("evidence",             sa.Text,          nullable=True),
        sa.Column("appeal_deadline_slot", sa.Integer,       nullable=True),
        sa.Column("created_at",           sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["validator_address"], ["validator_stakes.address"],
                                name="fk_slash_events_validator"),
        if_not_exists=True,
    )
    op.create_index("ix_slash_events_validator",        "slash_events", ["validator_address"],             if_not_exists=True)
    op.create_index("ix_slash_events_reason",           "slash_events", ["reason"],                        if_not_exists=True)
    op.create_index("ix_slash_events_validator_reason", "slash_events", ["validator_address", "reason"],   if_not_exists=True)

    # ── slash_appeals ─────────────────────────────────────────────────────────
    op.create_table(
        "slash_appeals",
        sa.Column("id",                sa.Integer,      primary_key=True, autoincrement=True),
        sa.Column("slash_event_id",    sa.Integer,      nullable=False),
        sa.Column("validator_address", sa.String(255),  nullable=False),
        sa.Column("justification",     sa.Text,         nullable=False),
        sa.Column("status",            sa.String(16),   nullable=False, server_default="PENDING"),
        sa.Column("reviewed_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes",    sa.Text,         nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["slash_event_id"], ["slash_events.id"],
                                name="fk_slash_appeals_event"),
        if_not_exists=True,
    )
    op.create_index("ix_slash_appeals_event",     "slash_appeals", ["slash_event_id"],    if_not_exists=True)
    op.create_index("ix_slash_appeals_validator", "slash_appeals", ["validator_address"], if_not_exists=True)
    op.create_index("ix_slash_appeals_status",    "slash_appeals", ["status"],            if_not_exists=True)


def downgrade() -> None:
    op.drop_table("slash_appeals",     if_exists=True)
    op.drop_table("slash_events",      if_exists=True)
    op.drop_table("validator_stakes",  if_exists=True)
    op.drop_table("vit_blocks",        if_exists=True)
