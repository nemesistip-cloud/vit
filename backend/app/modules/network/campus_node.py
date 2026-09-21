"""Campus Node Registry — handles university infrastructure registration and verification."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, HttpUrl
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth.dependencies import get_current_user, get_current_admin
from app.modules.network.models import NodeActivity
from app.modules.did.engine import get_or_create_agent_identity, issue_credential
from app.core.errors import AppError
from app.services.audit import write_audit

router = APIRouter(prefix="/api/network/campus", tags=["Campus Nodes"])
logger = logging.getLogger(__name__)

# ── Schemas ───────────────────────────────────────────────────────────────

class CampusRegistrationRequest(BaseModel):
    university_name: str
    country: str
    node_type: str = "campus"
    admin_email: EmailStr
    server_specs: dict
    verification_doc_url: HttpUrl

# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/register")
async def register_campus_node(
    body: CampusRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    POST /api/network/campus/register
    Creates a pending campus node registration recorded as a NodeActivity.
    """
    # Use a deterministic node_id based on university and user
    import hashlib
    node_id = f"campus_{hashlib.sha256(f'{body.university_name}_{current_user.id}'.encode()).hexdigest()[:12]}"

    # Check if already registered (look at latest activity)
    existing_stmt = (
        select(NodeActivity)
        .where(NodeActivity.node_id == node_id)
        .order_by(desc(NodeActivity.recorded_at))
        .limit(1)
    )
    res = await db.execute(existing_stmt)
    latest_activity = res.scalar_one_or_none()

    if latest_activity and latest_activity.node_type in ["campus", "pending_campus"]:
        raise AppError("This university node is already registered or pending.", status_code=400, code="already_registered")

    registration = NodeActivity(
        node_id=node_id,
        node_name=body.university_name,
        node_type="pending_campus",
        activity_type="campus_registration_pending",
        activity_meta={
            "university_name": body.university_name,
            "country": body.country,
            "admin_email": body.admin_email,
            "server_specs": body.server_specs,
            "verification_doc_url": str(body.verification_doc_url),
            "owner_user_id": current_user.id,
            "requested_at": datetime.now(timezone.utc).isoformat()
        }
    )
    db.add(registration)
    await db.commit()

    logger.info(f"Campus node registration pending for {body.university_name} (ID: {node_id})")

    return {
        "status": "pending",
        "message": "Campus node registration submitted. An administrator will verify your credentials.",
        "node_id": node_id
    }

@router.post("/activate/{node_id}")
async def activate_campus_node(
    node_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin),
):
    """
    POST /api/network/campus/activate/{node_id} (admin only)
    Activates campus node after verification and issues DID Verifiable Credential.
    """
    # Fetch the latest registration activity to avoid MultipleResultsFound
    stmt = (
        select(NodeActivity)
        .where(NodeActivity.node_id == node_id)
        .order_by(desc(NodeActivity.recorded_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    node_record = res.scalar_one_or_none()

    if not node_record:
        raise AppError(f"Node {node_id} not found.", status_code=404, code="not_found")

    if node_record.node_type == "campus":
        return {"status": "already_active", "node_id": node_id}

    before_state = {"node_type": node_record.node_type, "activity_type": node_record.activity_type}

    # Record activation as a new activity to preserve history
    activation = NodeActivity(
        node_id=node_id,
        node_name=node_record.node_name,
        node_type="campus",
        activity_type="campus_activated",
        activity_meta={
            **(node_record.activity_meta or {}),
            "activated_by": admin.username,
            "activated_at": datetime.now(timezone.utc).isoformat()
        }
    )
    db.add(activation)

    # 2. Setup DID and Issue Credential
    try:
        identity = await get_or_create_agent_identity(node_record.node_name, db)
        await issue_credential(
            identity_id=identity.id,
            credential_type="NodeContributionCredential",
            claims={
                "node_id": node_id,
                "node_type": "campus",
                "university": node_record.node_name,
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "verified_by": admin.username
            },
            db=db
        )
    except Exception as e:
        logger.error(f"Failed to issue DID credential for node {node_id}: {e}")
        # Continue anyway, but log the error

    await db.commit()

    # 3. Write Audit Log
    await write_audit(
        db=db,
        admin_id=admin.id,
        action="campus.activate",
        target_type="campus_node",
        target_id=node_id,
        before=before_state,
        after={"node_type": "campus", "activity_type": "campus_activated"},
        request=request
    )

    logger.info(f"Campus node {node_id} activated by admin {admin.username}")

    return {
        "status": "active",
        "message": f"Campus node {node_id} has been activated successfully.",
        "node_id": node_id
    }
