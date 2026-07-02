import enum
from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Text, Enum, Index
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from app.db.database import Base

class IdentityType(str, enum.Enum):
    INDIVIDUAL = "individual"
    ADMIN = "admin"
    VALIDATOR = "validator"
    INSTITUTION = "institution"
    ORGANIZATION = "organization"
    TEAM = "team"
    SERVICE_ACCOUNT = "service_account"
    SYSTEM_ACCOUNT = "system_account"
    EXTERNAL = "external"

class IdentityStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
    DELETED = "deleted"

class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class GlobalIdentity(Base):
    """Authoritative Global Identity model for the VIT Ecosystem."""
    __tablename__ = "global_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Immutable Global Identity ID (e.g. VIT-ID-8X9P-2K5M)
    gid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    type: Mapped[IdentityType] = mapped_column(Enum(IdentityType), default=IdentityType.INDIVIDUAL)
    status: Mapped[IdentityStatus] = mapped_column(Enum(IdentityStatus), default=IdentityStatus.ACTIVE)
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), default=VerificationStatus.UNVERIFIED)

    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(150))

    # Profile data (JSONB for flexibility)
    profile: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Authentication methods enabled for this identity
    auth_methods: Mapped[List[str]] = mapped_column(JSON, default=list) # e.g. ["password", "mfa_totp", "webauthn"]

    # Security metadata
    security_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    sessions = relationship("IdentitySession", back_populates="identity", cascade="all, delete-orphan")
    devices = relationship("TrustedDevice", back_populates="identity", cascade="all, delete-orphan")

class IdentitySession(Base):
    __tablename__ = "identity_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identity_id: Mapped[int] = mapped_column(Integer, ForeignKey("global_identities.id", ondelete="CASCADE"), nullable=False)

    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)

    device_id: Mapped[Optional[str]] = mapped_column(String(100))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    identity = relationship("GlobalIdentity", back_populates="sessions")

class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identity_id: Mapped[int] = mapped_column(Integer, ForeignKey("global_identities.id", ondelete="CASCADE"), nullable=False)

    device_id: Mapped[str] = mapped_column(String(100), nullable=False)
    platform: Mapped[Optional[str]] = mapped_column(String(50))
    browser: Mapped[Optional[str]] = mapped_column(String(50))

    is_trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_score: Mapped[float] = mapped_column(Integer, default=0) # 0-100

    last_ip: Mapped[Optional[str]] = mapped_column(String(45))
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    identity = relationship("GlobalIdentity", back_populates="devices")

    __table_args__ = (
        Index("idx_device_identity", "identity_id", "device_id", unique=True),
    )
