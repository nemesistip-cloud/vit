"""System Identity API routes.

GET  /api/identity/me          — get or create caller's System ID card
GET  /api/identity/{sid}       — resolve any System ID (public)
POST /api/identity/refresh     — force-refresh tier/badges (e.g. after KYC approval)
GET  /api/identity/admin/list  — admin: list all system IDs
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.database import get_db
from app.modules.identity.engine import (
    build_id_card_data,
    get_or_create_system_id,
    get_system_id_by_sid,
    refresh_system_id,
)
from app.modules.identity.models import SystemID
from app.schemas.schemas import StudentIdentityUpdate

router = APIRouter(prefix="/api/identity", tags=["System Identity"])
logger = logging.getLogger(__name__)


class OrganizationCreate(BaseModel):
    name: str
    slug: str


class OrganizationOut(BaseModel):
    id: int
    name: str
    slug: str
    owner_id: Optional[int] = None
    created_at: Optional[str] = None


class WorkspaceSettingUpsert(BaseModel):
    key: str = Field(min_length=1)
    value: dict | list | str | int | float | bool | None = None


class WorkspaceSettingOut(BaseModel):
    id: int
    key: str
    value: dict | list | str | int | float | bool | None = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TeamCreate(BaseModel):
    organization_id: int
    name: str
    slug: str


class TeamOut(BaseModel):
    id: int
    organization_id: int
    name: str
    slug: str
    created_at: Optional[str] = None


class RoleCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class RoleOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    permissions: list[str] = Field(default_factory=list)


class SessionOut(BaseModel):
    id: int
    user_id: int
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    active: bool


class DeviceOut(BaseModel):
    id: int
    device_id: str
    platform: Optional[str] = None
    browser: Optional[str] = None
    trusted: bool
    last_active: Optional[str] = None


class APIKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None


class APIKeyOut(BaseModel):
    id: int
    name: str
    prefix: str
    active: bool
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    raw_value: Optional[str] = None


@router.get("/me")
async def get_my_identity(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the caller's System ID card data, creating one if it doesn't exist."""
    sys_id = await get_or_create_system_id(current_user.id, current_user, db)
    await db.commit()
    return build_id_card_data(sys_id, current_user)


@router.post("/refresh")
async def refresh_my_identity(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-evaluate tier and badges from current user state."""
    sys_id = await refresh_system_id(current_user.id, current_user, db)
    await db.commit()
    if not sys_id:
        raise HTTPException(404, "System ID not found — call GET /api/identity/me first")
    return build_id_card_data(sys_id, current_user)


@router.get("/admin/list")
async def admin_list_identities(
    tier: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: paginated list of all system IDs."""
    q = select(SystemID)
    if tier:
        q = q.where(SystemID.tier == tier)
    q = q.order_by(SystemID.issued_at.desc()).limit(limit).offset(offset)
    res  = await db.execute(q)
    rows = res.scalars().all()
    return {
        "items": [
            {
                "sid":          r.sid,
                "user_id":      r.user_id,
                "display_name": r.display_name,
                "tier":         r.tier.value if hasattr(r.tier, "value") else r.tier,
                "did":          r.did,
                "badges":       r.badges,
                "issued_at":    r.issued_at.isoformat(),
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/organizations", tags=["Identity"])
async def list_organizations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    from app.modules.identity.models import Organization

    result = await db.execute(
        select(Organization).order_by(Organization.created_at.desc()).limit(limit).offset(offset)
    )
    rows = result.scalars().all()
    return {
        "items": [
            OrganizationOut(
                id=row.id,
                name=row.name,
                slug=row.slug,
                owner_id=row.owner_id,
                created_at=row.created_at.isoformat() if row.created_at else None,
            ).model_dump()
            for row in rows
        ],
        "count": len(rows),
    }


@router.get("/{sid}")
async def resolve_identity(sid: str, db: AsyncSession = Depends(get_db)):
    """Public: resolve any System ID to its public card data."""
    sys_id = await get_system_id_by_sid(sid.upper(), db)
    if not sys_id:
        raise HTTPException(404, f"System ID not found: {sid}")
    if sys_id.revoked:
        raise HTTPException(410, f"System ID {sid} has been revoked")

    from app.db.models import User
    res  = await db.execute(select(User).where(User.id == sys_id.user_id))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(404, "Associated user account not found or inactive")

    return {
        "sid":             sys_id.sid,
        "display_name":    sys_id.display_name,
        "tier":            sys_id.tier.value if hasattr(sys_id.tier, "value") else sys_id.tier,
        "avatar_initials": sys_id.avatar_initials,
        "did":             sys_id.did,
        "badges":          sys_id.badges,
        "issued_at":       sys_id.issued_at.isoformat(),
    }

@router.patch("/profile")
async def update_student_profile(
    data: StudentIdentityUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the student identity fields for the current user."""
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)

    await db.commit()
    await db.refresh(current_user)

    await refresh_system_id(current_user.id, current_user, db)
    await db.commit()

    return {"status": "success", "message": "Student profile updated"}


@router.post("/organizations", status_code=status.HTTP_201_CREATED, response_model=OrganizationOut)
async def create_organization(
    payload: OrganizationCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.identity.models import Organization

    existing = await db.execute(select(Organization).where(Organization.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Organization slug already exists")

    org = Organization(name=payload.name, slug=payload.slug, owner_id=current_user.id)
    db.add(org)
    await db.flush()
    await db.commit()
    await db.refresh(org)
    return OrganizationOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        owner_id=org.owner_id,
        created_at=org.created_at.isoformat() if org.created_at else None,
    )


@router.put("/organizations/{organization_id}", response_model=OrganizationOut)
async def update_organization(
    organization_id: int,
    payload: OrganizationCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.identity.models import Organization

    org = await db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    if org.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Only owners or admins may update organizations")
    org.name = payload.name
    org.slug = payload.slug
    await db.commit()
    await db.refresh(org)
    return OrganizationOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        owner_id=org.owner_id,
        created_at=org.created_at.isoformat() if org.created_at else None,
    )


@router.delete("/organizations/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.identity.models import Organization

    org = await db.get(Organization, organization_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    if org.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Only owners or admins may delete organizations")
    await db.delete(org)
    await db.commit()


@router.post("/teams", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.identity.models import Organization, IdentityTeam

    org = await db.get(Organization, payload.organization_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    if org.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(403, "Only owners or admins may create teams")

    existing = await db.execute(select(IdentityTeam).where(IdentityTeam.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Team slug already exists")

    team = IdentityTeam(name=payload.name, slug=payload.slug, organization_id=payload.organization_id)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return TeamOut(id=team.id, organization_id=team.organization_id, name=team.name, slug=team.slug, created_at=team.created_at.isoformat() if team.created_at else None)


@router.get("/teams", response_model=list[TeamOut])
async def list_teams(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.identity.models import IdentityTeam

    result = await db.execute(select(IdentityTeam).order_by(IdentityTeam.created_at.desc()))
    rows = result.scalars().all()
    return [TeamOut(id=row.id, organization_id=row.organization_id, name=row.name, slug=row.slug, created_at=row.created_at.isoformat() if row.created_at else None) for row in rows]


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.authz.models import Permission, Role, role_permissions

    if current_user.role != "admin":
        raise HTTPException(403, "Only admins may create roles")

    role = Role(name=payload.name, slug=payload.slug, description=payload.description, is_builtin=False)
    db.add(role)
    await db.flush()

    for perm_slug in payload.permissions:
        perm = await db.execute(select(Permission).where(Permission.slug == perm_slug))
        perm_row = perm.scalar_one_or_none()
        if perm_row is None:
            perm_row = Permission(slug=perm_slug, description=f"Permission {perm_slug}")
            db.add(perm_row)
            await db.flush()
        role.permissions.append(perm_row)

    await db.commit()
    await db.refresh(role)
    return RoleOut(id=role.id, name=role.name, slug=role.slug, description=role.description, permissions=[perm.slug for perm in role.permissions])


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.authz.models import Role

    result = await db.execute(select(Role).order_by(Role.created_at.desc()))
    rows = result.scalars().all()
    return [RoleOut(id=row.id, name=row.name, slug=row.slug, description=row.description, permissions=[perm.slug for perm in row.permissions]) for row in rows]


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.plugins.identity.models import IdentitySession

    result = await db.execute(select(IdentitySession).where(IdentitySession.identity_id == current_user.id).order_by(IdentitySession.created_at.desc()))
    rows = result.scalars().all()
    return [SessionOut(id=row.id, user_id=current_user.id, created_at=row.created_at.isoformat() if row.created_at else None, expires_at=row.expires_at.isoformat() if row.expires_at else None, active=row.is_active and row.expires_at > datetime.now(timezone.utc)) for row in rows]


@router.post("/sessions/{session_id}/revoke", response_model=dict[str, bool])
async def revoke_session(
    session_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.plugins.identity.models import IdentitySession

    session = await db.get(IdentitySession, session_id)
    if not session or session.identity_id != current_user.id:
        raise HTTPException(404, "Session not found")
    session.is_active = False
    await db.commit()
    return {"revoked": True}


@router.get("/devices", response_model=list[DeviceOut])
async def list_devices(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.plugins.identity.models import TrustedDevice

    result = await db.execute(select(TrustedDevice).where(TrustedDevice.identity_id == current_user.id).order_by(TrustedDevice.last_active.desc()))
    rows = result.scalars().all()
    return [DeviceOut(id=row.id, device_id=row.device_id, platform=row.platform, browser=row.browser, trusted=row.is_trusted, last_active=row.last_active.isoformat() if row.last_active else None) for row in rows]


@router.post("/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
async def register_device(
    device_id: str,
    platform: Optional[str] = None,
    browser: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.plugins.identity.models import TrustedDevice

    existing = await db.execute(select(TrustedDevice).where(TrustedDevice.identity_id == current_user.id, TrustedDevice.device_id == device_id))
    device = existing.scalar_one_or_none()
    if not device:
        device = TrustedDevice(identity_id=current_user.id, device_id=device_id, platform=platform, browser=browser, is_trusted=False)
        db.add(device)
    else:
        device.platform = platform
        device.browser = browser
        device.last_active = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(device)
    return DeviceOut(id=device.id, device_id=device.device_id, platform=device.platform, browser=device.browser, trusted=device.is_trusted, last_active=device.last_active.isoformat() if device.last_active else None)


@router.post("/devices/{device_id}/trust", response_model=DeviceOut)
async def trust_device(
    device_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.plugins.identity.models import TrustedDevice

    device = await db.execute(select(TrustedDevice).where(TrustedDevice.identity_id == current_user.id, TrustedDevice.device_id == device_id))
    row = device.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Device not found")
    row.is_trusted = True
    row.last_active = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)
    return DeviceOut(id=row.id, device_id=row.device_id, platform=row.platform, browser=row.browser, trusted=row.is_trusted, last_active=row.last_active.isoformat() if row.last_active else None)


@router.post("/api-keys", response_model=APIKeyOut, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.developer.models import APIKey
    from app.modules.developer.service import _hash_key
    import secrets

    raw = "vit_" + secrets.token_urlsafe(36)
    prefix = raw[:12]
    key = APIKey(
        user_id=current_user.id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=_hash_key(raw),
        key_plain=raw,
        plan="free",
        rate_limit_rpm=60,
        rate_limit_rpd=1000,
        is_active=True,
        expires_at=payload.expires_at,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return APIKeyOut(id=key.id, name=key.name, prefix=key.key_prefix, active=bool(key.is_active), created_at=key.created_at.isoformat() if key.created_at else None, expires_at=key.expires_at.isoformat() if key.expires_at else None, last_used_at=key.last_used_at.isoformat() if key.last_used_at else None, raw_value=raw)


@router.get("/api-keys", response_model=list[APIKeyOut])
async def list_api_keys(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.developer.models import APIKey

    result = await db.execute(select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc()))
    rows = result.scalars().all()
    return [APIKeyOut(id=row.id, name=row.name, prefix=row.key_prefix, active=bool(row.is_active), created_at=row.created_at.isoformat() if row.created_at else None, expires_at=row.expires_at.isoformat() if row.expires_at else None, last_used_at=row.last_used_at.isoformat() if row.last_used_at else None) for row in rows]


@router.post("/api-keys/{api_key_id}/disable", response_model=APIKeyOut)
async def disable_api_key(
    api_key_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.developer.models import APIKey

    key = await db.get(APIKey, api_key_id)
    if not key or key.user_id != current_user.id:
        raise HTTPException(404, "API key not found")
    key.is_active = False
    await db.commit()
    await db.refresh(key)
    return APIKeyOut(id=key.id, name=key.name, prefix=key.key_prefix, active=bool(key.is_active), created_at=key.created_at.isoformat() if key.created_at else None, expires_at=key.expires_at.isoformat() if key.expires_at else None, last_used_at=key.last_used_at.isoformat() if key.last_used_at else None)


@router.delete("/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    api_key_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.developer.models import APIKey

    key = await db.get(APIKey, api_key_id)
    if not key or key.user_id != current_user.id:
        raise HTTPException(404, "API key not found")
    await db.delete(key)
    await db.commit()


@router.post("/me/workspace", response_model=WorkspaceSettingOut)
async def upsert_workspace_setting(
    payload: WorkspaceSettingUpsert,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.identity.models import WorkspaceSetting

    existing = await db.execute(
        select(WorkspaceSetting).where(
            WorkspaceSetting.user_id == current_user.id,
            WorkspaceSetting.key == payload.key,
        )
    )
    row = existing.scalar_one_or_none()
    if not row:
        row = WorkspaceSetting(user_id=current_user.id, key=payload.key, value=payload.value)
        db.add(row)
    else:
        row.value = payload.value
    await db.flush()
    await db.commit()
    await db.refresh(row)
    return WorkspaceSettingOut(
        id=row.id,
        key=row.key,
        value=row.value,
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.get("/me/workspace")
async def list_workspace_settings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.modules.identity.models import WorkspaceSetting

    result = await db.execute(
        select(WorkspaceSetting)
        .where(WorkspaceSetting.user_id == current_user.id)
        .order_by(WorkspaceSetting.updated_at.desc())
    )
    rows = result.scalars().all()
    return {
        "items": [
            WorkspaceSettingOut(
                id=row.id,
                key=row.key,
                value=row.value,
                created_at=row.created_at.isoformat() if row.created_at else None,
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            ).model_dump()
            for row in rows
        ],
        "count": len(rows),
    }
