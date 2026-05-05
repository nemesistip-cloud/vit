"""VIT DID — Decentralized Identity models.

did:vit:{uuid}        — user DID
did:vit:agent:{name}  — agent/node DID

W3C DID-compatible documents stored on-chain in Phase 2.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class VITIdentity(Base):
    """A DID document anchored to a user or agent node."""
    __tablename__ = "vit_identities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    did: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Subject — either a human user or an agent node
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "agent"
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # DID Document (W3C-compatible JSON)
    did_document: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    credentials: Mapped[list["VerifiableCredential"]] = relationship(
        "VerifiableCredential", back_populates="identity", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_vit_identity_user_id", "user_id"),
        Index("idx_vit_identity_agent", "agent_name"),
        Index("idx_vit_identity_subject_type", "subject_type"),
    )


class VerifiableCredential(Base):
    """A Verifiable Credential (VC) issued by the VIT network to an identity."""
    __tablename__ = "verifiable_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    identity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vit_identities.id", ondelete="CASCADE"), nullable=False
    )

    # VC type: kyc | validator | prediction_accuracy | node_contribution | oracle_node
    credential_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Issuer DID (always did:vit:network)
    issuer: Mapped[str] = mapped_column(String(255), default="did:vit:network", nullable=False)

    # Full VC payload (W3C JSON-LD compatible)
    credential: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Lifecycle
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    identity: Mapped["VITIdentity"] = relationship("VITIdentity", back_populates="credentials")

    __table_args__ = (
        Index("idx_vc_identity_id", "identity_id"),
        Index("idx_vc_type", "credential_type"),
        Index("idx_vc_revoked", "revoked"),
    )
