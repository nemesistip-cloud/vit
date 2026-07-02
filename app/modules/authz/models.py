from __future__ import annotations
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Table, JSON, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.database import Base

# Association Table: Users <-> Roles
user_roles = Table(
    "authz_user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("authz_roles.id", ondelete="CASCADE"), primary_key=True),
    Index("idx_authz_user_roles_user", "user_id"),
    Index("idx_authz_user_roles_role", "role_id"),
)

# Association Table: Roles <-> Permissions
role_permissions = Table(
    "authz_role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("authz_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("authz_permissions.id", ondelete="CASCADE"), primary_key=True),
    Index("idx_authz_role_perms_role", "role_id"),
    Index("idx_authz_role_perms_perm", "permission_id"),
)

class AuthzEffect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"

class Permission(Base):
    """Granular permission definition (e.g., wallet.read)."""
    __tablename__ = "authz_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class Role(Base):
    """Institutional or custom role."""
    __tablename__ = "authz_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Hierarchical roles
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("authz_roles.id"), nullable=True)

    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    parent = relationship("Role", remote_side=[id], backref="children")

class Resource(Base):
    """Securable system resource."""
    __tablename__ = "authz_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Policy(Base):
    """ABAC Policy definition."""
    __tablename__ = "authz_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    effect: Mapped[AuthzEffect] = mapped_column(String(10), default=AuthzEffect.ALLOW)

    # Targeted action and resource (can be patterns/wildcards)
    action_pattern: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_pattern: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # JSON-based condition logic for ABAC
    # Example: {"attr": "user.tier", "op": "eq", "value": "elite"}
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())
