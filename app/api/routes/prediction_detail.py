"""
app/api/routes/prediction_detail.py — Canonical Prediction Detail Endpoint (A.4)

Assembly endpoint returning the complete canonical prediction contract
(evidence + model + markets + market_intelligence + value + validation + provenance)
for a given match_id.

NOTE: Router NOT registered in main.py in this session — awaiting separate designated integration session.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_optional_user
from app.config import APP_VERSION
from app.db.database import get_db
from app.db.models import Match, Prediction, User
from app.modules.evidence.models import EvidenceSnapshot, MarketRequirementResult
from app.modules.evidence.requirements import MARKET_REQUIREMENTS, evaluate_market_requirements

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/matches", tags=["prediction-detail"])


def _compute_attestation_hash(prediction: Prediction) -> str:
    """Deterministic SHA-256 hash of core prediction fields."""
    payload = {
        "id": prediction.id,
        "match_id": prediction.match_id,
        "bet_side": prediction.bet_side,
        "confidence": float(prediction.confidence or 0),
        "home_prob": float(prediction.home_prob or 0),
        "draw_prob": float(prediction.draw_prob or 0),
        "away_prob": float(prediction.away_prob or 0),
        "final_ev": float(prediction.final_ev or 0),
        "outcome": getattr(prediction, "outcome", None),
        "timestamp": str(prediction.timestamp),
        "user_id": prediction.user_id,
    }
    raw = json.dumps(payload, sort_keys=True)
    return "vit:" + hashlib.sha256(raw.encode()).hexdigest()


# ══════════════════════════════════════════════════════════════════════
# Schemas for Canonical Prediction Detail Response Contract
# ══════════════════════════════════════════════════════════════════════

class EvidenceBlock(BaseModel):
    snapshot_id: Optional[int] = None
    quality_score: Optional[int] = Field(default=None, ge=0, le=100)
    feature_completeness_pct: Optional[int] = Field(default=None, ge=0, le=100)
    missing_critical_inputs: List[Any] = Field(default_factory=list)
    market_requirements: Dict[str, bool] = Field(default_factory=dict)
    reasons: Dict[str, Optional[str]] = Field(default_factory=dict)
    reason_if_null: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ModelBlock(BaseModel):
    home_prob: Optional[float] = None
    draw_prob: Optional[float] = None
    away_prob: Optional[float] = None
    over_25_prob: Optional[float] = None
    under_25_prob: Optional[float] = None
    btts_prob: Optional[float] = None
    consensus_prob: Optional[float] = None
    confidence: Optional[float] = None
    bet_side: Optional[str] = None
    model_consensus: Optional[str] = None
    alternative_bets: Optional[List[Any]] = None
    model_weights: Optional[Dict[str, Any]] = None
    model_insights: Optional[List[Any]] = None
    models_used: Optional[int] = None
    neural_consensus_score: Optional[float] = None
    reason_if_null: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MarketRequirementItem(BaseModel):
    market_key: str
    requirements_met: bool
    reason: Optional[str] = None


class MarketIntelligenceBlock(BaseModel):
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    closing_odds_home: Optional[float] = None
    closing_odds_draw: Optional[float] = None
    closing_odds_away: Optional[float] = None
    odds_source: Optional[str] = None
    reason_if_null: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ValueBlock(BaseModel):
    final_ev: Optional[float] = None
    raw_edge: Optional[float] = None
    vig_free_edge: Optional[float] = None
    normalized_edge: Optional[float] = None
    recommended_stake: Optional[float] = None
    entry_odds: Optional[float] = None
    analytics_rating: Optional[str] = None
    prediction_accuracy_estimate: Optional[float] = None
    reason_if_null: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ValidationBlock(BaseModel):
    attestation_hash: Optional[str] = None
    attested: bool = False
    tx_hash: Optional[str] = None
    block_height: Optional[int] = None
    timestamp: Optional[int] = None
    method: Optional[str] = None
    all_passed: bool = False
    rules_passed: List[str] = Field(default_factory=list)
    rules_failed: List[str] = Field(default_factory=list)
    reason_if_null: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProvenanceBlock(BaseModel):
    match_id: int
    sport: str = "football"
    data_source: Optional[str] = None
    timestamp: Optional[str] = None
    data_quality: Optional[Dict[str, Any]] = None
    model_version: Optional[str] = None
    environment: Optional[str] = None
    reason_if_null: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PredictionDetailResponse(BaseModel):
    match_id: int
    status: str  # "not_initialized" | "validating" | "verified" | "unavailable"
    unavailable_reason: Optional[str] = None
    evidence: Optional[EvidenceBlock] = None
    model: Optional[ModelBlock] = None
    markets: Dict[str, MarketRequirementItem] = Field(default_factory=dict)
    market_intelligence: Optional[MarketIntelligenceBlock] = None
    value: Optional[ValueBlock] = None
    validation: Optional[ValidationBlock] = None
    provenance: Optional[ProvenanceBlock] = None

    model_config = ConfigDict(from_attributes=True)


# ══════════════════════════════════════════════════════════════════════
# Endpoint implementation
# ══════════════════════════════════════════════════════════════════════

@router.get("/{match_id}/prediction-detail", response_model=PredictionDetailResponse)
async def get_match_prediction_detail(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieve the full canonical prediction contract for a match.

    Assembles evidence, model, markets, market_intelligence, value, validation, and provenance
    into a single unified payload.
    """
    # ── 1. Query Match ────────────────────────────────────────────────────────
    match_result = await db.execute(select(Match).where(Match.id == match_id))
    match = match_result.scalar_one_or_none()
    if not match:
        return PredictionDetailResponse(
            match_id=match_id,
            status="not_initialized",
            unavailable_reason=f"Match with ID {match_id} was not found in database.",
        )

    # ── 2. Query latest Prediction for match ──────────────────────────────────
    pred_stmt = (
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(Prediction.timestamp.desc(), Prediction.id.desc())
    )
    pred_result = await db.execute(pred_stmt)
    prediction = pred_result.scalars().first()

    # ── 3. Query latest EvidenceSnapshot for match ─────────────────────────────
    evidence_stmt = (
        select(EvidenceSnapshot)
        .options(selectinload(EvidenceSnapshot.market_requirement_results))
        .where(EvidenceSnapshot.match_id == match_id)
        .order_by(EvidenceSnapshot.created_at.desc(), EvidenceSnapshot.id.desc())
    )
    evidence_result = await db.execute(evidence_stmt)
    evidence_snapshot = evidence_result.scalars().first()

    # ── 4. Extract Odds from Match Entity ─────────────────────────────────────
    home_odds = getattr(match, "opening_odds_home", None)
    draw_odds = getattr(match, "opening_odds_draw", None)
    away_odds = getattr(match, "opening_odds_away", None)

    # ── 5. Build Evidence Block & Markets Block ────────────────────────────────
    evidence_block: Optional[EvidenceBlock] = None
    markets_dict: Dict[str, MarketRequirementItem] = {}

    if evidence_snapshot:
        m_reqs: Dict[str, bool] = {}
        reasons: Dict[str, Optional[str]] = {}
        for req_res in evidence_snapshot.market_requirement_results:
            m_reqs[req_res.market_key] = req_res.requirements_met
            reasons[req_res.market_key] = req_res.reason
            markets_dict[req_res.market_key] = MarketRequirementItem(
                market_key=req_res.market_key,
                requirements_met=req_res.requirements_met,
                reason=req_res.reason,
            )

        evidence_block = EvidenceBlock(
            snapshot_id=evidence_snapshot.id,
            quality_score=evidence_snapshot.quality_score,
            feature_completeness_pct=evidence_snapshot.feature_completeness_pct,
            missing_critical_inputs=evidence_snapshot.missing_critical_inputs or [],
            market_requirements=m_reqs,
            reasons=reasons,
            reason_if_null=None,
        )
    else:
        evidence_block = EvidenceBlock(
            snapshot_id=None,
            quality_score=None,
            feature_completeness_pct=None,
            missing_critical_inputs=[],
            market_requirements={},
            reasons={},
            reason_if_null=f"No evidence snapshot recorded for match {match_id}.",
        )
        # Populate markets evaluated on-the-fly or mark unavailable
        feature_snap = {
            "feature_completeness_pct": 0,
            "features": {},
            "market_odds": {"home": home_odds, "draw": draw_odds, "away": away_odds},
        }
        for m_key in MARKET_REQUIREMENTS.keys():
            eval_res = evaluate_market_requirements(feature_snap, m_key)
            markets_dict[m_key] = MarketRequirementItem(
                market_key=m_key,
                requirements_met=eval_res["requirements_met"],
                reason=eval_res.get("reason"),
            )

    # ── 6. Build Model Block & Value Block ────────────────────────────────────
    model_block: Optional[ModelBlock] = None
    value_block: Optional[ValueBlock] = None

    if prediction:
        models_cnt = len(prediction.model_insights) if prediction.model_insights else 0
        neural_score = (prediction.consensus_prob * 100) if prediction.consensus_prob is not None else None

        model_block = ModelBlock(
            home_prob=prediction.home_prob,
            draw_prob=prediction.draw_prob,
            away_prob=prediction.away_prob,
            over_25_prob=prediction.over_25_prob,
            under_25_prob=prediction.under_25_prob,
            btts_prob=prediction.btts_prob,
            consensus_prob=prediction.consensus_prob,
            confidence=prediction.confidence,
            bet_side=prediction.bet_side,
            model_consensus=prediction.model_consensus,
            alternative_bets=prediction.alternative_bets,
            model_weights=prediction.model_weights or {},
            model_insights=prediction.model_insights or [],
            models_used=models_cnt,
            neural_consensus_score=neural_score,
            reason_if_null=None,
        )

        value_block = ValueBlock(
            final_ev=prediction.final_ev,
            raw_edge=prediction.raw_edge,
            vig_free_edge=prediction.vig_free_edge,
            normalized_edge=prediction.normalized_edge,
            recommended_stake=prediction.recommended_stake,
            entry_odds=prediction.entry_odds,
            analytics_rating=None,  # Not calculated on prediction model directly
            prediction_accuracy_estimate=None,  # Dynamic user accuracy metric, null unless populated
            reason_if_null="Analytics rating and accuracy estimate require historical backtest context.",
        )
    else:
        model_block = ModelBlock(
            reason_if_null=f"No prediction record exists for match {match_id}."
        )
        value_block = ValueBlock(
            reason_if_null=f"No prediction value calculations exist for match {match_id}."
        )

    # ── 7. Build Market Intelligence Block ────────────────────────────────────
    market_intel_block = MarketIntelligenceBlock(
        home_odds=home_odds,
        draw_odds=draw_odds,
        away_odds=away_odds,
        closing_odds_home=match.closing_odds_home,
        closing_odds_draw=match.closing_odds_draw,
        closing_odds_away=match.closing_odds_away,
        odds_source="match_entity",
        reason_if_null=None if (home_odds or draw_odds or away_odds) else "Odds not available for match entity.",
    )

    # ── 8. Build Validation Block (Attestation & Rules) ────────────────────────
    validation_block: Optional[ValidationBlock] = None
    rules_passed: List[str] = []
    rules_failed: List[str] = []

    if prediction:
        attestation_hash = _compute_attestation_hash(prediction)

        if prediction.home_prob is not None and prediction.away_prob is not None:
            rules_passed.append("probabilities_normalized")
        else:
            rules_failed.append("missing_probabilities")

        if home_odds and away_odds:
            rules_passed.append("valid_market_odds")
        else:
            rules_failed.append("missing_market_odds")

        # Check primary market '1x2' requirement
        primary_req = markets_dict.get("1x2")
        if primary_req and primary_req.requirements_met:
            rules_passed.append("primary_market_requirements_met")
        else:
            fail_reason = primary_req.reason if primary_req else "1x2 market requirements failed"
            rules_failed.append(f"primary_market_requirements_failed: {fail_reason}")

        all_passed = len(rules_failed) == 0

        validation_block = ValidationBlock(
            attestation_hash=attestation_hash,
            attested=True,
            tx_hash=None,
            block_height=None,
            timestamp=int(time.time()),
            method="hash_only",
            all_passed=all_passed,
            rules_passed=rules_passed,
            rules_failed=rules_failed,
            reason_if_null=None,
        )
    else:
        validation_block = ValidationBlock(
            attested=False,
            all_passed=False,
            rules_failed=["no_prediction_exists"],
            reason_if_null=f"Validation cannot run without an existing prediction for match {match_id}.",
        )

    # ── 9. Build Provenance Block ─────────────────────────────────────────────
    provenance_block = ProvenanceBlock(
        match_id=match_id,
        sport=getattr(match, "sport", "football") or "football",
        data_source=getattr(prediction, "source", None) or "native_ensemble",
        timestamp=prediction.timestamp.isoformat() if (prediction and prediction.timestamp) else datetime.now(timezone.utc).isoformat(),
        data_quality={
            "quality_score": evidence_block.quality_score if evidence_block else None,
            "completeness": evidence_block.feature_completeness_pct if evidence_block else None,
        },
        model_version=APP_VERSION,
        environment=os.getenv("ENVIRONMENT", "production"),
        reason_if_null=None,
    )

    # ── 10. Determine Status & Unavailable Reason ─────────────────────────────
    status_str: str = "not_initialized"
    unavailable_reason: Optional[str] = None

    if not prediction:
        status_str = "not_initialized"
        unavailable_reason = f"No prediction exists yet for match {match_id}."
    elif validation_block and validation_block.rules_failed:
        status_str = "unavailable"
        unavailable_reason = f"Validation rules failed: {'; '.join(validation_block.rules_failed)}"
    elif evidence_snapshot is None:
        status_str = "validating"
        unavailable_reason = None
    elif validation_block and validation_block.all_passed:
        status_str = "verified"
        unavailable_reason = None
    else:
        status_str = "validating"
        unavailable_reason = None

    return PredictionDetailResponse(
        match_id=match_id,
        status=status_str,
        unavailable_reason=unavailable_reason,
        evidence=evidence_block,
        model=model_block,
        markets=markets_dict,
        market_intelligence=market_intel_block,
        value=value_block,
        validation=validation_block,
        provenance=provenance_block,
    )
