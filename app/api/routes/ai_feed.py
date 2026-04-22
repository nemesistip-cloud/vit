# app/api/routes/ai_feed.py
"""API endpoints for live AI feed"""

import logging
from fastapi import APIRouter, Depends
from app.api.middleware.auth import verify_api_key
from app.schemas.schemas import MatchRequest
from app.services.live_ai_feed import LiveAIFeedService, AISource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-feed", tags=["AI Feed"], dependencies=[Depends(verify_api_key)])

ai_feed_service = LiveAIFeedService()


@router.post("/predictions")
async def get_ai_predictions(match: MatchRequest):
    """Get live AI predictions from all available free sources."""
    match_data = {
        "match_id": f"{match.home_team}_vs_{match.away_team}",
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "market_odds": match.market_odds,
    }
    result = await ai_feed_service.get_live_predictions(match_data)
    return {
        "match": {
            "home_team": match.home_team,
            "away_team": match.away_team,
            "league": match.league,
        },
        "ai_predictions": result,
    }


@router.post("/consensus")
async def get_ai_consensus(match: MatchRequest):
    """Get AI consensus and compare with market odds."""
    match_data = {
        "match_id": f"{match.home_team}_vs_{match.away_team}",
        "home_team": match.home_team,
        "away_team": match.away_team,
        "league": match.league,
        "market_odds": match.market_odds,
    }
    result = await ai_feed_service.get_live_odds_and_predictions(match_data)

    opportunities = []
    if result.get("high_disagreement"):
        opportunities.append("High AI disagreement - information asymmetry detected")

    market_comparison = result.get("market_comparison", {})
    edges = market_comparison.get("edge_vs_market", {})
    for outcome, edge in edges.items():
        if edge > 0.03:
            opportunities.append(f"AI consensus shows +{edge*100:.1f}% edge on {outcome}")
        elif edge < -0.03:
            opportunities.append(f"Market is more confident on {outcome} than AI")

    result["opportunities"] = opportunities
    return result


@router.get("/sources")
async def get_available_sources():
    """Get list of available AI prediction sources and their status."""
    sources = []
    for source in ai_feed_service.sources:
        sources.append({
            "name": source["name"].value,
            "enabled": source["enabled"],
            "requires_api_key": source["name"] in [AISource.BZZOIRO, AISource.SPORTBOT],
        })

    return {
        "sources": sources,
        "total_enabled": sum(1 for s in sources if s["enabled"]),
        "instructions": {
            "sports_skills": "pip install sports-skills",
            "bzzoiro": "Sign up at sports.bzzoiro.com for free API key",
            "sportbot": "Sign up at sportbot.ai for free tier API key",
            "football_bin": "No setup required",
        },
    }


@router.get("/health")
async def ai_feed_health():
    """Check health of all AI feed sources."""
    health_status = {}
    for source in ai_feed_service.sources:
        health_status[source["name"].value] = {
            "enabled": source["enabled"],
            "status": "ready" if source["enabled"] else "disabled",
        }
    return health_status
