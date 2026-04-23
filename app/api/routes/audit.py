# app/api/routes/audit.py
# VIT Sports Intelligence — Admin Audit Log

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.database import get_db
from app.db.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


def _require_admin(request: Request):
    admin_key = os.getenv("API_KEY", "")
    req_key = request.headers.get("x-api-key", "")
    if admin_key and req_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/logs")
async def get_audit_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List audit log entries (admin only)."""
    _require_admin(request)

    q = select(AuditLog).order_by(desc(AuditLog.timestamp))
    if action:
        q = q.where(AuditLog.action.ilike(f"%{action}%"))
    if actor:
        q = q.where(AuditLog.actor.ilike(f"%{actor}%"))
    if status:
        q = q.where(AuditLog.status == status)

    total_result = await db.execute(q)
    all_rows = total_result.scalars().all()
    total = len(all_rows)

    paged = all_rows[offset: offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "actor": log.actor,
                "resource": log.resource,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "status": log.status,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in paged
        ]
    }


@router.get("/log")
async def get_audit_log_alias(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Alias for GET /audit/log to list audit log entries."""
    return await get_audit_logs(request, limit, offset, action, actor, status, db)


class AuditLogCreate(BaseModel):
    action: str
    actor: Optional[str] = "system"
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    status: Optional[str] = "success"


@router.post("/log")
async def create_audit_log(
    body: AuditLogCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Manually write an audit log entry (admin only)."""
    _require_admin(request)

    entry = AuditLog(
        action=body.action,
        actor=body.actor or "admin",
        resource=body.resource,
        resource_id=body.resource_id,
        details=body.details,
        ip_address=request.client.host if request.client else None,
        status=body.status or "success",
    )
    db.add(entry)
    await db.commit()
    return {"success": True, "id": entry.id}


async def write_audit(
    db: AsyncSession,
    action: str,
    actor: str = "system",
    resource: str = None,
    resource_id: str = None,
    details: dict = None,
    ip: str = None,
    status: str = "success",
):
    """Helper for other routes to write audit entries."""
    entry = AuditLog(
        action=action,
        actor=actor,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=ip,
        status=status,
    )
    db.add(entry)
