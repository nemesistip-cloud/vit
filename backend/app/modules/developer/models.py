# app/modules/developer/models.py
"""Developer Platform & SDK database models — Module L."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, JSON,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class APIKey(Base):
    """L1 — Developer API key."""
    __tablename__ = "dev_api_keys"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id         : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name            : Mapped[str]      = mapped_column(String(128), nullable=False)
    key_prefix      : Mapped[str]      = mapped_column(String(12), nullable=False)        # first 12 chars — shown to user
    key_hash        : Mapped[str]      = mapped_column(String(128), unique=True, nullable=False)  # bcrypt hash
    key_plain       : Mapped[str]      = mapped_column(String(64), nullable=True)         # shown once on creation, then nulled

    plan            : Mapped[str]      = mapped_column(String(32), default="free")        # free | starter | pro | enterprise
    app_id          : Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scopes          : Mapped[list]     = mapped_column(JSON, default=list, nullable=False)
    rate_limit_rpm  : Mapped[int]      = mapped_column(Integer, default=60)               # requests per minute
    rate_limit_rpd  : Mapped[int]      = mapped_column(Integer, default=1000)             # requests per day

    is_active       : Mapped[bool]     = mapped_column(Boolean, default=True)
    last_used_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    total_requests  : Mapped[int]      = mapped_column(Integer, default=0)
    total_vitcoin_billed : Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    user        = relationship("User", foreign_keys=[user_id])
    usage_logs  = relationship("APIUsageLog", back_populates="api_key", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_dev_key_user_id",   "user_id"),
        Index("idx_dev_key_prefix",    "key_prefix"),
        Index("idx_dev_key_is_active", "is_active"),
    )


class APIUsageLog(Base):
    """L2 — One row per authenticated API call made with a developer key."""
    __tablename__ = "dev_api_usage_logs"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    api_key_id      : Mapped[int]      = mapped_column(Integer, ForeignKey("dev_api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    endpoint        : Mapped[str]      = mapped_column(String(255), nullable=False)
    method          : Mapped[str]      = mapped_column(String(8), nullable=False)         # GET | POST | …
    status_code     : Mapped[int]      = mapped_column(Integer, nullable=False)
    latency_ms      : Mapped[int]      = mapped_column(Integer, nullable=True)

    vitcoin_billed  : Mapped[Decimal]  = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))

    ip_address      : Mapped[str]      = mapped_column(String(45), nullable=True)
    user_agent      : Mapped[str]      = mapped_column(String(255), nullable=True)

    called_at       : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    api_key = relationship("APIKey", back_populates="usage_logs")
    user    = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_dev_usage_key_id",   "api_key_id"),
        Index("idx_dev_usage_user_id",  "user_id"),
        Index("idx_dev_usage_called_at","called_at"),
    )


class APIKeyPlan(Base):
    """L3 — Plan definitions (admin-managed)."""
    __tablename__ = "dev_api_plans"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    name            : Mapped[str]      = mapped_column(String(32), unique=True, nullable=False)
    display_name    : Mapped[str]      = mapped_column(String(64), nullable=False)
    rate_limit_rpm  : Mapped[int]      = mapped_column(Integer, nullable=False)
    rate_limit_rpd  : Mapped[int]      = mapped_column(Integer, nullable=False)
    price_vitcoin_per_1k : Mapped[Decimal] = mapped_column(Numeric(20, 8), default=Decimal("0.00000000"))
    description     : Mapped[str]      = mapped_column(Text, nullable=True)
    is_active       : Mapped[bool]     = mapped_column(Boolean, default=True)

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookEndpoint(Base):
    """L4 — Developer registered webhook callback endpoint."""
    __tablename__ = "dev_webhooks"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id         : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    url             : Mapped[str]      = mapped_column(String(512), nullable=False)
    description     : Mapped[str]      = mapped_column(String(255), nullable=True)
    secret          : Mapped[str]      = mapped_column(String(128), nullable=False)       # HMAC signing secret
    events          : Mapped[list]     = mapped_column(JSON, default=list)                # list of event strings, e.g. ["prediction.resolved", "match.started"]

    is_active       : Mapped[bool]     = mapped_column(Boolean, default=True)
    failure_count   : Mapped[int]      = mapped_column(Integer, default=0)
    last_called_at  : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user          = relationship("User", foreign_keys=[user_id])
    delivery_logs = relationship("WebhookDeliveryLog", back_populates="webhook", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_dev_webhook_user_id",   "user_id"),
        Index("idx_dev_webhook_is_active", "is_active"),
    )


class WebhookDeliveryLog(Base):
    """L5 — Delivery history for developer webhooks."""
    __tablename__ = "dev_webhook_logs"

    id              : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    webhook_id      : Mapped[int]      = mapped_column(Integer, ForeignKey("dev_webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id         : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type      : Mapped[str]      = mapped_column(String(64), nullable=False)
    payload         : Mapped[dict]     = mapped_column(JSON, nullable=False)
    status_code     : Mapped[int]      = mapped_column(Integer, nullable=True)
    response_body   : Mapped[str]      = mapped_column(Text, nullable=True)
    latency_ms      : Mapped[int]      = mapped_column(Integer, nullable=True)
    success         : Mapped[bool]     = mapped_column(Boolean, default=False)
    error_message   : Mapped[str]      = mapped_column(Text, nullable=True)

    delivered_at    : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    webhook = relationship("WebhookEndpoint", back_populates="delivery_logs")
    user    = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_dev_wh_log_webhook_id",  "webhook_id"),
        Index("idx_dev_wh_log_user_id",     "user_id"),
        Index("idx_dev_wh_log_delivered_at","delivered_at"),
    )


class DeveloperApp(Base):
    """L6 — Registered Developer Application."""
    __tablename__ = "dev_apps"

    id                  : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    app_id              : Mapped[str]      = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id             : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name                : Mapped[str]      = mapped_column(String(128), nullable=False)
    description         : Mapped[str]      = mapped_column(Text, nullable=True)
    icon                : Mapped[str]      = mapped_column(String(512), nullable=True)
    category            : Mapped[str]      = mapped_column(String(64), default="General")

    dev_url             : Mapped[str]      = mapped_column(String(512), nullable=True)
    prod_url            : Mapped[str]      = mapped_column(String(512), nullable=True)

    requested_scopes    : Mapped[list]     = mapped_column(JSON, default=list)
    status              : Mapped[str]      = mapped_column(String(32), default="draft")  # draft | sandbox_testing | review_pending | approved | published | rejected | suspended

    created_at          : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at          : Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user                = relationship("User", foreign_keys=[user_id])
    sandbox_config      = relationship("AppSandboxConfig", back_populates="app", uselist=False, cascade="all, delete-orphan")
    releases            = relationship("AppRelease", back_populates="app", cascade="all, delete-orphan")
    audit_logs          = relationship("AppAuditLog", back_populates="app", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_dev_apps_user_id", "user_id"),
        Index("idx_dev_apps_status",  "status"),
    )


class AppSandboxConfig(Base):
    """L7 — Sandbox configuration & test fixture parameters for a developer application."""
    __tablename__ = "dev_app_sandbox_configs"

    id                  : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    app_id              : Mapped[int]      = mapped_column(Integer, ForeignKey("dev_apps.id", ondelete="CASCADE"), unique=True, nullable=False)

    is_sandbox_enabled  : Mapped[bool]     = mapped_column(Boolean, default=True)
    sandbox_api_key_id  : Mapped[int]      = mapped_column(Integer, ForeignKey("dev_api_keys.id", ondelete="SET NULL"), nullable=True)
    endpoint_url        : Mapped[str]      = mapped_column(String(512), nullable=True)
    test_fixtures       : Mapped[dict]     = mapped_column(JSON, default=dict)
    last_tested_at      : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at          : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at          : Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    app                 = relationship("DeveloperApp", back_populates="sandbox_config")
    sandbox_api_key     = relationship("APIKey", foreign_keys=[sandbox_api_key_id])


class AppRelease(Base):
    """L8 — Application releases, metadata snapshots & review decisions."""
    __tablename__ = "dev_app_releases"

    id                  : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    app_id              : Mapped[int]      = mapped_column(Integer, ForeignKey("dev_apps.id", ondelete="CASCADE"), nullable=False, index=True)

    version             : Mapped[str]      = mapped_column(String(32), nullable=False, default="1.0.0")
    changelog           : Mapped[str]      = mapped_column(Text, nullable=True)
    metadata_snapshot   : Mapped[dict]     = mapped_column(JSON, default=dict)

    review_status       : Mapped[str]      = mapped_column(String(32), default="pending")  # pending | approved | rejected
    reviewer_notes      : Mapped[str]      = mapped_column(Text, nullable=True)
    reviewed_by_id      : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    submitted_at        : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at         : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    app                 = relationship("DeveloperApp", back_populates="releases")
    reviewed_by         = relationship("User", foreign_keys=[reviewed_by_id])

    __table_args__ = (
        Index("idx_dev_releases_app_id",        "app_id"),
        Index("idx_dev_releases_review_status", "review_status"),
    )


class AppAuditLog(Base):
    """L9 — Developer application audit events."""
    __tablename__ = "dev_app_audit_logs"

    id                  : Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    app_id              : Mapped[int]      = mapped_column(Integer, ForeignKey("dev_apps.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id             : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type          : Mapped[str]      = mapped_column(String(64), nullable=False)
    details             : Mapped[dict]     = mapped_column(JSON, default=dict)

    created_at          : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    app                 = relationship("DeveloperApp", back_populates="audit_logs")
    user                = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_dev_app_audit_app_id", "app_id"),
        Index("idx_dev_app_audit_created", "created_at"),
    )
