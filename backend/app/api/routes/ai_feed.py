# app/api/routes/ai_feed.py
"""API endpoints for live AI feed"""

import logging
from time import perf_counter
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_optional_user
from app.schemas.schemas import MatchRequest
from app.services.live_ai_feed import LiveAIFeedService
from app.services.vit_ai_client import vit_ai_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-feed", tags=["AI Feed"])

ai_feed_service = LiveAIFeedService()


@router.post("/predictions")
async def get_ai_predictions(match: MatchRequest, current_user=Depends(get_optional_user)):
    """Get live AI predictions from native intelligence sources."""
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
async def get_ai_consensus(match: MatchRequest, current_user=Depends(get_optional_user)):
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
            opportunities.append(f"Native AI shows +{edge*100:.1f}% edge on {outcome}")
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
            "requires_api_key": False,
        })

    return {
        "sources": sources,
        "total_enabled": sum(1 for s in sources if s["enabled"]),
        "instructions": {
            "native": "Always enabled internal intelligence engine",
        },
    }


@router.get("/models")
async def get_live_models():
    """Proxy public model metadata through the authenticated vit-ai client."""
    try:
        models = await vit_ai_client.get_models()
    except Exception as exc:
        logger.warning("Live vit-ai model registry unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="AI model registry unavailable") from exc
    if not isinstance(models, list):
        raise HTTPException(status_code=502, detail="AI model registry returned an invalid response")
    return {"models": models, "registered_count": len(models)}


@router.get("/health")
async def ai_feed_health():
    """Proxy live vit-ai health and report the actual gateway round-trip time."""
    started_at = perf_counter()
    try:
        health = await vit_ai_client.get_health()
    except Exception as exc:
        logger.warning("Live vit-ai health unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="AI service health unavailable") from exc

    service_status = health["status"]
    sources_status = {
        source["name"].value: {
            "enabled": source["enabled"],
            "status": service_status if source["enabled"] else "disabled",
        }
        for source in ai_feed_service.sources
    }
    return {
        "status": service_status,
        "version": health.get("version"),
        "provider_count": sum(1 for s in ai_feed_service.sources if s.get("enabled")),
        "models_loaded": health.get("models_loaded"),
        "latency_ms": round((perf_counter() - started_at) * 1000, 1),
        "sources": sources_status,
    }
