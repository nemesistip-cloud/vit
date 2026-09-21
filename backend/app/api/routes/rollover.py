"""
Rollover Engine API routes.

GET  /api/rollover/candidates  — upcoming fixtures available for certification
POST /api/rollover/run         — run the full certification pipeline  (admin)
GET  /api/rollover/certified   — paginated list of certification results
GET  /api/rollover/stats       — aggregate statistics
GET  /api/rollover/{id}        — single certificate detail
DELETE /api/rollover/{id}      — delete a certificate (admin)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin, get_current_user
from app.db.database import get_db
from app.db.models import Match, Prediction, RolloverCertificate
from app.services.rollover_engine import RolloverCertifier

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rollover", tags=["rollover"])


def _cert_to_dict(cert: RolloverCertificate, match: Match | None = None) -> dict:
    d = {
        "id":                  cert.id,
        "fixture_id":          cert.fixture_id,
        "prediction_id":       cert.prediction_id,
        "outcome":             cert.outcome,
        "outcome_label":       cert.outcome_label,
        "signal_density":      cert.signal_density,
        "model_confidence":    cert.model_confidence,
        "simulation_agreement": cert.simulation_agreement,
        "status":              cert.status,
        "kelly_fraction":      cert.kelly_fraction,
        "xg_source":           cert.xg_source,
        "home_lambda":         cert.home_lambda,
        "away_lambda":         cert.away_lambda,
        "mc_home_prob":        cert.mc_home_prob,
        "mc_draw_prob":        cert.mc_draw_prob,
        "mc_away_prob":        cert.mc_away_prob,
        "mc_btts_prob":        cert.mc_btts_prob,
        "mc_over25_prob":      cert.mc_over25_prob,
        "mc_under25_prob":     cert.mc_under25_prob,
        "mc_over35_prob":      cert.mc_over35_prob,
        "simulations_run":     cert.simulations_run,
        "top_correct_scores":  cert.top_correct_scores,
        "conflict_flags":      cert.conflict_flags or [],
        "pipeline_run_id":     cert.pipeline_run_id,
        "created_at":          cert.created_at.isoformat() if cert.created_at else None,
    }
    if match:
        d["fixture"] = {
            "home_team":    match.home_team,
            "away_team":    match.away_team,
            "league":       match.league,
            "kickoff_time": match.kickoff_time.isoformat() if match.kickoff_time else None,
            "opening_odds_home": match.opening_odds_home,
            "opening_odds_draw": match.opening_odds_draw,
            "opening_odds_away": match.opening_odds_away,
        }
    return d


@router.get("/candidates")
async def get_candidates(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Upcoming unresolved fixtures that can be passed through the engine."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now + timedelta(days=days)

    result = await db.execute(
        select(Match).where(
            and_(
                Match.kickoff_time >= now,
                Match.kickoff_time <= cutoff,
                Match.actual_outcome.is_(None),
                Match.sport == "football",
            )
        ).order_by(Match.kickoff_time).limit(100)
    )
    matches = result.scalars().all()

    # Check which ones already have predictions
    fix_ids = [m.id for m in matches]
    pred_result = await db.execute(
        select(Prediction.match_id, func.count(Prediction.id))
        .where(Prediction.match_id.in_(fix_ids))
        .group_by(Prediction.match_id)
    )
    pred_counts = {row[0]: row[1] for row in pred_result.all()}

    # Check which ones have certificates
    cert_result = await db.execute(
        select(RolloverCertificate.fixture_id, RolloverCertificate.status)
        .where(RolloverCertificate.fixture_id.in_(fix_ids))
        .order_by(RolloverCertificate.created_at.desc())
    )
    cert_map: dict[int, str] = {}
    for row in cert_result.all():
        if row[0] not in cert_map:
            cert_map[row[0]] = row[1]

    return {
        "candidates": [
            {
                "fixture_id":    m.id,
                "home_team":     m.home_team,
                "away_team":     m.away_team,
                "league":        m.league,
                "kickoff_time":  m.kickoff_time.isoformat() if m.kickoff_time else None,
                "has_prediction": pred_counts.get(m.id, 0) > 0,
                "cert_status":   cert_map.get(m.id),
                "has_odds":      bool(m.opening_odds_home),
            }
            for m in matches
        ],
        "total": len(matches),
        "days": days,
    }


@router.post("/run")
async def run_pipeline(
    days_ahead: int = Query(7, ge=1, le=30),
    n_simulations: int = Query(10000, ge=1000, le=100000),
    replace_existing: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Run the full rollover certification pipeline (admin only)."""
    certifier = RolloverCertifier(n_simulations=n_simulations)
    try:
        result = await certifier.run_pipeline(db, days_ahead=days_ahead, replace_existing=replace_existing)
        return result
    except Exception as exc:
        logger.error(f"[rollover] pipeline error: {exc}")
        raise HTTPException(500, f"Pipeline failed: {exc}")


@router.get("/certified")
async def get_certified(
    status: Optional[str] = Query(None, pattern="^(certified|watchlist|rejected)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Paginated list of certification results, newest first."""
    q = select(RolloverCertificate, Match).join(
        Match, RolloverCertificate.fixture_id == Match.id
    ).order_by(desc(RolloverCertificate.created_at))

    if status:
        q = q.where(RolloverCertificate.status == status)

    total_q = select(func.count(RolloverCertificate.id))
    if status:
        total_q = total_q.where(RolloverCertificate.status == status)

    total = (await db.execute(total_q)).scalar() or 0
    rows  = (await db.execute(q.offset(offset).limit(limit))).all()

    return {
        "items":  [_cert_to_dict(cert, match) for cert, match in rows],
        "total":  total,
        "offset": offset,
        "limit":  limit,
    }


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Aggregate rollover engine statistics."""
    # Total counts by status
    counts_result = await db.execute(
        select(RolloverCertificate.status, func.count(RolloverCertificate.id))
        .group_by(RolloverCertificate.status)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}

    # Average scores
    avg_result = await db.execute(
        select(
            func.avg(RolloverCertificate.signal_density),
            func.avg(RolloverCertificate.model_confidence),
            func.avg(RolloverCertificate.simulation_agreement),
        )
    )
    avg_row = avg_result.one()

    # Last run time
    last_run_result = await db.execute(
        select(func.max(RolloverCertificate.created_at))
    )
    last_run = last_run_result.scalar()

    # Win rate (certified picks that were settled)
    settled_result = await db.execute(
        select(
            func.count(RolloverCertificate.id).label("total"),
            func.sum(
                func.cast(RolloverCertificate.settled_correct, type_=None)
            ).label("wins"),
        ).where(
            RolloverCertificate.settled_correct.isnot(None)
        )
    )
    settled_row = settled_result.one()
    total_settled = settled_row[0] or 0
    total_wins    = int(settled_row[1] or 0)
    win_rate      = round(total_wins / total_settled, 4) if total_settled > 0 else None

    # Recent pipeline runs (distinct run IDs)
    pipeline_result = await db.execute(
        select(
            RolloverCertificate.pipeline_run_id,
            func.count(RolloverCertificate.id),
            func.max(RolloverCertificate.created_at),
        )
        .where(RolloverCertificate.pipeline_run_id.isnot(None))
        .group_by(RolloverCertificate.pipeline_run_id)
        .order_by(func.max(RolloverCertificate.created_at).desc())
        .limit(5)
    )
    recent_runs = [
        {"run_id": row[0], "count": row[1], "ran_at": row[2].isoformat() if row[2] else None}
        for row in pipeline_result.all()
    ]

    total_certs = sum(counts.values())

    return {
        "total_certified": counts.get("certified", 0),
        "total_watchlist":  counts.get("watchlist", 0),
        "total_rejected":   counts.get("rejected", 0),
        "total_all":        total_certs,
        "avg_signal_density":      round(float(avg_row[0] or 0), 1),
        "avg_model_confidence":    round(float(avg_row[1] or 0), 4),
        "avg_simulation_agreement": round(float(avg_row[2] or 0), 4),
        "win_rate":         win_rate,
        "total_settled":    total_settled,
        "last_run_at":      last_run.isoformat() if last_run else None,
        "recent_runs":      recent_runs,
    }


@router.get("/{cert_id}")
async def get_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Full certificate detail with fixture info."""
    result = await db.execute(
        select(RolloverCertificate, Match).join(
            Match, RolloverCertificate.fixture_id == Match.id
        ).where(RolloverCertificate.id == cert_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(404, "Certificate not found")
    cert, match = row
    return _cert_to_dict(cert, match)


@router.delete("/{cert_id}")
async def delete_certificate(
    cert_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Remove a certificate (admin only)."""
    result = await db.execute(
        select(RolloverCertificate).where(RolloverCertificate.id == cert_id)
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(404, "Certificate not found")
    await db.delete(cert)
    await db.commit()
    return {"status": "ok", "deleted": cert_id}
