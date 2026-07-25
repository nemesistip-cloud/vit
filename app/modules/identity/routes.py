"""System Identity API routes.

GET  /api/identity/me          — get or create caller's System ID card
GET  /api/identity/{sid}       — resolve any System ID (public)
POST /api/identity/refresh     — force-refresh tier/badges (e.g. after KYC approval)
GET  /api/identity/admin/list  — admin: list all system IDs
"""
from __future__ import annotations

import logging
from typing import Optional

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


@router.get("/organizations")
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
