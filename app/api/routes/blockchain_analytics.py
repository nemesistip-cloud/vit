"""app/api/routes/blockchain_analytics.py — Blockchain analytics & slash management routes.

GET  /api/blockchain/analytics/network      — full network stats
GET  /api/blockchain/analytics/leaderboard  — validator leaderboard
GET  /api/blockchain/analytics/economics    — token economics snapshot
GET  /api/blockchain/analytics/slash-history — slash event audit trail
POST /api/blockchain/analytics/auto-slash   — admin: trigger auto-slash run
POST /api/blockchain/validators/{id}/slash  — admin: manual slash
POST /api/blockchain/disputes/{id}/resolve  — admin: resolve oracle dispute
GET  /api/blockchain/disputes               — list open disputes
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.database import get_db
from app.modules.blockchain.models import (
    OracleDispute,
    ValidatorSlashEvent,
    ValidatorProfile,
)

router = APIRouter(prefix="/api/blockchain", tags=["Blockchain Analytics"])
logger = logging.getLogger(__name__)


# ── Analytics endpoints ────────────────────────────────────────────────────────

@router.get("/analytics/network")
async def network_stats(db: AsyncSession = Depends(get_db)):
    """Full blockchain network statistics snapshot. Public read-only."""
    try:
        from app.modules.blockchain.analytics import get_network_stats
        return await get_network_stats(db)
    except Exception as exc:
        logger.error("network_stats error: %s", exc)
        raise HTTPException(500, str(exc))


@router.get("/analytics/leaderboard")
async def validator_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Top validators ranked by influence score."""
    try:
        from app.modules.blockchain.analytics import get_validator_leaderboard
        return {"leaderboard": await get_validator_leaderboard(db, limit=limit)}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.get("/analytics/economics")
async def token_economics(db: AsyncSession = Depends(get_db)):
    """VITCoin token economics — supply, burns, treasury snapshot."""
    try:
        from app.modules.blockchain.analytics import get_token_economics
        return await get_token_economics(db)
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.get("/analytics/slash-history")
async def slash_history(
    limit: int = Query(50, ge=1, le=200),
    validator_id: Optional[str] = None,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: full slash audit trail."""
    q = select(ValidatorSlashEvent).order_by(ValidatorSlashEvent.slashed_at.desc()).limit(limit)
    if validator_id:
        q = q.where(ValidatorSlashEvent.validator_id == validator_id)
    result = await db.execute(q)
    rows = result.scalars().all()
    return {
        "slash_events": [
            {
                "id": r.id,
                "validator_id": r.validator_id,
                "user_id": r.user_id,
                "slash_reason": r.slash_reason,
                "slash_pct": float(r.slash_pct),
                "slash_amount": float(r.slash_amount),
                "stake_before": float(r.stake_before),
                "stake_after": float(r.stake_after),
                "trust_score_at_slash": float(r.trust_score_at_slash),
                "prior_slash_count": r.prior_slash_count,
                "admin_user_id": r.admin_user_id,
                "slashed_at": r.slashed_at.isoformat(),
            }
            for r in rows
        ],
        "count": len(rows),
    }


# ── Auto-slash trigger ─────────────────────────────────────────────────────────

@router.post("/analytics/auto-slash")
async def trigger_auto_slash(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: run the automated slash engine across all active validators."""
    try:
        from app.modules.blockchain.auto_slash import run_auto_slash
        summary = await run_auto_slash(db)
        await db.commit()
        return summary
    except Exception as exc:
        await db.rollback()
        raise HTTPException(500, str(exc))


# ── Manual slash ───────────────────────────────────────────────────────────────

class ManualSlashRequest(BaseModel):
    slash_pct: float = Field(..., ge=0.01, le=1.0)
    reason: str = Field(..., min_length=5, max_length=200)


@router.post("/validators/{validator_id}/slash")
async def manual_slash(
    validator_id: str,
    body: ManualSlashRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: manually slash a specific validator's staked amount."""
    try:
        from app.modules.blockchain.auto_slash import manual_slash as _slash
        result = await _slash(
            validator_id=validator_id,
            slash_pct=body.slash_pct,
            reason=body.reason,
            db=db,
            admin_user_id=admin.id,
        )
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        await db.rollback()
        raise HTTPException(500, str(exc))


# ── Oracle dispute management ──────────────────────────────────────────────────

@router.get("/disputes")
async def list_disputes(
    status: Optional[str] = Query(None, pattern="^(open|resolved|all)$"),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list oracle disputes."""
    q = select(OracleDispute).order_by(OracleDispute.created_at.desc()).limit(limit)
    if status and status != "all":
        q = q.where(OracleDispute.status == status)
    result = await db.execute(q)
    rows = result.scalars().all()
    return {
        "disputes": [
            {
                "id": r.id,
                "match_id": r.match_id,
                "source_a": r.source_a,
                "result_a": r.result_a,
                "source_b": r.source_b,
                "result_b": r.result_b,
                "resolution": r.resolution,
                "resolved_by": r.resolved_by,
                "resolution_note": r.resolution_note,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


class ResolveDisputeRequest(BaseModel):
    resolution: str = Field(..., pattern="^(home|draw|away|void)$")
    resolution_note: Optional[str] = None


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: str,
    body: ResolveDisputeRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: resolve an oracle dispute with a final result."""
    from datetime import datetime, timezone
    result = await db.execute(
        select(OracleDispute).where(OracleDispute.id == dispute_id)
    )
    dispute = result.scalar_one_or_none()
    if not dispute:
        raise HTTPException(404, "Dispute not found")
    if dispute.status == "resolved":
        raise HTTPException(400, "Dispute already resolved")

    dispute.resolution = body.resolution
    dispute.resolved_by = admin.id
    dispute.resolution_note = body.resolution_note
    dispute.status = "resolved"
    dispute.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    return {"dispute_id": dispute_id, "resolution": body.resolution, "status": "resolved"}
