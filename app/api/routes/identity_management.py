"""
Identity Management API — sessions, devices, login history, permissions.

All endpoints operate on the authenticated User (JWT). GlobalIdentity records
are looked up / created by email so the identity plugin integrates cleanly with
the existing auth system without requiring a migration.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import AuditLog, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/identity/me", tags=["Identity Management"])

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_global_identity(db: AsyncSession, user: User):
    """Fetch the GlobalIdentity for this user, creating one if absent."""
    try:
        from app.plugins.identity.models import GlobalIdentity, IdentityStatus, IdentityType
        import uuid, re

        result = await db.execute(
            select(GlobalIdentity).where(GlobalIdentity.email == user.email)
        )
        identity = result.scalar_one_or_none()
        if not identity:
            def _gid():
                raw = uuid.uuid4().hex.upper()
                return f"VIT-ID-{raw[:4]}-{raw[4:8]}"

            identity = GlobalIdentity(
                gid=_gid(),
                type=IdentityType.ADMIN if user.role == "admin" else IdentityType.INDIVIDUAL,
                status=IdentityStatus.ACTIVE,
                username=user.username,
                email=user.email,
                auth_methods=["password"],
                security_metadata={},
                profile={},
            )
            db.add(identity)
            await db.commit()
            await db.refresh(identity)
        return identity
    except Exception as exc:
        logger.error("_get_or_create_global_identity failed: %s", exc)
        return None

# ── Sessions ──────────────────────────────────────────────────────────────────

class SessionOut(BaseModel):
    id: int
    session_token_preview: str
    device_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_active: bool
    created_at: datetime
    last_activity: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


@router.get("/sessions", response_model=List[SessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active sessions for the current user."""
    identity = await _get_or_create_global_identity(db, current_user)
    if not identity:
        return []

    try:
        from app.plugins.identity.models import IdentitySession
        result = await db.execute(
            select(IdentitySession)
            .where(IdentitySession.identity_id == identity.id)
            .order_by(desc(IdentitySession.last_activity))
        )
        sessions = result.scalars().all()
        return [
            SessionOut(
                id=s.id,
                session_token_preview=s.session_token[:8] + "…",
                device_id=s.device_id,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                is_active=s.is_active and s.expires_at > datetime.now(timezone.utc),
                created_at=s.created_at,
                last_activity=s.last_activity,
                expires_at=s.expires_at,
            )
            for s in sessions
        ]
    except Exception as exc:
        logger.error("list_sessions: %s", exc)
        return []


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session."""
    identity = await _get_or_create_global_identity(db, current_user)
    if not identity:
        raise HTTPException(404, "Identity not found")

    try:
        from app.plugins.identity.models import IdentitySession
        result = await db.execute(
            select(IdentitySession).where(
                IdentitySession.id == session_id,
                IdentitySession.identity_id == identity.id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(404, "Session not found")
        session.is_active = False
        await db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("revoke_session: %s", exc)
        raise HTTPException(500, "Could not revoke session")


@router.delete("/sessions", status_code=204)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all sessions for the current user (force re-login everywhere)."""
    identity = await _get_or_create_global_identity(db, current_user)
    if not identity:
        return

    try:
        from app.plugins.identity.models import IdentitySession
        result = await db.execute(
            select(IdentitySession).where(IdentitySession.identity_id == identity.id)
        )
        for s in result.scalars().all():
            s.is_active = False
        await db.commit()
    except Exception as exc:
        logger.error("revoke_all_sessions: %s", exc)


# ── Devices ───────────────────────────────────────────────────────────────────

class DeviceOut(BaseModel):
    id: int
    device_id: str
    platform: Optional[str]
    browser: Optional[str]
    is_trusted: bool
    risk_score: int
    last_ip: Optional[str]
    last_active: datetime

    class Config:
        from_attributes = True


@router.get("/devices", response_model=List[DeviceOut])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all registered devices for the current user."""
    identity = await _get_or_create_global_identity(db, current_user)
    if not identity:
        return []

    try:
        from app.plugins.identity.models import TrustedDevice
        result = await db.execute(
            select(TrustedDevice)
            .where(TrustedDevice.identity_id == identity.id)
            .order_by(desc(TrustedDevice.last_active))
        )
        return list(result.scalars().all())
    except Exception as exc:
        logger.error("list_devices: %s", exc)
        return []


@router.post("/devices/{device_id}/trust", status_code=200)
async def trust_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a device as trusted."""
    identity = await _get_or_create_global_identity(db, current_user)
    if not identity:
        raise HTTPException(404, "Identity not found")

    try:
        from app.plugins.identity.services.device_trust_manager import DeviceTrustManager
        mgr = DeviceTrustManager(db)
        await mgr.trust_device(identity.id, device_id)
        return {"status": "trusted", "device_id": device_id}
    except Exception as exc:
        logger.error("trust_device: %s", exc)
        raise HTTPException(500, "Could not trust device")


@router.delete("/devices/{device_id}", status_code=204)
async def remove_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a registered device."""
    identity = await _get_or_create_global_identity(db, current_user)
    if not identity:
        raise HTTPException(404, "Identity not found")

    try:
        from app.plugins.identity.models import TrustedDevice
        result = await db.execute(
            select(TrustedDevice).where(
                TrustedDevice.identity_id == identity.id,
                TrustedDevice.device_id == device_id,
            )
        )
        device = result.scalar_one_or_none()
        if device:
            await db.delete(device)
            await db.commit()
    except Exception as exc:
        logger.error("remove_device: %s", exc)


# ── Login History ─────────────────────────────────────────────────────────────

class LoginHistoryEntry(BaseModel):
    id: int
    action: str
    ip_address: Optional[str]
    details: Dict[str, Any]
    created_at: datetime


@router.get("/login-history", response_model=List[LoginHistoryEntry])
async def login_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the last N login events for the current user."""
    try:
        result = await db.execute(
            select(AuditLog)
            .where(
                AuditLog.actor == current_user.email,
                AuditLog.action.in_(["login", "login_success", "login_failed", "logout",
                                     "password_reset", "2fa_enabled", "2fa_disabled",
                                     "email_verified"]),
            )
            .order_by(desc(AuditLog.created_at))
            .limit(min(limit, 200))
        )
        rows = result.scalars().all()
        return [
            LoginHistoryEntry(
                id=r.id,
                action=r.action,
                ip_address=r.details.get("ip") if isinstance(r.details, dict) else None,
                details=r.details if isinstance(r.details, dict) else {},
                created_at=r.created_at,
            )
            for r in rows
        ]
    except Exception as exc:
        logger.error("login_history: %s", exc)
        return []


# ── Permissions ───────────────────────────────────────────────────────────────

class PermissionOut(BaseModel):
    slug: str
    description: Optional[str]
    via_role: str


@router.get("/permissions", response_model=List[PermissionOut])
async def list_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all permissions the current user holds (via their roles)."""
    try:
        from app.modules.authz.models import user_roles, Role, Permission, role_permissions
        from sqlalchemy import join, text

        # Get roles assigned to this user
        roles_result = await db.execute(
            select(Role)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == current_user.id)
        )
        roles = roles_result.scalars().all()

        perms: List[PermissionOut] = []
        seen: set[str] = set()
        for role in roles:
            perms_result = await db.execute(
                select(Permission)
                .join(role_permissions, Permission.id == role_permissions.c.permission_id)
                .where(role_permissions.c.role_id == role.id)
            )
            for perm in perms_result.scalars().all():
                if perm.slug not in seen:
                    seen.add(perm.slug)
                    perms.append(PermissionOut(
                        slug=perm.slug,
                        description=perm.description,
                        via_role=role.name,
                    ))

        # Always include built-in role from user.role
        builtin = current_user.role or "viewer"
        if f"builtin:{builtin}" not in seen:
            seen.add(f"builtin:{builtin}")
            perms.insert(0, PermissionOut(
                slug=f"builtin:{builtin}",
                description=f"Built-in role: {builtin}",
                via_role=builtin,
            ))

        return perms
    except Exception as exc:
        logger.error("list_permissions: %s", exc)
        # Graceful fallback
        return [PermissionOut(
            slug=f"builtin:{current_user.role or 'viewer'}",
            description=f"Built-in role: {current_user.role or 'viewer'}",
            via_role=current_user.role or "viewer",
        )]


# ── Security overview ─────────────────────────────────────────────────────────

@router.get("/security-overview")
async def security_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Single endpoint for the security dashboard card."""
    identity = await _get_or_create_global_identity(db, current_user)

    active_sessions = 0
    trusted_devices = 0
    total_devices = 0

    if identity:
        try:
            from app.plugins.identity.models import IdentitySession, TrustedDevice
            now = datetime.now(timezone.utc)

            s_result = await db.execute(
                select(IdentitySession).where(
                    IdentitySession.identity_id == identity.id,
                    IdentitySession.is_active == True,
                    IdentitySession.expires_at > now,
                )
            )
            active_sessions = len(s_result.scalars().all())

            d_result = await db.execute(
                select(TrustedDevice).where(TrustedDevice.identity_id == identity.id)
            )
            all_devices = d_result.scalars().all()
            total_devices = len(all_devices)
            trusted_devices = sum(1 for d in all_devices if d.is_trusted)
        except Exception:
            pass

    return {
        "mfa_enabled": bool(getattr(current_user, "totp_enabled", False)),
        "wallet_linked": bool(getattr(current_user, "wallet_address", None)),
        "email_verified": bool(getattr(current_user, "is_verified", True)),
        "active_sessions": active_sessions,
        "trusted_devices": trusted_devices,
        "total_devices": total_devices,
        "role": current_user.role,
        "subscription_tier": getattr(current_user, "subscription_tier", "viewer"),
        "account_age_days": (
            datetime.now(timezone.utc) - current_user.created_at.replace(tzinfo=timezone.utc)
        ).days if current_user.created_at else 0,
    }
