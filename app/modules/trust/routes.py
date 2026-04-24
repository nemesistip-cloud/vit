"""
Module I — Trust, Reputation & Anti-Fraud — REST API routes
Prefix: /api/trust
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.deps import get_current_user, get_current_admin
from app.db.models import User
from app.modules.trust.engine import calculate_trust_score, refresh_all_trust_scores
from app.modules.trust.models import FraudFlag, RiskEvent, UserTrustScore

router = APIRouter(prefix="/api/trust", tags=["trust"])


# ─── Schemas ────────────────────────────────────────────────────────────────

class TrustScoreOut(BaseModel):
    user_id:            int
    composite_score:    float
    transaction_score:  float
    prediction_score:   float
    activity_score:     float
    fraud_penalty:      float
    risk_tier:          str
    total_flags:        int
    open_flags:         int
    last_calculated_at: Optional[datetime]

    class Config:
        from_attributes = True


class FraudFlagOut(BaseModel):
    id:              int
    user_id:         int
    flagged_by:      str
    category:        str
    severity:        str
    rule_code:       str
    title:           str
    detail:          Optional[str]
    status:          str
    evidence:        Optional[dict]
    reviewed_at:     Optional[datetime]
    resolution_note: Optional[str]
    created_at:      Optional[datetime]


class RiskEventOut(BaseModel):
    id:           int
    user_id:      int
    rule_code:    str
    score_impact: float
    detail:       Optional[str]
    evidence:     Optional[dict]
    created_at:   Optional[datetime]


class ReviewFlagIn(BaseModel):
    status:          str
    resolution_note: Optional[str] = None


class PlatformStatsOut(BaseModel):
    total_users_scored: int
    critical_tier:      int
    high_tier:          int
    medium_tier:        int
    low_tier:           int
    open_flags:         int
    flags_today:        int
    avg_composite:      float


# ─── Helpers ────────────────────────────────────────────────────────────────

def _parse_evidence(obj) -> Optional[dict]:
    raw = getattr(obj, "evidence_json", None)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return None


def _flag_out(f: FraudFlag) -> FraudFlagOut:
    return FraudFlagOut(
        id=f.id, user_id=f.user_id, flagged_by=f.flagged_by,
        category=f.category, severity=f.severity, rule_code=f.rule_code,
        title=f.title, detail=f.detail, status=f.status,
        evidence=_parse_evidence(f), reviewed_at=f.reviewed_at,
        resolution_note=f.resolution_note, created_at=f.created_at,
    )


def _event_out(e: RiskEvent) -> RiskEventOut:
    return RiskEventOut(
        id=e.id, user_id=e.user_id, rule_code=e.rule_code,
        score_impact=e.score_impact, detail=e.detail,
        evidence=_parse_evidence(e), created_at=e.created_at,
    )


# ─── User endpoints ─────────────────────────────────────────────────────────

@router.get("/me", response_model=TrustScoreOut, summary="My trust score")
async def get_my_trust_score(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    score = await calculate_trust_score(db, current_user.id)
    return score


@router.get("/me/flags", summary="My fraud flags")
async def get_my_flags(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(FraudFlag).where(FraudFlag.user_id == current_user.id)
    if status:
        q = q.where(FraudFlag.status == status)
    q = q.order_by(FraudFlag.created_at.desc()).limit(50)
    result = await db.execute(q)
    return [_flag_out(f) for f in result.scalars().all()]


@router.get("/me/events", summary="My risk events")
async def get_my_risk_events(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        select(RiskEvent)
        .where(RiskEvent.user_id == current_user.id)
        .order_by(RiskEvent.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    return [_event_out(e) for e in result.scalars().all()]


# ─── Admin endpoints ─────────────────────────────────────────────────────────

@router.get("/admin/stats", response_model=PlatformStatsOut, summary="Platform trust stats (admin)")
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    scores_result = await db.execute(select(UserTrustScore))
    scores = scores_result.scalars().all()

    tier_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_composite = 0.0
    for s in scores:
        tier_counts[s.risk_tier] = tier_counts.get(s.risk_tier, 0) + 1
        total_composite += s.composite_score
    avg_comp = total_composite / len(scores) if scores else 0.0

    open_flags_result = await db.execute(
        select(func.count(FraudFlag.id)).where(FraudFlag.status == "open")
    )
    open_flags = open_flags_result.scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count(FraudFlag.id)).where(FraudFlag.created_at >= today_start)
    )
    flags_today = today_result.scalar() or 0

    return PlatformStatsOut(
        total_users_scored=len(scores),
        critical_tier=tier_counts.get("critical", 0),
        high_tier=tier_counts.get("high", 0),
        medium_tier=tier_counts.get("medium", 0),
        low_tier=tier_counts.get("low", 0),
        open_flags=open_flags,
        flags_today=flags_today,
        avg_composite=round(avg_comp, 2),
    )


@router.get("/admin/flags", summary="All fraud flags (admin)")
async def list_all_flags(
    status:   Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    user_id:  Optional[int] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    q = select(FraudFlag)
    if status:
        q = q.where(FraudFlag.status == status)
    if severity:
        q = q.where(FraudFlag.severity == severity)
    if category:
        q = q.where(FraudFlag.category == category)
    if user_id:
        q = q.where(FraudFlag.user_id == user_id)
    q = q.order_by(FraudFlag.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return [_flag_out(f) for f in result.scalars().all()]


@router.get("/admin/users/{user_id}/score", response_model=TrustScoreOut, summary="Get/recalculate user trust score (admin)")
async def admin_get_score(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalars().first():
        raise HTTPException(404, "User not found")
    return await calculate_trust_score(db, user_id)


@router.patch("/admin/flags/{flag_id}/review", summary="Review a fraud flag (admin)")
async def review_flag(
    flag_id: int,
    body: ReviewFlagIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    valid = {"reviewed", "dismissed", "actioned"}
    if body.status not in valid:
        raise HTTPException(400, f"status must be one of {valid}")

    result = await db.execute(select(FraudFlag).where(FraudFlag.id == flag_id))
    flag = result.scalars().first()
    if not flag:
        raise HTTPException(404, "Flag not found")

    flag.status          = body.status
    flag.reviewed_by_id  = current_user.id
    flag.reviewed_at     = datetime.now(timezone.utc)
    flag.resolution_note = body.resolution_note
    await db.commit()

    await calculate_trust_score(db, flag.user_id)
    return {"ok": True, "flag_id": flag_id, "new_status": body.status}


@router.post("/admin/users/{user_id}/recalculate", response_model=TrustScoreOut, summary="Force recalculate (admin)")
async def force_recalculate(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user_result = await db.execute(select(User).where(User.id == user_id))
    if not user_result.scalars().first():
        raise HTTPException(404, "User not found")
    return await calculate_trust_score(db, user_id)


@router.post("/admin/batch-refresh", summary="Refresh all trust scores (admin)")
async def batch_refresh(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    count = await refresh_all_trust_scores(db)
    return {"ok": True, "users_updated": count}
