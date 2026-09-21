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

_AI_WEIGHT_BASE = Decimal("0.60")
_VALIDATOR_WEIGHT_BASE = Decimal("0.40")
_ACCURACY_ALPHA = Decimal("0.05")
_DECAY_RATE = Decimal("2.0")
_ACCURACY_THRESHOLD = Decimal("0.15")

# Dynamic weighting: when validators have ≥ MIN_VALIDATORS_FOR_DYNAMIC active
# nodes with sufficient track records, their weight rises up to MAX_VALIDATOR_WEIGHT.
_MIN_VALIDATORS_FOR_DYNAMIC = 3
_MIN_PREDICTIONS_FOR_CLV = 10
_MAX_VALIDATOR_WEIGHT = Decimal("0.65")
_MIN_VALIDATOR_WEIGHT = Decimal("0.15")


def _dynamic_weights(
    validator_count: int,
    avg_trust_score: Decimal,
    avg_accuracy: Decimal,
) -> tuple[Decimal, Decimal]:
    """
    Calculate dynamic AI/validator blend weights based on validator network quality.

    Rules:
      - < MIN_VALIDATORS_FOR_DYNAMIC active validators → pure AI (AI=0.85, V=0.15)
      - High trust + high accuracy → validators earn up to MAX_VALIDATOR_WEIGHT
      - Weight rises linearly with trust_score * accuracy rate
    """
    if validator_count < _MIN_VALIDATORS_FOR_DYNAMIC:
        return Decimal("0.85"), Decimal("0.15")

    # Combined quality signal: trust * accuracy
    quality = avg_trust_score * avg_accuracy
    # Map quality [0, 1] → validator_weight [MIN, MAX]
    val_weight = _MIN_VALIDATOR_WEIGHT + quality * (_MAX_VALIDATOR_WEIGHT - _MIN_VALIDATOR_WEIGHT)
    val_weight = max(_MIN_VALIDATOR_WEIGHT, min(_MAX_VALIDATOR_WEIGHT, val_weight))
    ai_weight = Decimal("1.0") - val_weight
    return ai_weight, val_weight


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
            outcomes = {
                "home": Decimal(str(result.get("home_prob", 0.333))),
                "draw": Decimal(str(result.get("draw_prob", 0.333))),
                "away": Decimal(str(result.get("away_prob", 0.334))),
            }
            return {
                "p_home": Decimal(str(result.get("home_prob", 0.333))),
                "p_draw": Decimal(str(result.get("draw_prob", 0.333))),
                "p_away": outcomes["away"],
                "outcomes": outcomes,
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
    w_outcomes = {}

    for vp, vpr in rows:
        influence = vpr.stake_amount * vpr.trust_score
        total_influence += influence

        # Outcomes from JSON or legacy fields
        outcomes = vp.outcomes or {
            "home": vp.p_home,
            "draw": vp.p_draw,
            "away": vp.p_away
        }
        for name, prob in outcomes.items():
            w_outcomes[name] = w_outcomes.get(name, Decimal("0")) + influence * Decimal(str(prob))

    consensus_outcomes = {}
    if total_influence > 0:
        for name, weight in w_outcomes.items():
            consensus_outcomes[name] = weight / total_influence
    else:
        consensus_outcomes = ai.get("outcomes") or {
            "home": ai["p_home"],
            "draw": ai["p_draw"],
            "away": ai["p_away"]
        }

    # Extract legacy probs for compatibility
    consensus_home = consensus_outcomes.get("home", Decimal("0"))
    consensus_draw = consensus_outcomes.get("draw", Decimal("0"))
    consensus_away = consensus_outcomes.get("away", Decimal("0"))


    # Dynamic weighting: quality of validator pool determines how much weight they get
    if rows:
        avg_trust = sum(vpr.trust_score for _, vpr in rows) / len(rows)
        avg_accuracy = sum(
            Decimal(str(vpr.accurate_predictions / max(vpr.total_predictions, 1)))
            for _, vpr in rows
        ) / len(rows)
    else:
        avg_trust = Decimal("0.5")
        avg_accuracy = Decimal("0.5")

    ai_weight, val_weight = _dynamic_weights(len(rows), avg_trust, avg_accuracy)


    ai_outcomes = ai.get("outcomes") or {
        "home": ai["p_home"],
        "draw": ai["p_draw"],
        "away": ai["p_away"]
    }

    final_outcomes = {}
    all_keys = set(ai_outcomes.keys()) | set(consensus_outcomes.keys())
    for k in all_keys:
        p_ai = Decimal(str(ai_outcomes.get(k, 0)))
        p_val = Decimal(str(consensus_outcomes.get(k, 0)))
        final_outcomes[k] = (ai_weight * p_ai) + (val_weight * p_val)

    # Normalize
    total_norm = sum(final_outcomes.values())
    if total_norm > 0:
        for k in final_outcomes:
            final_outcomes[k] /= total_norm

    final_home = final_outcomes.get("home", Decimal("0"))
    final_draw = final_outcomes.get("draw", Decimal("0"))
    final_away = final_outcomes.get("away", Decimal("0"))


    existing = await db.execute(
        select(ConsensusPrediction).where(ConsensusPrediction.match_id == match_id)
    )
    cp = existing.scalar_one_or_none()


    if cp:
        cp.ai_p_home = ai["p_home"]
        cp.ai_p_draw = ai["p_draw"]
        cp.ai_p_away = ai["p_away"]
        cp.ai_outcomes = ai_outcomes
        cp.ai_confidence = ai["confidence"]
        cp.ai_risk = ai["risk"]
        cp.validator_count = len(rows)
        cp.consensus_p_home = consensus_home
        cp.consensus_p_draw = consensus_draw
        cp.consensus_p_away = consensus_away
        cp.consensus_outcomes = consensus_outcomes
        cp.final_p_home = final_home
        cp.final_p_draw = final_draw
        cp.final_p_away = final_away
        cp.final_outcomes = final_outcomes
        cp.total_influence = total_influence
        if rows:
            cp.category = rows[0].ValidatorPrediction.category
    else:
        cp = ConsensusPrediction(
            match_id=match_id,
            ai_p_home=ai["p_home"],
            ai_p_draw=ai["p_draw"],
            ai_p_away=ai["p_away"],
            ai_outcomes=ai_outcomes,
            ai_confidence=ai["confidence"],
            ai_risk=ai["risk"],
            validator_count=len(rows),
            consensus_p_home=consensus_home,
            consensus_p_draw=consensus_draw,
            consensus_p_away=consensus_away,
            consensus_outcomes=consensus_outcomes,
            final_p_home=final_home,
            final_p_draw=final_draw,
            final_p_away=final_away,
            final_outcomes=final_outcomes,
            total_influence=total_influence,
            status=ConsensusStatus.OPEN.value,
            category=rows[0].ValidatorPrediction.category if rows else "sports"
        )
        db.add(cp)


    await db.flush()
    logger.info(
        f"Consensus for {match_id}: H={float(final_home):.3f} "
        f"D={float(final_draw):.3f} A={float(final_away):.3f} "
        f"(validators={len(rows)}, ai_weight={float(ai_weight):.2f}, val_weight={float(val_weight):.2f})"
    )
    return cp


async def update_trust_scores(match_id: str, oracle_result: str, db: AsyncSession) -> None:
    """
    Update validator trust scores and category-specific reputation after a result is confirmed.
    """
    val_result = await db.execute(
        select(ValidatorPrediction, ValidatorProfile)
        .join(ValidatorProfile, ValidatorPrediction.validator_id == ValidatorProfile.id)
        .where(ValidatorPrediction.match_id == match_id)
    )
    rows = val_result.all()

    for vp, vpr in rows:
        category = vp.category or "sports"

        # Outcomes from JSON or legacy fields
        pred_outcomes = vp.outcomes or {
            "home": vp.p_home,
            "draw": vp.p_draw,
            "away": vp.p_away
        }

        # Deviation from "perfect" prediction (1.0 for the actual result)
        pred_p = Decimal(str(pred_outcomes.get(oracle_result, 0)))
        deviation = Decimal("1") - pred_p

        old_trust = vpr.trust_score
        is_accurate = deviation < _ACCURACY_THRESHOLD

        if is_accurate:
            new_trust = old_trust + (_ACCURACY_ALPHA * (Decimal("1") - old_trust))
            vp.result = PredictionResult.ACCURATE.value
        else:
            decay = Decimal(str(math.exp(float(-_DECAY_RATE * deviation))))
            new_trust = old_trust * decay
            vp.result = PredictionResult.INACCURATE.value

        new_trust = max(Decimal("0.0"), min(Decimal("1.0"), new_trust))
        vp.trust_delta = new_trust - old_trust

        # Global Trust Update
        vpr.trust_score = new_trust
        vpr.total_predictions += 1
        if is_accurate:
            vpr.accurate_predictions += 1

        # Category-Specific Reputation Update
        reputation = dict(vpr.category_reputation or {})
        cat_stats = reputation.get(category, {"trust": 0.5, "accuracy": 0.0, "total": 0})

        c_trust = Decimal(str(cat_stats["trust"]))
        c_total = int(cat_stats["total"])
        c_acc_count = int(c_total * cat_stats["accuracy"])

        if is_accurate:
            c_trust = c_trust + (_ACCURACY_ALPHA * (Decimal("1") - c_trust))
            c_acc_count += 1
        else:
            decay = Decimal(str(math.exp(float(-_DECAY_RATE * deviation))))
            c_trust = c_trust * decay

        c_total += 1
        cat_stats["trust"] = float(max(Decimal("0"), min(Decimal("1"), c_trust)))
        cat_stats["total"] = c_total
        cat_stats["accuracy"] = float(c_acc_count / c_total)

        reputation[category] = cat_stats
        vpr.category_reputation = reputation

        vpr.influence_score = vpr.stake_amount * vpr.trust_score

    await db.flush()
    logger.info(f"Reputation updated for {len(rows)} validators on match {match_id} (result: {oracle_result})")
