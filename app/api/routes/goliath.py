"""app/api/routes/goliath.py — Goliath G-Score Over/Under API.

GET  /api/goliath/{match_id}   — G-Score for a stored match
POST /api/goliath/predict       — G-Score from raw team + league params
GET  /api/goliath/sharp         — Sharp money signals across upcoming matches
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import verify_api_key
from app.db.database import get_db
from app.services.goliath_score import compute_goliath_score
from app.services.sharp_money import scan_all_sharp_movements, analyze_odds_movement

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/goliath", tags=["goliath"])


class GoliathRequest(BaseModel):
    home_team:      str             = Field(..., min_length=1, max_length=100)
    away_team:      str             = Field(..., min_length=1, max_length=100)
    league:         Optional[str]   = Field("default", max_length=80)
    kickoff_hour:   int             = Field(15, ge=0, le=23)
    home_form_pts:  float           = Field(1.3, ge=0.0, le=3.0)
    away_form_pts:  float           = Field(1.2, ge=0.0, le=3.0)


@router.get("/predict/{home_team}/{away_team}")
async def goliath_predict_get(
    home_team: str,
    away_team: str,
    league:       str = Query("default"),
    kickoff_hour: int = Query(15, ge=0, le=23),
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """
    Convenience GET: compute Goliath G-Score from team names in the URL path.

    Example: GET /api/goliath/predict/Manchester%20City/Arsenal?league=premier_league
    """
    try:
        result = await compute_goliath_score(
            db=db,
            home_team=home_team,
            away_team=away_team,
            league=league or "default",
            kickoff_hour=kickoff_hour,
        )
        return result
    except Exception as exc:
        logger.error("[goliath] predict GET error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/elo/ratings")
async def elo_ratings_list(
    league:    Optional[str] = Query(None, description="Filter by league"),
    limit:     int           = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """Return top team ELO ratings optionally filtered by league."""
    try:
        from sqlalchemy import text
        where = "WHERE league = :league" if league else ""
        stmt = text(
            f"SELECT team_name, league, elo_rating, matches_played, last_updated "
            f"FROM team_elo {where} ORDER BY elo_rating DESC LIMIT :lim"
        )
        params: Dict[str, Any] = {"lim": limit}
        if league:
            params["league"] = league
        result = await db.execute(stmt, params)
        rows = result.fetchall()
        return {
            "count":   len(rows),
            "ratings": [
                {
                    "team_name":      r[0],
                    "league":         r[1],
                    "elo_rating":     round(float(r[2]), 1),
                    "matches_played": r[3],
                    "last_updated":   r[4].isoformat() if r[4] else None,
                }
                for r in rows
            ],
        }
    except Exception as exc:
        logger.warning("[goliath] elo ratings error: %s", exc)
        return {"count": 0, "ratings": [], "note": "ELO table not yet populated"}


@router.get("/elo/{team_name}")
async def elo_for_team(
    team_name: str,
    league: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """Return ELO rating for a specific team."""
    try:
        from app.ml.features.elo import get_elo_rating, _ensure_table
        await _ensure_table(db)
        rating, matches_played = await get_elo_rating(db, team_name, league or "default")
        return {
            "team_name":      team_name,
            "league":         league or "default",
            "elo_rating":     round(rating, 1),
            "matches_played": matches_played,
        }
    except Exception as exc:
        logger.warning("[goliath] elo team error: %s", exc)
        return {"team_name": team_name, "elo_rating": 1500.0, "matches_played": 0, "note": str(exc)}


@router.get("/{match_id}")
async def goliath_for_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """
    Compute Goliath G-Score for a match stored in the database.

    Returns expected goals, over/under probabilities, BTTS odds, and the
    composite G-Score index (0–100) that indicates match goal intensity.
    """
    try:
        from app.db.models import Match
        from sqlalchemy import select

        row = await db.execute(select(Match).where(Match.id == match_id))
        match = row.scalar_one_or_none()
        if not match:
            raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

        kickoff_hour = 15
        if match.kickoff_time:
            kt = match.kickoff_time
            if kt.tzinfo is None:
                kt = kt.replace(tzinfo=timezone.utc)
            kickoff_hour = kt.hour

        result = await compute_goliath_score(
            db=db,
            home_team=match.home_team,
            away_team=match.away_team,
            league=match.league or "default",
            kickoff_hour=kickoff_hour,
        )
        result["match_id"] = match_id
        result["kickoff_time"] = match.kickoff_time.isoformat() if match.kickoff_time else None
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[goliath] match_id=%s error: %s", match_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/predict")
async def goliath_predict(
    req: GoliathRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """
    Compute Goliath G-Score from raw team/league parameters without a stored match.

    Useful for quick pre-match analysis before a match is registered in the DB.
    """
    try:
        result = await compute_goliath_score(
            db=db,
            home_team=req.home_team,
            away_team=req.away_team,
            league=req.league or "default",
            kickoff_hour=req.kickoff_hour,
            home_form_pts=req.home_form_pts,
            away_form_pts=req.away_form_pts,
        )
        return result
    except Exception as exc:
        logger.error("[goliath] predict error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sharp/signals")
async def sharp_money_signals(
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """
    Scan all upcoming matches (next 3 days) for sharp money movements.

    Returns matches where opening odds vs. current odds show >2% probability
    shift — a classic indicator of professional betting activity.
    """
    try:
        signals = await scan_all_sharp_movements(db)
        return {
            "count":   len(signals),
            "signals": signals,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("[goliath] sharp signals error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


