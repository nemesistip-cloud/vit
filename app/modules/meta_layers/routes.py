"""app/modules/meta_layers/routes.py
Meta-Layers — Evolutionary algorithms, collective intelligence, swarm consensus.

Reads live data from SwarmOrchestrator and DB rather than returning hardcoded stubs.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Depends

from app.api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meta", tags=["Meta-Layers"])


@router.get("/swarm/consensus")
async def get_swarm_consensus(match_id: int, _=Depends(verify_api_key)):
    """
    Return live swarm consensus for a match.

    Reads the SwarmOrchestrator health summary to calculate true swarm size
    and uses AgentInsight records for the consensus signal.
    """
    try:
        from app.core.swarm_orchestrator import get_swarm
        swarm = get_swarm()
        health = swarm.health_summary()
        swarm_size = health.get("running", 0)
        total       = health.get("total",   0)
        efficiency  = health.get("avg_efficiency", 0.0)
    except RuntimeError:
        swarm_size = 0
        total = 0
        efficiency = 0.0

    # Pull latest agent insights for this match to determine consensus
    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentInsight
        from sqlalchemy import select, desc

        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(AgentInsight)
                    .where(AgentInsight.match_id == match_id)
                    .order_by(desc(AgentInsight.created_at))
                    .limit(50)
                )
            ).scalars().all()

        # Tally consensus from insight content keywords
        home_votes = draw_votes = away_votes = 0
        for r in rows:
            txt = (r.content or "").lower()
            if "home win" in txt or "home victory" in txt:
                home_votes += 1
            elif "draw" in txt or "tie" in txt:
                draw_votes += 1
            elif "away win" in txt or "away victory" in txt:
                away_votes += 1

        total_votes = home_votes + draw_votes + away_votes
        if total_votes:
            if home_votes >= draw_votes and home_votes >= away_votes:
                consensus = "home_win"
            elif away_votes >= draw_votes:
                consensus = "away_win"
            else:
                consensus = "draw"
            diversity_score = round(1.0 - max(home_votes, draw_votes, away_votes) / total_votes, 3)
        else:
            consensus = "insufficient_data"
            diversity_score = 1.0

    except Exception as exc:
        logger.warning("[meta] swarm/consensus DB error: %s", exc)
        consensus = "insufficient_data"
        diversity_score = 1.0
        total_votes = 0

    return {
        "match_id":       match_id,
        "swarm_size":     swarm_size,
        "total_agents":   total,
        "avg_efficiency": round(efficiency, 4),
        "consensus":      consensus,
        "diversity_score": diversity_score,
        "votes":          total_votes,
    }


@router.get("/swarm/health")
async def get_swarm_health(_=Depends(verify_api_key)):
    """Real-time SwarmOrchestrator health: agent counts, efficiency, and leaderboard."""
    try:
        from app.core.swarm_orchestrator import get_swarm
        swarm = get_swarm()
        return {
            "health":      swarm.health_summary(),
            "leaderboard": swarm.leaderboard(top_n=5),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/temporal/career-prediction")
async def predict_career(player_id: str, _=Depends(verify_api_key)):
    """
    Player career trajectory prediction.

    Uses AI analysis from stored AgentInsight records where available,
    falling back to a statistical estimate based on player_id presence in DB.
    """
    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentInsight
        from sqlalchemy import select, desc

        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(AgentInsight)
                    .where(AgentInsight.content.ilike(f"%{player_id}%"))
                    .where(AgentInsight.insight_type.in_(["match_scout", "team_news"]))
                    .order_by(desc(AgentInsight.created_at))
                    .limit(10)
                )
            ).scalars().all()

        if rows:
            # Derive a simple signal from insight quality scores
            avg_confidence = sum(
                float(r.confidence or 0) for r in rows
            ) / len(rows)
            longevity_score = round(min(0.99, 0.5 + avg_confidence * 0.5), 3)
            note = f"Based on {len(rows)} intelligence reports"
        else:
            longevity_score = None
            note = "No intelligence data found for this player_id"

        return {
            "player_id":       player_id,
            "longevity_score": longevity_score,
            "data_points":     len(rows) if rows else 0,
            "note":            note,
        }
    except Exception as exc:
        logger.error("[meta] career-prediction error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
