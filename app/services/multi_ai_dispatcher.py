"""app/services/multi_ai_dispatcher.py
Fan-out match analysis to multiple AI providers in parallel,
ingest probability outputs into AIPrediction table.
"""

import asyncio
import logging
from typing import List, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

PROVIDERS = ["gemini", "claude", "grok"]

PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "claude": "Anthropic Claude",
    "grok":   "xAI Grok",
}


async def _call_provider(provider: str, kwargs: dict) -> dict:
    try:
        if provider == "gemini":
            from app.services.gemini_insights import generate_match_insights
        elif provider == "claude":
            from app.services.claude_insights import generate_match_insights
        elif provider == "grok":
            from app.services.grok_insights import generate_match_insights
        else:
            return {"available": False, "source": provider, "error": f"Unknown provider: {provider}"}
        result = await generate_match_insights(**kwargs)
        result["source"] = provider
        result["label"]  = PROVIDER_LABELS.get(provider, provider)
        return result
    except Exception as exc:
        logger.error(f"Provider {provider} failed: {exc}")
        return {
            "available": False, "source": provider,
            "label": PROVIDER_LABELS.get(provider, provider),
            "error": str(exc),
        }


async def run_multi_ai(
    match_id: int,
    db: AsyncSession,
    sources: Optional[List[str]] = None,
) -> Dict:
    """
    Fetch match + prediction data from DB, fan-out to selected AI providers,
    ingest probability outputs, return all results.
    """
    from app.db.models import Match, Prediction

    sources = [s for s in (sources or PROVIDERS) if s in PROVIDERS]
    if not sources:
        return {"results": {}, "sources_requested": [], "match_id": match_id}

    match_row = await db.execute(select(Match).where(Match.id == match_id))
    match = match_row.scalar_one_or_none()
    if not match:
        raise ValueError(f"Match {match_id} not found")

    pred_row = await db.execute(select(Prediction).where(Prediction.match_id == match_id))
    pred = pred_row.scalar_one_or_none()

    kwargs = dict(
        home_team=match.home_team,
        away_team=match.away_team,
        league=match.league or "unknown",
        home_prob=pred.home_prob if pred else 0.33,
        draw_prob=pred.draw_prob if pred else 0.33,
        away_prob=pred.away_prob if pred else 0.34,
        over_25_prob=pred.over_25_prob if pred else None,
        btts_prob=pred.btts_prob if pred else None,
        bet_side=pred.bet_side if pred else None,
        edge=pred.vig_free_edge if pred else 0.0,
        entry_odds=pred.entry_odds if pred else None,
        confidence=float(pred.confidence) if pred and pred.confidence else 0.5,
    )

    from app.services.insight_store import load_match_insights

    defaults = {
        "home_prob": kwargs["home_prob"],
        "draw_prob": kwargs["draw_prob"],
        "away_prob": kwargs["away_prob"],
        "confidence": kwargs["confidence"],
    }
    cached = load_match_insights(match_id, defaults=defaults)
    results = {source: cached[source] for source in sources if source in cached}
    missing_sources = [source for source in sources if source not in results]

    if missing_sources:
        tasks = [_call_provider(s, kwargs) for s in missing_sources]
        results_list = await asyncio.gather(*tasks, return_exceptions=False)
        results.update({r["source"]: r for r in results_list})

    # Ingest probability outputs into AIPrediction table
    for source, r in results.items():
        if r.get("available") and r.get("home_prob") is not None:
            try:
                from app.services.ai_ingestion import AIIngestionService
                svc = AIIngestionService(db)
                await svc.ingest_prediction(
                    match_id=match_id,
                    source=source,
                    home_prob=float(r["home_prob"]),
                    draw_prob=float(r["draw_prob"]),
                    away_prob=float(r["away_prob"]),
                    confidence=float(r.get("confidence") or 0.7),
                    reason=r.get("summary", "")[:500] if r.get("summary") else None,
                )
            except Exception as exc:
                logger.warning(f"Failed to ingest {source} prediction: {exc}")

    return {
        "match_id": match_id,
        "sources_requested": sources,
        "cache_hits": sorted([source for source, result in results.items() if result.get("from_cache")]),
        "results": results,
    }
