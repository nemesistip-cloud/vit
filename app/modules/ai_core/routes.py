"""app/modules/ai_core/routes.py
AI Analytics Core — Atomic Match Model (AMM), Player DNA, Causal Inference.

All endpoints query the live database (AgentInsight, Prediction, Match) for real
data. Hardcoded demonstration values have been removed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import AgentInsight, Prediction, Match
from app.auth.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/ai-core", tags=["AI Core"])
logger = logging.getLogger(__name__)


@router.get("/player-dna/{player_id}")
async def get_player_dna(player_id: str, db: AsyncSession = Depends(get_db)):
    """
    Player DNA profile derived from AgentInsight records mentioning this player.

    Returns aggregated signal metrics from news-sentinel, match-scout, and
    odds-anomaly agents. When no data exists an explicit empty state is returned.
    """
    rows = (
        await db.execute(
            select(AgentInsight)
            .where(AgentInsight.content.ilike(f"%{player_id}%"))
            .order_by(desc(AgentInsight.created_at))
            .limit(20)
        )
    ).scalars().all()

    if not rows:
        return {
            "player_id":    player_id,
            "data_points":  0,
            "dna":          None,
            "note":         "No analytics data found. DNA is built from agent insight records.",
            "last_updated": None,
        }

    avg_confidence = sum(float(r.confidence or 0) for r in rows) / len(rows)
    providers = list({r.ai_provider for r in rows if r.ai_provider})
    insight_types = list({r.insight_type for r in rows if r.insight_type})

    return {
        "player_id":    player_id,
        "data_points":  len(rows),
        "dna": {
            "avg_confidence":  round(avg_confidence, 4),
            "insight_types":   insight_types,
            "ai_providers":    providers,
        },
        "last_updated": rows[0].created_at.isoformat() if rows[0].created_at else None,
    }


@router.get("/causal/inference")
async def get_causal_inference(match_id: int, db: AsyncSession = Depends(get_db)):
    """
    Causal inference summary for a specific match.

    Aggregates prediction confidence shifts from AgentInsight records for the match.
    """
    rows = (
        await db.execute(
            select(AgentInsight)
            .where(AgentInsight.match_id == match_id)
            .order_by(desc(AgentInsight.created_at))
            .limit(50)
        )
    ).scalars().all()

    if not rows:
        return {
            "match_id":       match_id,
            "causal_signals": 0,
            "key_factors":    [],
            "note":           "No causal signals found for this match.",
        }

    # Extract key factors from insight content
    factors = []
    for r in rows:
        if r.insight_type in ("match_scout", "odds_anomaly") and r.content:
            factors.append({
                "agent":       r.agent_name,
                "type":        r.insight_type,
                "confidence":  float(r.confidence or 0),
                "summary":     r.content[:120],
                "provider":    r.ai_provider,
            })

    avg_conf = round(
        sum(f["confidence"] for f in factors) / len(factors), 4
    ) if factors else 0.0

    return {
        "match_id":          match_id,
        "causal_signals":    len(rows),
        "avg_confidence":    avg_conf,
        "key_factors":       factors[:5],
        "last_updated":      rows[0].created_at.isoformat() if rows[0].created_at else None,
    }


@router.get("/atomic/pitch-snapshot")
async def get_pitch_snapshot(match_id: int, db: AsyncSession = Depends(get_db)):
    """
    Live pitch snapshot for a match — returns live match data from the DB.
    Full 25 Hz positional data requires a connected tracking provider.
    """
    match = (
        await db.execute(select(Match).where(Match.id == match_id))
    ).scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    return {
        "match_id":   match_id,
        "home_team":  match.home_team,
        "away_team":  match.away_team,
        "status":     match.status,
        "home_score": match.home_goals,
        "away_score": match.away_goals,
        "minute":     getattr(match, "minute", None),
        "tracking_data": None,
        "note": (
            "Full 25 Hz positional tracking requires a connected stadium/broadcast provider. "
            "Set TRACKING_PROVIDER_URL in Secrets to enable."
        ),
    }


@router.get("/momentum/tensor")
async def get_momentum_tensor(match_id: int, db: AsyncSession = Depends(get_db)):
    """
    Multi-dimensional momentum tensor derived from prediction confidence
    and AgentInsight signals for the match.
    """
    # Get latest prediction confidence for the match
    pred = (
        await db.execute(
            select(Prediction)
            .where(Prediction.match_id == match_id)
            .order_by(desc(Prediction.timestamp))
            .limit(1)
        )
    ).scalar_one_or_none()

    # Get insight count for tactical signals
    insight_count = (
        await db.execute(
            select(func.count(AgentInsight.id))
            .where(AgentInsight.match_id == match_id)
        )
    ).scalar() or 0

    if not pred:
        return {
            "match_id":  match_id,
            "momentum":  None,
            "data_available": False,
            "note": "No prediction data for this match.",
        }

    home_conf  = float(getattr(pred, "home_prob", 0.33))
    away_conf  = float(getattr(pred, "away_prob", 0.33))
    draw_conf  = float(getattr(pred, "draw_prob", 0.34))
    model_conf = float(pred.confidence or 50) / 100.0

    trend = "rising" if home_conf > 0.4 else ("falling" if away_conf > 0.4 else "neutral")

    return {
        "match_id": match_id,
        "momentum": {
            "spatial":        round(model_conf, 4),
            "psychological":  round(home_conf,  4),
            "physiological":  round(draw_conf,  4),
        },
        "trend":         trend,
        "insight_count": insight_count,
        "data_available": True,
        "last_updated":  pred.timestamp.isoformat() if pred.timestamp else None,
    }
