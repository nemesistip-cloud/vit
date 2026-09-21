"""
Module F — Data Pipeline API Routes

GET  /api/pipeline/status              — pipeline health + stats
POST /api/pipeline/run                 — admin: trigger full ETL
POST /api/pipeline/refresh/odds        — admin: trigger odds-only refresh
GET  /api/pipeline/features            — list all feature records
GET  /api/pipeline/features/{match_id} — get features for one match
GET  /api/pipeline/runs                — ETL run history
WS   /api/pipeline/ws/odds             — real-time odds/event stream
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.data.models import MatchFeatureStore, PipelineRun
from app.data.pipeline import run_full_etl, run_odds_refresh, get_pipeline_status
from app.data.realtime import odds_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["Data Pipeline"])


# ---------------------------------------------------------------------------
# Status & health
# ---------------------------------------------------------------------------

@router.get("/status")
async def pipeline_status():
    """Pipeline health, last run summary, and feature store stats."""
    return await get_pipeline_status()


# ---------------------------------------------------------------------------
# Manual triggers (admin only)
# ---------------------------------------------------------------------------

@router.post("/run")
async def trigger_full_etl(
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """Trigger a full ETL run in the background. Admin only."""
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    background_tasks.add_task(_run_etl_task)
    return {"message": "Full ETL run queued", "status": "queued"}


@router.post("/refresh/odds")
async def trigger_odds_refresh(
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """Trigger a lightweight odds-only refresh. Admin only."""
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    background_tasks.add_task(_run_odds_refresh_task)
    return {"message": "Odds refresh queued", "status": "queued"}


async def _run_etl_task():
    try:
        await run_full_etl(run_type="manual")
    except Exception as e:
        logger.error(f"[pipeline] Manual ETL failed: {e}", exc_info=True)


async def _run_odds_refresh_task():
    try:
        await run_odds_refresh()
    except Exception as e:
        logger.error(f"[pipeline] Manual odds refresh failed: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Feature store queries
# ---------------------------------------------------------------------------

@router.get("/features")
async def list_features(
    league: Optional[str] = Query(None, description="Filter by league"),
    active_only: bool = Query(True, description="Exclude stale (past kickoff) records"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """List all feature records from the store."""
    q = select(MatchFeatureStore).order_by(MatchFeatureStore.kickoff_time)

    if league:
        q = q.where(MatchFeatureStore.league == league)
    if active_only:
        q = q.where(MatchFeatureStore.is_stale == False)

    total_q = select(MatchFeatureStore)
    if league:
        total_q = total_q.where(MatchFeatureStore.league == league)
    if active_only:
        total_q = total_q.where(MatchFeatureStore.is_stale == False)

    all_records = (await db.execute(total_q)).scalars().all()
    records = (await db.execute(q.offset(offset).limit(limit))).scalars().all()

    return {
        "total": len(all_records),
        "offset": offset,
        "limit": limit,
        "records": [_serialize_feature_record(r) for r in records],
    }


@router.get("/features/{match_id}")
async def get_features(match_id: str, db: AsyncSession = Depends(get_db)):
    """Get the full feature vector for a specific match."""
    record = (
        await db.execute(select(MatchFeatureStore).where(MatchFeatureStore.match_id == match_id))
    ).scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail=f"No features found for match_id={match_id}")

    return _serialize_feature_record(record, include_full=True)


# ---------------------------------------------------------------------------
# Pipeline run history
# ---------------------------------------------------------------------------

@router.get("/runs")
async def list_pipeline_runs(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return recent ETL pipeline run history."""
    runs = (
        await db.execute(
            select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(limit)
        )
    ).scalars().all()

    return {
        "total": len(runs),
        "runs": [
            {
                "id": r.id,
                "run_type": r.run_type,
                "status": r.status,
                "leagues_processed": r.leagues_processed,
                "matches_upserted": r.matches_upserted,
                "matches_skipped": r.matches_skipped,
                "errors": r.errors,
                "duration_seconds": r.duration_seconds,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in runs
        ],
    }


# ---------------------------------------------------------------------------
# WebSocket — real-time odds stream
# ---------------------------------------------------------------------------

@router.websocket("/ws/odds")
async def websocket_odds(websocket: WebSocket):
    """
    Real-time WebSocket stream for live odds updates and pipeline events.

    Subscribe to a league:
        {"action": "subscribe", "league": "premier_league"}

    Subscribe to all leagues:
        {"action": "subscribe", "league": "*"}

    Keepalive ping:
        {"action": "ping"}
    """
    await odds_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await odds_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        await odds_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"[ws] Unexpected error: {e}")
        await odds_manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------

def _serialize_feature_record(r: MatchFeatureStore, include_full: bool = False) -> Dict[str, Any]:
    base = {
        "match_id": r.match_id,
        "home_team": r.home_team,
        "away_team": r.away_team,
        "league": r.league,
        "kickoff_time": r.kickoff_time.isoformat() if r.kickoff_time else None,
        "source_quality": r.source_quality,
        "pipeline_version": r.pipeline_version,
        "is_stale": r.is_stale,
        "last_updated": r.last_updated.isoformat() if r.last_updated else None,
    }
    if include_full:
        base["features"] = r.features
        base["odds_snapshot"] = r.odds_snapshot
        base["injury_snapshot"] = r.injury_snapshot
    else:
        # Summary: only market and key form features
        f = r.features or {}
        base["summary"] = {
            "market_home_prob_vf": f.get("market_home_prob_vf"),
            "market_draw_prob_vf": f.get("market_draw_prob_vf"),
            "market_away_prob_vf": f.get("market_away_prob_vf"),
            "home_form_points": f.get("home_form_points"),
            "away_form_points": f.get("away_form_points"),
            "home_position": f.get("home_position"),
            "away_position": f.get("away_position"),
            "home_injury_score": f.get("home_injury_score"),
            "away_injury_score": f.get("away_injury_score"),
        }
    return base
