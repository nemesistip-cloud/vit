"""Consensus engine — Module C2.

Blends AI predictions (60%) with validator-weighted consensus (40%).
"""

import logging
import math
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    ConsensusPrediction,
    ConsensusStatus,
    ValidatorPrediction,
    ValidatorProfile,
    PredictionResult,
)

logger = logging.getLogger(__name__)

_AI_WEIGHT = Decimal("0.60")
_VALIDATOR_WEIGHT = Decimal("0.40")
_ACCURACY_ALPHA = Decimal("0.05")
_DECAY_RATE = Decimal("2.0")
_ACCURACY_THRESHOLD = Decimal("0.15")


async def _get_ai_prediction(match_id: str) -> Optional[dict]:
    """
    Retrieve AI prediction for this match from the existing prediction system.
    Returns dict with p_home, p_draw, p_away, confidence, risk, or None.
    """
    try:
        from app.core.dependencies import get_orchestrator
        orch = get_orchestrator()
        if not orch:
            return None
        result = orch.predict_from_match_id(match_id)
        if result:
            return {
                "p_home": Decimal(str(result.get("home_prob", 0.333))),
                "p_draw": Decimal(str(result.get("draw_prob", 0.333))),
                "p_away": Decimal(str(result.get("away_prob", 0.334))),
                "confidence": Decimal(str(result.get("confidence", 0.5))),
                "risk": Decimal(str(result.get("risk", 0.5))),
            }
    except Exception as exc:
        logger.debug(f"AI prediction lookup failed for {match_id}: {exc}")
    return None


async def calculate_consensus(match_id: str, db: AsyncSession) -> ConsensusPrediction:
    """
    Calculate (or recalculate) the consensus prediction for a match.

    Steps:
      1. Load AI prediction
      2. Load all ValidatorPredictions
      3. Compute influence-weighted validator consensus
      4. Blend AI (60%) + validators (40%)
      5. Upsert ConsensusPrediction
    """
    ai = await _get_ai_prediction(match_id) or {
        "p_home": Decimal("0.333"),
        "p_draw": Decimal("0.333"),
        "p_away": Decimal("0.334"),
        "confidence": Decimal("0.5"),
        "risk": Decimal("0.5"),
    }

    val_result = await db.execute(
        select(ValidatorPrediction, ValidatorProfile)
        .join(ValidatorProfile, ValidatorPrediction.validator_id == ValidatorProfile.id)
        .where(
            ValidatorPrediction.match_id == match_id,
            ValidatorProfile.status == "active",
        )
    )
    rows = val_result.all()

    total_influence = Decimal("0")
    w_home = Decimal("0")
    w_draw = Decimal("0")
    w_away = Decimal("0")

    for vp, vpr in rows:
        influence = vpr.stake_amount * vpr.trust_score
        total_influence += influence
        w_home += influence * vp.p_home
        w_draw += influence * vp.p_draw
        w_away += influence * vp.p_away

    if total_influence > 0:
        consensus_home = w_home / total_influence
        consensus_draw = w_draw / total_influence
        consensus_away = w_away / total_influence
    else:
        consensus_home = ai["p_home"]
        consensus_draw = ai["p_draw"]
        consensus_away = ai["p_away"]

    final_home = (_AI_WEIGHT * ai["p_home"]) + (_VALIDATOR_WEIGHT * consensus_home)
    final_draw = (_AI_WEIGHT * ai["p_draw"]) + (_VALIDATOR_WEIGHT * consensus_draw)
    final_away = (_AI_WEIGHT * ai["p_away"]) + (_VALIDATOR_WEIGHT * consensus_away)

    total_norm = final_home + final_draw + final_away
    if total_norm > 0:
        final_home /= total_norm
        final_draw /= total_norm
        final_away /= total_norm

    existing = await db.execute(
        select(ConsensusPrediction).where(ConsensusPrediction.match_id == match_id)
    )
    cp = existing.scalar_one_or_none()

    if cp:
        cp.ai_p_home = ai["p_home"]
        cp.ai_p_draw = ai["p_draw"]
        cp.ai_p_away = ai["p_away"]
        cp.ai_confidence = ai["confidence"]
        cp.ai_risk = ai["risk"]
        cp.validator_count = len(rows)
        cp.consensus_p_home = consensus_home
        cp.consensus_p_draw = consensus_draw
        cp.consensus_p_away = consensus_away
        cp.final_p_home = final_home
        cp.final_p_draw = final_draw
        cp.final_p_away = final_away
        cp.total_influence = total_influence
    else:
        cp = ConsensusPrediction(
            match_id=match_id,
            ai_p_home=ai["p_home"],
            ai_p_draw=ai["p_draw"],
            ai_p_away=ai["p_away"],
            ai_confidence=ai["confidence"],
            ai_risk=ai["risk"],
            validator_count=len(rows),
            consensus_p_home=consensus_home,
            consensus_p_draw=consensus_draw,
            consensus_p_away=consensus_away,
            final_p_home=final_home,
            final_p_draw=final_draw,
            final_p_away=final_away,
            total_influence=total_influence,
            status=ConsensusStatus.OPEN.value,
        )
        db.add(cp)

    await db.flush()
    logger.info(
        f"Consensus for {match_id}: H={float(final_home):.3f} "
        f"D={float(final_draw):.3f} A={float(final_away):.3f} "
        f"(validators={len(rows)})"
    )
    return cp


async def update_trust_scores(match_id: str, oracle_result: str, db: AsyncSession) -> None:
    """
    Update validator trust scores after a match result is confirmed.

    For each prediction:
      - If deviation < threshold → accurate, trust increases
      - Otherwise → inaccurate, trust decays exponentially
    """
    outcome_probs = {"home": Decimal("1"), "draw": Decimal("0"), "away": Decimal("0")}
    if oracle_result == "home":
        outcome_probs = {"home": Decimal("1"), "draw": Decimal("0"), "away": Decimal("0")}
    elif oracle_result == "draw":
        outcome_probs = {"home": Decimal("0"), "draw": Decimal("1"), "away": Decimal("0")}
    elif oracle_result == "away":
        outcome_probs = {"home": Decimal("0"), "draw": Decimal("0"), "away": Decimal("1")}

    val_result = await db.execute(
        select(ValidatorPrediction, ValidatorProfile)
        .join(ValidatorProfile, ValidatorPrediction.validator_id == ValidatorProfile.id)
        .where(ValidatorPrediction.match_id == match_id)
    )
    rows = val_result.all()

    for vp, vpr in rows:
        actual_p = outcome_probs.get(oracle_result, Decimal("0"))
        pred_p_map = {"home": vp.p_home, "draw": vp.p_draw, "away": vp.p_away}
        pred_p = pred_p_map.get(oracle_result, Decimal("0"))

        deviation = abs(pred_p - actual_p)

        old_trust = vpr.trust_score
        if deviation < _ACCURACY_THRESHOLD:
            new_trust = old_trust + (_ACCURACY_ALPHA * (Decimal("1") - old_trust))
            vp.result = PredictionResult.ACCURATE.value
        else:
            decay = Decimal(str(math.exp(float(-_DECAY_RATE * deviation))))
            new_trust = old_trust * decay
            vp.result = PredictionResult.INACCURATE.value

        new_trust = max(Decimal("0.0"), min(Decimal("1.0"), new_trust))
        vp.trust_delta = new_trust - old_trust
        vpr.trust_score = new_trust
        vpr.total_predictions += 1
        if vp.result == PredictionResult.ACCURATE.value:
            vpr.accurate_predictions += 1
        vpr.influence_score = vpr.stake_amount * vpr.trust_score

    await db.flush()
    logger.info(f"Trust scores updated for {len(rows)} validators on match {match_id}")
