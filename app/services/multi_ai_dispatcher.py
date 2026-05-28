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

PROVIDERS = ["gemini", "claude", "grok", "openai"]

PROVIDER_LABELS = {
    "gemini":        "Google Gemini",
    "claude":        "Anthropic Claude",
    "grok":          "xAI Grok",
    "openai":        "OpenAI GPT",
    "deterministic": "VIT Statistical Engine",
}


async def _call_provider(provider: str, kwargs: dict) -> dict:
    try:
        if provider == "gemini":
            from app.services.gemini_insights import generate_match_insights
        elif provider == "claude":
            from app.services.claude_insights import generate_match_insights
        elif provider == "grok":
            from app.services.grok_insights import generate_match_insights
        elif provider == "openai":
            from app.services.openai_insights import generate_match_insights
        elif provider == "deterministic":
            from app.services.deterministic_insights import generate_match_insights
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
        # Wrap each provider call in a timeout to prevent slow APIs from hanging the entire request
        # We use a 12s timeout per provider.
        tasks = [asyncio.wait_for(_call_provider(s, kwargs), timeout=12.0) for s in missing_sources]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        for i, r in enumerate(results_list):
            requested_source = missing_sources[i]
            if isinstance(r, asyncio.TimeoutError):
                logger.warning(f"[multi-ai] Provider {requested_source} timed out after 12s")
                results[requested_source] = {
                    "available": False,
                    "source": requested_source,
                    "label": PROVIDER_LABELS.get(requested_source, requested_source),
                    "error": "Request timed out after 12s",
                }
            elif isinstance(r, Exception):
                logger.error(f"[multi-ai] Provider {requested_source} failed with exception: {r}")
                results[requested_source] = {
                    "available": False,
                    "source": requested_source,
                    "label": PROVIDER_LABELS.get(requested_source, requested_source),
                    "error": str(r),
                }
            else:
                # Successfully returned a result dict
                results[requested_source] = r

    # ── Deterministic fallback: ensure at least one result is available ───────
    # If every LLM provider failed or is cooling down, inject the statistical
    # engine result so the AI panel is never completely empty.
    llm_available = any(
        r.get("available") for s, r in results.items() if s != "deterministic"
    )
    if not llm_available and "deterministic" not in results:
        logger.info("[multi-ai] All LLM providers unavailable — using deterministic fallback")
        det_result = await _call_provider("deterministic", kwargs)
        results["deterministic"] = det_result

    # ── Ingest probability outputs into AIPrediction table ───────────
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

    # ── Persist freshly generated insights to disk (TTL-cached) ──────
    new_insights = {
        source: r for source, r in results.items()
        if not r.get("from_cache") and r.get("available")
    }
    if new_insights:
        try:
            from app.services.insight_store import INSIGHTS_DIR, _path_for
            import json as _json
            import os as _os
            from datetime import datetime as _dt, timezone as _tz

            _os.makedirs(INSIGHTS_DIR, exist_ok=True)
            cache_path = _path_for(match_id)

            # Merge with existing file if present (to preserve other providers' cached data)
            existing_cached: dict = {}
            if _os.path.exists(cache_path):
                try:
                    with open(cache_path, encoding="utf-8") as _f:
                        _existing = _json.load(_f)
                    existing_cached = _existing.get("insights", {})
                except Exception:
                    existing_cached = {}

            merged_insights = {**existing_cached, **new_insights}
            payload = {
                "match_id": match_id,
                "generated_at": _dt.now(_tz.utc).isoformat(),
                "insights": merged_insights,
            }
            with open(cache_path, "w", encoding="utf-8") as _f:
                _json.dump(payload, _f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"Failed to cache insights for match {match_id}: {exc}")

    cache_hits = sorted(s for s, r in results.items() if r.get("from_cache"))
    return {
        "match_id": match_id,
        "sources_requested": sources,
        "cache_hits": cache_hits,
        "results": results,
    }
