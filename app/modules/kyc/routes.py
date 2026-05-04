"""KYC API routes — fully offline verification, no external API keys.

POST /api/kyc/submit              — submit KYC (user)
GET  /api/kyc/status              — get caller's KYC status
GET  /api/kyc/admin/queue         — admin: pending/manual-review submissions
POST /api/kyc/admin/{id}/approve  — admin: manually approve a submission
POST /api/kyc/admin/{id}/reject   — admin: manually reject a submission
GET  /api/kyc/admin/{id}/audit    — admin: audit trail for a submission
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.database import get_db
from app.modules.kyc.models import (
    KYCAuditEvent, KYCStatus, KYCSubmission,
)
from app.modules.kyc.service import verify_offline
from app.modules.kyc.smile_identity import verify_with_smile_identity

router = APIRouter(prefix="/api/kyc", tags=["KYC"])
logger = logging.getLogger(__name__)

KYC_VALIDITY_DAYS = 365 * 2   # approved KYC is valid for 2 years


# ── Schemas ───────────────────────────────────────────────────────────────────

class KYCSubmitRequest(BaseModel):
    full_name:       str
    date_of_birth:   str        # YYYY-MM-DD
    nationality:     str
    document_type:   str        # national_id | passport | drivers_license | ...
    document_number: str
    address:         Optional[str] = None
    selfie_data:     Optional[dict] = None  # {thumbnail: base64, captured_at: ISO}

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("full_name is required")
        return v

    @field_validator("document_number")
    @classmethod
    def doc_num_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("document_number is required")
        return v


class AdminReviewRequest(BaseModel):
    note: Optional[str] = None


class AdminRejectRequest(BaseModel):
    reason: str
    note:   Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _write_audit(
    db: AsyncSession,
    submission_id: int,
    user_id: int,
    event_type: str,
    from_status: Optional[str],
    to_status: str,
    actor_id: Optional[int] = None,
    note: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    event = KYCAuditEvent(
        submission_id = submission_id,
        user_id       = user_id,
        actor_id      = actor_id,
        event_type    = event_type,
        from_status   = from_status,
        to_status     = to_status,
        note          = note,
        event_data    = metadata or {},
    )
    db.add(event)


async def _sync_user_kyc(db: AsyncSession, user_id: int, status: str, verified: bool):
    """Keep legacy kyc_status / kyc_verified on User model in sync."""
    from app.db.models import User
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if user:
        if hasattr(user, "kyc_status"):
            user.kyc_status = status
        if hasattr(user, "kyc_submitted_at") and status == "pending":
            user.kyc_submitted_at = datetime.now(timezone.utc)

    from app.modules.wallet.models import Wallet
    res_w = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = res_w.scalar_one_or_none()
    if wallet and hasattr(wallet, "kyc_verified"):
        wallet.kyc_verified = verified


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/submit")
async def submit_kyc(
    body: KYCSubmitRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit KYC data for offline rule-based verification."""
    # Check for active submission
    res = await db.execute(
        select(KYCSubmission)
        .where(KYCSubmission.user_id == current_user.id)
        .where(KYCSubmission.status.in_([
            KYCStatus.PENDING, KYCStatus.AUTO_APPROVED,
            KYCStatus.MANUAL_REVIEW, KYCStatus.APPROVED,
        ]))
        .order_by(KYCSubmission.submitted_at.desc())
        .limit(1)
    )
    active = res.scalar_one_or_none()

    if active and active.status == KYCStatus.APPROVED:
        return {
            "status":    "approved",
            "message":   "Your identity is already verified.",
            "risk_score": active.risk_score,
        }

    if active and active.status in (KYCStatus.PENDING, KYCStatus.AUTO_APPROVED, KYCStatus.MANUAL_REVIEW):
        return {
            "status":  active.status.value,
            "message": "A KYC submission is already under review. Please wait for it to complete.",
        }

    # Build verification payload
    payload = {
        "full_name":       body.full_name,
        "date_of_birth":   body.date_of_birth,
        "document_type":   body.document_type,
        "document_number": body.document_number,
        "nationality":     body.nationality,
    }

    # Try Smile Identity live verification first; fall back to offline engine
    result = await verify_with_smile_identity(payload)
    if result is None:
        result = verify_offline(payload)
    else:
        logger.info("[kyc] Smile Identity verification used for user %d", current_user.id)

    now    = datetime.now(timezone.utc)
    status: KYCStatus = result["status"]

    submission = KYCSubmission(
        user_id         = current_user.id,
        full_name       = body.full_name,
        date_of_birth   = body.date_of_birth,
        nationality     = body.nationality,
        document_type   = body.document_type,
        document_number = body.document_number,
        address         = body.address,
        selfie_data     = body.selfie_data,
        status          = status,
        risk_score      = result["risk_score"],
        risk_level      = result["risk_level"],
        rule_checks     = result["rule_checks"],
        risk_flags      = result["risk_flags"],
    )

    if status == KYCStatus.AUTO_APPROVED:
        submission.approved_at = now
        submission.expires_at  = now + timedelta(days=KYC_VALIDITY_DAYS)

    db.add(submission)
    await db.flush()

    await _write_audit(
        db, submission.id, current_user.id,
        "submitted", None, status.value,
        note=f"risk_score={result['risk_score']}",
        metadata={"rule_checks": result["rule_checks"]},
    )

    # Sync legacy fields
    verified = status == KYCStatus.AUTO_APPROVED
    await _sync_user_kyc(db, current_user.id, status.value, verified)

    # Issue VC if auto-approved
    if status == KYCStatus.AUTO_APPROVED:
        try:
            from app.modules.did.engine import get_or_create_user_identity, issue_credential
            identity = await get_or_create_user_identity(
                current_user.id,
                getattr(current_user, "username", "user"),
                db,
            )
            await issue_credential(
                identity.id, "KYCCredential",
                {
                    "full_name":     body.full_name,
                    "nationality":   body.nationality,
                    "document_type": body.document_type,
                    "verified_at":   now.isoformat(),
                    "method":        "offline_rule_engine",
                },
                db,
                valid_days=KYC_VALIDITY_DAYS,
            )
        except Exception as exc:
            logger.warning("[kyc] VC issuance failed user=%d: %s", current_user.id, exc)

    # Refresh System ID tier
    try:
        from app.modules.identity.engine import refresh_system_id
        await refresh_system_id(current_user.id, current_user, db)
    except Exception as exc:
        logger.debug("[kyc] system id refresh failed: %s", exc)

    await db.commit()

    messages = {
        KYCStatus.AUTO_APPROVED:  "Your identity has been verified successfully.",
        KYCStatus.MANUAL_REVIEW:  "Your submission has been queued for manual review. You will be notified once processed.",
        KYCStatus.REJECTED:       "Your submission could not be verified. Please check the details and resubmit.",
    }

    return {
        "status":     status.value,
        "risk_score": result["risk_score"],
        "risk_flags": result["risk_flags"],
        "message":    messages.get(status, "Submission received."),
    }


@router.get("/status")
async def get_kyc_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the caller's latest KYC submission status."""
    res = await db.execute(
        select(KYCSubmission)
        .where(KYCSubmission.user_id == current_user.id)
        .order_by(KYCSubmission.submitted_at.desc())
        .limit(1)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        return {"status": "none", "message": "No KYC submission on record."}

    return {
        "id":           sub.id,
        "status":       sub.status.value,
        "risk_score":   sub.risk_score,
        "risk_level":   sub.risk_level.value,
        "risk_flags":   sub.risk_flags,
        "submitted_at": sub.submitted_at.isoformat(),
        "reviewed_at":  sub.reviewed_at.isoformat() if sub.reviewed_at else None,
        "approved_at":  sub.approved_at.isoformat() if sub.approved_at else None,
        "expires_at":   sub.expires_at.isoformat() if sub.expires_at else None,
        "rule_checks":  sub.rule_checks,
        "review_note":  sub.review_note,
        "rejection_reason": sub.rejection_reason,
    }


@router.get("/admin/queue")
async def admin_queue(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: list KYC submissions by status."""
    statuses = [KYCStatus.PENDING, KYCStatus.MANUAL_REVIEW]
    if status:
        try:
            statuses = [KYCStatus(status)]
        except ValueError:
            raise HTTPException(400, f"Invalid status '{status}'")

    q = (
        select(KYCSubmission)
        .where(KYCSubmission.status.in_(statuses))
        .order_by(KYCSubmission.submitted_at.asc())
        .limit(limit)
        .offset(offset)
    )
    res  = await db.execute(q)
    rows = res.scalars().all()

    return {
        "items": [
            {
                "id":             r.id,
                "user_id":        r.user_id,
                "full_name":      r.full_name,
                "nationality":    r.nationality,
                "document_type":  r.document_type,
                "status":         r.status.value,
                "risk_score":     r.risk_score,
                "risk_level":     r.risk_level.value,
                "risk_flags":     r.risk_flags,
                "submitted_at":   r.submitted_at.isoformat(),
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.post("/admin/{submission_id}/approve")
async def admin_approve(
    submission_id: int,
    body: AdminReviewRequest = AdminReviewRequest(),
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Admin: manually approve a KYC submission."""
    res = await db.execute(select(KYCSubmission).where(KYCSubmission.id == submission_id))
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.status == KYCStatus.APPROVED:
        return {"message": "Already approved"}

    prev      = sub.status.value
    now       = datetime.now(timezone.utc)
    sub.status      = KYCStatus.APPROVED
    sub.approved_at = now
    sub.expires_at  = now + timedelta(days=KYC_VALIDITY_DAYS)
    sub.reviewed_by = admin.id
    sub.reviewed_at = now
    sub.review_note = body.note

    await _write_audit(db, sub.id, sub.user_id, "approved", prev, "approved", actor_id=admin.id, note=body.note)
    await _sync_user_kyc(db, sub.user_id, "approved", True)

    # Issue VC
    try:
        from app.modules.did.engine import get_or_create_user_identity, issue_credential
        from app.db.models import User
        user_res = await db.execute(select(User).where(User.id == sub.user_id))
        user = user_res.scalar_one_or_none()
        if user:
            identity = await get_or_create_user_identity(sub.user_id, user.username, db)
            await issue_credential(
                identity.id, "KYCCredential",
                {"full_name": sub.full_name, "method": "admin_manual", "approved_by": admin.id},
                db, valid_days=KYC_VALIDITY_DAYS,
            )
    except Exception as exc:
        logger.warning("[kyc] VC issuance failed on admin approve: %s", exc)

    await db.commit()
    return {"message": "Submission approved", "submission_id": submission_id}


@router.post("/admin/{submission_id}/reject")
async def admin_reject(
    submission_id: int,
    body: AdminRejectRequest,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Admin: manually reject a KYC submission."""
    res = await db.execute(select(KYCSubmission).where(KYCSubmission.id == submission_id))
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Submission not found")

    prev = sub.status.value
    now  = datetime.now(timezone.utc)
    sub.status           = KYCStatus.REJECTED
    sub.reviewed_by      = admin.id
    sub.reviewed_at      = now
    sub.review_note      = body.note
    sub.rejection_reason = body.reason

    await _write_audit(db, sub.id, sub.user_id, "rejected", prev, "rejected", actor_id=admin.id, note=body.note)
    await _sync_user_kyc(db, sub.user_id, "rejected", False)

    await db.commit()
    return {"message": "Submission rejected", "submission_id": submission_id}


@router.get("/admin/{submission_id}/audit")
async def admin_audit_trail(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: full audit trail for a KYC submission."""
    res = await db.execute(
        select(KYCAuditEvent)
        .where(KYCAuditEvent.submission_id == submission_id)
        .order_by(KYCAuditEvent.created_at.asc())
    )
    events = res.scalars().all()
    return {
        "submission_id": submission_id,
        "events": [
            {
                "id":           e.id,
                "event_type":   e.event_type,
                "from_status":  e.from_status,
                "to_status":    e.to_status,
                "actor_id":     e.actor_id,
                "note":         e.note,
                "metadata":     e.metadata,
                "created_at":   e.created_at.isoformat(),
            }
            for e in events
        ],
    }
