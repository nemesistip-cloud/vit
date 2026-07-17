# app/modules/ai/orchestrator.py
"""
E2 — Ensemble Orchestrator Service

Wraps the existing ModelOrchestrator, applies DB weights,
wires AISignalCache as LLM signal input (P0#1 / P1#4),
and writes every prediction to the AIPredictionAudit log.
"""

import logging
import math
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import AIPredictionAudit
from app.services.accuracy_enhancer import TemperatureScaler

logger = logging.getLogger(__name__)


def _entropy(h: float, d: float, a: float) -> float:
    total = 0.0
    for p in (h, d, a):
        if p > 0:
            total -= p * math.log(p)
    return total


async def _load_ai_signals(db: AsyncSession, match_id: str) -> Dict:
    """
    P0#1 / P1#4: Fetch AISignalCache for the match and return
    the signal dict that will be injected into features["ai_signals"].
    Returns an empty dict when no cache row exists.
    """
    try:
        from sqlalchemy import select
        from app.db.models import AISignalCache, AIPerformance

        result = await db.execute(
            select(AISignalCache).where(AISignalCache.match_id == int(match_id))
        )
        cache = result.scalar_one_or_none()
        if cache is None:
            return {}

        signals: Dict = {
            "ai_consensus_home": cache.consensus_home,
            "ai_consensus_draw": cache.consensus_draw,
            "ai_consensus_away": cache.consensus_away,
            "ai_weighted_home":  cache.weighted_home,
            "ai_weighted_draw":  cache.weighted_draw,
            "ai_weighted_away":  cache.weighted_away,
            "ai_disagreement":   cache.disagreement_score,
            "ai_max_confidence": cache.max_confidence,
            "ai_avg_confidence": 0.5,
            "ai_provider_count": 0,
        }

        # Enrich with per-provider signals and average accuracy
        per_ai = cache.per_ai_predictions or {}
        for provider, probs in per_ai.items():
            signals[f"ai_{provider}_home"] = probs.get("home", 0.33)
            signals[f"ai_{provider}_draw"] = probs.get("draw", 0.33)
            signals[f"ai_{provider}_away"] = probs.get("away", 0.33)
        signals["ai_provider_count"] = len(per_ai)

        # Average accuracy of participating providers
        if per_ai:
            perf_res = await db.execute(
                select(AIPerformance).where(
                    AIPerformance.source.in_(list(per_ai.keys()))
                )
            )
            perfs = perf_res.scalars().all()
            if perfs:
                avg_acc = sum(p.accuracy for p in perfs) / len(perfs)
                signals["ai_avg_confidence"] = round(avg_acc, 4)

        return signals
    except Exception as exc:
        logger.debug("[E2] AI signal load failed for match_id=%s: %s", match_id, exc)
        return {}


async def generate_ai_prediction(
    features: Dict[str, Any],
    match_id: str,
    orchestrator: Any,
    sport: str = "soccer",
    db: Optional[AsyncSession] = None,
    triggered_by: str = "api",
) -> Dict[str, Any]:
    """
    E2 — Core ensemble prediction entry point.

    1. Pre-fetches AISignalCache and injects into features["ai_signals"]
       so Model #13 (LLM Consensus) can consume it (P0#1 / P1#4).
    2. Calls the existing ModelOrchestrator.predict() which applies
       per-model algorithms, the diversity-weighted aggregation,
       bootstrap CI (P2#10), and per-league weights (P1#5).
    3. Enriches the result with risk_score (entropy) and
       a weights snapshot from the live orchestrator.
    4. Writes the full result to the AIPredictionAudit table (E4)
       including the attribution block (P3#14).

    Returns the same dict shape as ModelOrchestrator.predict() with
    an additional `audit_id` field.
    """
    # ── P0#1 / P1#4: Wire AI signals into features ────────────────────────────
    if db is not None and "ai_signals" not in features:
        try:
            match_id_int = int(match_id)
            signals = await _load_ai_signals(db, str(match_id_int))
            if signals:
                features = dict(features)
                features["ai_signals"] = signals
                logger.debug(
                    "[E2] Injected AI signals for match_id=%s (providers=%s)",
                    match_id, signals.get("ai_provider_count", 0),
                )
        except (ValueError, TypeError):
            pass

    raw = await orchestrator.predict(features, match_id, sport=sport)

    preds = raw.get("predictions", {})
    individual = raw.get("individual_results", [])
    attribution = raw.get("attribution", [])

    # Spec §1.4: never substitute a uniform 33/33/34 distribution. If any of
    # the 1x2 probabilities are missing, propagate the failure so the caller
    # can surface a real error instead of a fabricated prediction.
    missing = [k for k in ("home_prob", "draw_prob", "away_prob") if preds.get(k) is None]
    if missing:
        raise ValueError(
            f"Orchestrator returned no value for {missing} — "
            "refusing to fabricate uniform probabilities."
        )

    hp = float(preds["home_prob"])
    dp = float(preds["draw_prob"])
    ap = float(preds["away_prob"])

    # Temperature scaling — global calibration on the final ensemble
    # distribution. T=1.0 (default) is a no-op; values are tuned by
    # `fit_temperature_from_history` and persisted in models/temperature.json.
    scaler = await TemperatureScaler.load()
    hp, dp, ap = scaler.apply(hp, dp, ap)
    preds["home_prob"], preds["draw_prob"], preds["away_prob"] = hp, dp, ap
    if abs(scaler.temperature - 1.0) > 1e-6:
        preds["temperature"] = scaler.temperature

    # Risk score: entropy of final distribution (high entropy = uncertain)
    ent = _entropy(hp, dp, ap)
    max_ent = math.log(3)
    risk_score = round(ent / max_ent, 4)  # 0 = certain, 1 = maximum uncertainty

    # Weights snapshot from live orchestrator
    weights_snapshot = {
        key: meta["weight"]
        for key, meta in orchestrator.model_meta.items()
    }

    pkl_active = sum(1 for v in orchestrator._pkl_loaded.values() if v)

    # Enrich prediction dict
    preds["risk_score"]         = risk_score
    preds["pkl_models_active"]  = pkl_active
    preds["llm_signals_active"] = bool(features.get("ai_signals"))

    audit_id = None
    if db is not None:
        try:
            home_team = features.get("home_team", "")
            away_team = features.get("away_team", "")

            audit = AIPredictionAudit(
                match_id=str(match_id),
                home_team=home_team,
                away_team=away_team,
                home_prob=hp,
                draw_prob=dp,
                away_prob=ap,
                over_25_prob=preds.get("over_25_prob"),
                btts_prob=preds.get("btts_prob"),
                confidence=preds.get("confidence", {}).get("1x2"),
                risk_score=risk_score,
                model_agreement=preds.get("model_agreement"),
                individual_results=individual,
                weights_snapshot=weights_snapshot,
                pkl_models_active=pkl_active,
                triggered_by=triggered_by,
            )
            db.add(audit)
            await db.commit()
            await db.refresh(audit)
            audit_id = audit.id
        except Exception as exc:
            logger.warning(f"[orchestrator] Audit log write failed: {exc}")
            await db.rollback()

    raw["predictions"]  = preds
    raw["audit_id"]     = audit_id
    raw["attribution"]  = attribution
    return raw
