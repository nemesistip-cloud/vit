"""
app/modules/evidence/service.py — Evidence evaluation service logic.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_env
from app.core.errors import AppError
from app.modules.evidence.models import EvidenceSnapshot, MarketRequirementResult
from app.modules.evidence.requirements import evaluate_market_requirements

logger = logging.getLogger(__name__)


def _parse_float_env(key: str, default: float) -> float:
    val_str = get_env(key, str(default))
    try:
        return float(val_str)
    except ValueError:
        logger.warning(
            "Invalid float for env key '%s': '%s'. Using default %f",
            key, val_str, default
        )
        return default


def compute_quality_score(
    feature_completeness_pct: int,
    provider_freshness_score: int,
    provider_disagreement_penalty: int,
    missing_critical_inputs: List[Any],
) -> int:
    """
    Computes quality score (0–100) using configurable weights.

    Weights MUST be read via get_env()/PlatformConfig, never hardcoded.
    Default weights:
      - w_feature = 0.4
      - w_freshness = 0.3
      - w_disagreement = 0.2
      - w_missing = 0.1
    """
    w_feature = _parse_float_env("EVIDENCE_WEIGHT_FEATURE", 0.4)
    w_freshness = _parse_float_env("EVIDENCE_WEIGHT_FRESHNESS", 0.3)
    w_disagreement = _parse_float_env("EVIDENCE_WEIGHT_DISAGREEMENT", 0.2)
    w_missing = _parse_float_env("EVIDENCE_WEIGHT_MISSING", 0.1)

    missing_count = len(missing_critical_inputs) if missing_critical_inputs else 0
    missing_score = max(0, 100 - (missing_count * 25))

    disagreement_score = max(0, 100 - provider_disagreement_penalty)

    completeness_score = max(0, min(100, feature_completeness_pct))
    freshness_score = max(0, min(100, provider_freshness_score))

    raw_score = (
        (completeness_score * w_feature)
        + (freshness_score * w_freshness)
        + (disagreement_score * w_disagreement)
        + (missing_score * w_missing)
    )

    return max(0, min(100, int(round(raw_score))))


async def create_evidence_snapshot(
    db: AsyncSession,
    match_id: int,
    feature_completeness_pct: int,
    provider_data: Dict[str, Any],
    provider_freshness_score: int = 100,
    provider_disagreement_penalty: int = 0,
    missing_critical_inputs: Optional[List[Any]] = None,
    market_keys_to_evaluate: Optional[List[str]] = None,
) -> EvidenceSnapshot:
    """
    Creates an EvidenceSnapshot and evaluates requirements for requested market_keys.

    Must use `async with db.begin()` for the write.
    """
    if match_id <= 0:
        raise AppError("Invalid match_id", status_code=400, code="invalid_match_id")

    missing_inputs = missing_critical_inputs or []
    quality_score = compute_quality_score(
        feature_completeness_pct=feature_completeness_pct,
        provider_freshness_score=provider_freshness_score,
        provider_disagreement_penalty=provider_disagreement_penalty,
        missing_critical_inputs=missing_inputs,
    )

    market_evaluations = []
    if market_keys_to_evaluate:
        feature_snapshot = {
            "feature_completeness_pct": feature_completeness_pct,
            "features": provider_data.get("features", provider_data),
            "market_odds": provider_data.get("market_odds"),
        }
        for market_key in market_keys_to_evaluate:
            eval_res = evaluate_market_requirements(feature_snapshot, market_key)
            market_evaluations.append((market_key, eval_res))

    async with db.begin():
        snapshot = EvidenceSnapshot(
            match_id=match_id,
            feature_completeness_pct=feature_completeness_pct,
            provider_data=provider_data,
            quality_score=quality_score,
            missing_critical_inputs=missing_inputs,
        )

        for market_key, eval_res in market_evaluations:
            req_result = MarketRequirementResult(
                market_key=market_key,
                requirements_met=eval_res["requirements_met"],
                reason=eval_res.get("reason"),
            )
            snapshot.market_requirement_results.append(req_result)

        db.add(snapshot)

    return snapshot
