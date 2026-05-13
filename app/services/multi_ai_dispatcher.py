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


_PROVIDER_TIMEOUT_SECONDS = 20


async def _call_provider(provider: str, kwargs: dict) -> dict:
    """Call a single AI provider with a per-provider timeout to prevent one slow
    provider from blocking the entire fan-out (L4-5 gap fix)."""
    async def _inner():
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

    try:
        result = await asyncio.wait_for(_inner(), timeout=_PROVIDER_TIMEOUT_SECONDS)
        return result
    except asyncio.TimeoutError:
        logger.warning(f"Provider {provider} timed out after {_PROVIDER_TIMEOUT_SECONDS}s")
        return {
            "available": False, "source": provider,
            "label": PROVIDER_LABELS.get(provider, provider),
            "error": f"Provider timeout after {_PROVIDER_TIMEOUT_SECONDS}s",
        }
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

    # ── Deduplicate fallback-only results ─────────────────────────────────────
    # Each *_insights service has its own _scie_fallback that returns
    # available=True + is_fallback=True when its LLM is down.  Without
    # deduplication the dispatcher returns 3 identical cards labelled
    # Gemini / Claude / Grok — misleading UX.
    #
    # Rule: if EVERY requested slot is a fallback result (no real LLM answered),
    # consolidate into a single "deterministic" key and mark the LLM slots
    # unavailable so the frontend shows one authoritative statistical card.
    llm_slots   = [s for s in sources if s in results and s != "deterministic"]
    real_llm    = [s for s in llm_slots if results[s].get("available") and not results[s].get("is_fallback")]
    fallback_llm = [s for s in llm_slots if results[s].get("is_fallback")]

    if not real_llm and fallback_llm:
        # Promote the first fallback result to the deterministic slot
        first_key = fallback_llm[0]
        det_result = dict(results[first_key])
        det_result["source"] = "deterministic"
        det_result["label"]  = "VIT Statistical Engine"
        results["deterministic"] = det_result
        # Mark all LLM slots as truly unavailable
        for key in llm_slots:
            results[key] = {
                "available": False, "source": key,
                "label": PROVIDER_LABELS.get(key, key),
                "error": "LLM unavailable — statistical fallback provided",
            }
        logger.info("[multi-ai] All LLM providers used fallback — consolidated into deterministic slot")
    elif not real_llm and not fallback_llm and "deterministic" not in results:
        # All providers hard-failed with available=False — inject deterministic
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
