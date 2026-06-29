"""Android Node Registry — lightweight mobile node management."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.modules.network.models import NodeActivity
from app.core.errors import AppError

router = APIRouter(prefix="/api/network/android", tags=["Android Nodes"])
logger = logging.getLogger(__name__)

# ── Schemas ───────────────────────────────────────────────────────────────

class AndroidRegistrationRequest(BaseModel):
    device_model: str
    os_version: str
    max_storage_gb: float = 5.0
    # Nigeria-specific data cost sensitivity constraints
    only_when_charging: bool = True
    only_on_wifi: bool = True
    max_bandwidth_mb_per_day: int = 100

class AndroidHeartbeatRequest(BaseModel):
    node_id: str
    is_charging: bool
    is_on_wifi: bool
    storage_used_gb: float

# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/register")
async def register_android_node(
    body: AndroidRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    POST /api/network/android/register
    Registers a new Android node for the current user.
    """
    import hashlib
    node_id = f"android_{hashlib.sha256(f'{body.device_model}_{current_user.id}_{datetime.now().timestamp()}'.encode()).hexdigest()[:12]}"

    # Record registration
    registration = NodeActivity(
        node_id=node_id,
        node_name=body.device_model,
        node_type="android",
        activity_type="android_registration",
        contribution_score=0.0,
        activity_meta={
            "owner_user_id": current_user.id,
            "os_version": body.os_version,
            "constraints": {
                "max_storage_gb": body.max_storage_gb,
                "only_when_charging": body.only_when_charging,
                "only_on_wifi": body.only_on_wifi,
                "max_bandwidth_mb_per_day": body.max_bandwidth_mb_per_day
            },
            "registered_at": datetime.now(timezone.utc).isoformat()
        }
    )
    db.add(registration)
    await db.commit()

    logger.info(f"Android node {node_id} registered for user {current_user.id}")

    return {
        "status": "success",
        "node_id": node_id,
        "node_type": "android",
        "reward_multiplier": 0.5
    }

@router.post("/heartbeat")
async def android_heartbeat(
    body: AndroidHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    POST /api/network/android/heartbeat
    Periodic ping from mobile node to update status.
    """
    # 1. Verify node exists and belongs to user
    stmt = (
        select(NodeActivity)
        .where(NodeActivity.node_id == body.node_id)
        .order_by(desc(NodeActivity.recorded_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    node_record = res.scalar_one_or_none()

    if not node_record:
        raise AppError(f"Node {body.node_id} not found", status_code=404, code="not_found")

    owner_id = node_record.activity_meta.get("owner_user_id") if node_record.activity_meta else None
    if owner_id != current_user.id:
         raise AppError("Unauthorized access to node", status_code=403, code="unauthorized")

    # 2. Record Heartbeat
    heartbeat = NodeActivity(
        node_id=body.node_id,
        node_name=node_record.node_name,
        node_type="android",
        activity_type="android_heartbeat",
        contribution_score=0.1, # Small uptime bonus
        activity_meta={
            "charge_status": "charging" if body.is_charging else "discharging",
            "wifi_status": "connected" if body.is_on_wifi else "disconnected",
            "storage_used_gb": body.storage_used_gb,
            "last_seen": datetime.now(timezone.utc).isoformat()
        }
    )
    db.add(heartbeat)
    await db.commit()

    return {
        "status": "online",
        "node_id": body.node_id,
        "tasks_available": body.is_charging and body.is_on_wifi
    }
