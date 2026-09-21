"""
VIT Network — Recommendation Engine (Phase B)

Provides market-aware prediction recommendations, composite signal scoring,
ensemble model consensus metrics, probability calibration analysis,
state qualification (QUALIFIED_SIGNAL / NO_SIGNAL / etc.), and
historical signal tracking.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.calibration import CalibratorRegistry
from app.db.models import Match, Prediction, AISignalCache, AIPrediction, Market

logger = logging.getLogger(__name__)

# ── Signal Qualification States ───────────────────────────────────────────────
STATE_QUALIFIED_SIGNAL = "QUALIFIED_SIGNAL"
STATE_LOW_CONFIDENCE   = "LOW_CONFIDENCE"
STATE_HIGH_DISAGREEMENT = "HIGH_DISAGREEMENT"
STATE_DATA_DEFICIENT   = "DATA_DEFICIENT"
STATE_NO_SIGNAL        = "NO_SIGNAL"

# Default thresholds
MIN_QUALIFIED_EDGE = 0.02       # 2% vig-free edge
MIN_QUALIFIED_CONF = 0.55       # 55% model confidence
MIN_AGREEMENT_PCT  = 0.50       # 50% model agreement
MIN_FEATURE_COMPLETENESS = 0.30 # 30% feature completeness


def _entropy_confidence(probs: List[float]) -> float:
    """Derive entropy-based confidence score in range [0.50, 0.95]."""
    valid = [p for p in probs if p > 0]
    if not valid:
        return 0.50
    k = len(valid)
    if k <= 1:
        return 0.95
    ent = -sum(p * math.log(p) for p in valid)
    max_ent = math.log(k)
    normalised = max(0.0, min(1.0, 1.0 - (ent / max_ent)))
    return round(0.50 + normalised * 0.45, 3)


def compute_signal_score(
    vig_free_edge: float,
    agreement_pct: float,
    confidence: float,
    calibration_applied: bool,
    feature_completeness: float = 1.0,
    has_odds: bool = True,
) -> float:
    """
    Compute a composite signal score from 0.0 to 100.0.

    Components:
      * Edge (0-35 pts): scaled up to 10%+ edge
      * Consensus (0-30 pts): model agreement share
      * Confidence (0-20 pts): entropy-derived model confidence
      * Calibration (0-10 pts): bonus for calibrated models
      * Completeness (0-5 pts): feature richness bonus
    """
    if not has_odds:
        return 0.0

    edge_score = min(max(vig_free_edge, 0.0) / 0.10, 1.0) * 35.0
    consensus_score = min(max(agreement_pct, 0.0), 1.0) * 30.0
    conf_score = min(max((confidence - 0.50) / 0.45, 0.0), 1.0) * 20.0
    calib_score = 10.0 if calibration_applied else 3.0
    completeness_score = min(max(feature_completeness, 0.0), 1.0) * 5.0

    raw_total = edge_score + consensus_score + conf_score + calib_score + completeness_score
    return round(min(100.0, max(0.0, raw_total)), 1)


def classify_signal_state(
    signal_score: float,
    vig_free_edge: float,
    agreement_pct: float,
    confidence: float,
    disagreement_score: float,
    feature_completeness: float,
    has_odds: bool = True,
) -> str:
    """
    Classify the recommendation into an explicit signal state.
    """
    if not has_odds or feature_completeness < MIN_FEATURE_COMPLETENESS:
        return STATE_DATA_DEFICIENT

    if disagreement_score > 0.08 or agreement_pct < 0.40:
        return STATE_HIGH_DISAGREEMENT

    if vig_free_edge < 0.015 or signal_score < 35.0:
        return STATE_NO_SIGNAL

    if confidence < MIN_QUALIFIED_CONF or agreement_pct < MIN_AGREEMENT_PCT:
        return STATE_LOW_CONFIDENCE

    if vig_free_edge >= MIN_QUALIFIED_EDGE and signal_score >= 50.0:
        return STATE_QUALIFIED_SIGNAL

    return STATE_LOW_CONFIDENCE


class RecommendationEngine:
    """
    Core Recommendation & Signal Evaluation Engine.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.calibrator = CalibratorRegistry.get()

    def evaluate_model_consensus(
        self,
        individual_results: List[Dict[str, Any]],
        total_models: int = 13,
    ) -> Dict[str, Any]:
        """
        Compute vote share distribution, leader pick, agreement percentage,
        and disagreement variance across individual ensemble model predictions.
        """
        if not individual_results:
            return {
                "leader": "home",
                "home_pct": 33.3,
                "draw_pct": 33.3,
                "away_pct": 33.4,
                "votes": {"home": 0, "draw": 0, "away": 0},
                "agreement_pct": 0.333,
                "disagreement_score": 0.0,
                "models_polled": 0,
                "total_models": total_models,
            }

        votes = {"home": 0, "draw": 0, "away": 0}
        probs_home: List[float] = []
        probs_draw: List[float] = []
        probs_away: List[float] = []

        valid_models = 0
        for m in individual_results:
            if m.get("failed"):
                continue
            hp = float(m.get("home_prob") or 0.333)
            dp = float(m.get("draw_prob") or 0.333)
            ap = float(m.get("away_prob") or 0.334)

            probs_home.append(hp)
            probs_draw.append(dp)
            probs_away.append(ap)

            side = max((("home", hp), ("draw", dp), ("away", ap)), key=lambda x: x[1])[0]
            votes[side] += 1
            valid_models += 1

        if valid_models == 0:
            return {
                "leader": "home",
                "home_pct": 33.3,
                "draw_pct": 33.3,
                "away_pct": 33.4,
                "votes": votes,
                "agreement_pct": 0.333,
                "disagreement_score": 0.0,
                "models_polled": 0,
                "total_models": total_models,
            }

        leader_side = max(votes.keys(), key=lambda k: votes[k])
        max_votes = votes[leader_side]
        agreement_pct = round(max_votes / valid_models, 3)

        # Disagreement variance calculation across home prob predictions
        mean_home = sum(probs_home) / valid_models
        var_home = sum((p - mean_home) ** 2 for p in probs_home) / valid_models
        disagreement_score = round(var_home, 4)

        return {
            "leader": leader_side,
            "home_pct": round((votes["home"] / valid_models) * 100, 1),
            "draw_pct": round((votes["draw"] / valid_models) * 100, 1),
            "away_pct": round((votes["away"] / valid_models) * 100, 1),
            "votes": votes,
            "agreement_pct": agreement_pct,
            "disagreement_score": disagreement_score,
            "models_polled": valid_models,
            "total_models": total_models,
        }

    def evaluate_calibration(
        self,
        individual_results: List[Dict[str, Any]],
        method: str = "isotonic",
    ) -> Dict[str, Any]:
        """
        Evaluate and apply probability calibration across individual models.
        """
        calibrated_models = []
        uncalibrated_models = []
        partial_models = []

        total_applied = 0
        for m in individual_results:
            model_name = m.get("model_name") or "unknown"
            hp = float(m.get("home_prob") or 0.333)
            dp = float(m.get("draw_prob") or 0.333)
            ap = float(m.get("away_prob") or 0.334)

            cal_probs, meta = self.calibrator.apply(model_name, hp, dp, ap, method=method)
            m["calibrated_home_prob"] = cal_probs[0]
            m["calibrated_draw_prob"] = cal_probs[1]
            m["calibrated_away_prob"] = cal_probs[2]
            m["calibration_meta"] = meta

            if meta.get("applied"):
                total_applied += 1
                if meta.get("partial"):
                    partial_models.append(model_name)
                else:
                    calibrated_models.append(model_name)
            else:
                uncalibrated_models.append(model_name)

        return {
            "method": method,
            "calibrated_count": total_applied,
            "uncalibrated_count": len(uncalibrated_models),
            "calibrated_models": calibrated_models,
            "uncalibrated_models": uncalibrated_models,
            "partial_models": partial_models,
            "is_calibrated": total_applied > 0,
        }

    def generate_recommendation(
        self,
        match_id: Optional[int],
        home_team: str,
        away_team: str,
        market_type: str = "sports",
        category: str = "football",
        home_prob: float = 0.333,
        draw_prob: float = 0.333,
        away_prob: float = 0.334,
        market_odds: Optional[Dict[str, float]] = None,
        individual_results: Optional[List[Dict[str, Any]]] = None,
        feature_completeness: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive, market-aware recommendation object with signal scoring,
        consensus evaluation, calibration status, and qualification state.
        """
        odds = market_odds or {}
        has_odds = bool(odds.get("home") and odds.get("away"))

        # 1. Evaluate Model Consensus
        consensus = self.evaluate_model_consensus(
            individual_results or [],
            total_models=13,
        )

        # 2. Evaluate Calibration
        calib_meta = self.evaluate_calibration(
            individual_results or [],
            method="isotonic",
        )

        # 3. Derive Edge and EV
        home_o = float(odds.get("home") or 2.5)
        draw_o = float(odds.get("draw") or 3.2)
        away_o = float(odds.get("away") or 2.8)

        # Determine best side & implied probabilities
        probs = {"home": home_prob, "draw": draw_prob, "away": away_prob}
        best_side = max(probs.keys(), key=lambda k: probs[k])
        best_prob = probs[best_side]

        chosen_odds = home_o if best_side == "home" else (draw_o if best_side == "draw" else away_o)
        implied_prob = (1.0 / chosen_odds) if chosen_odds > 1.0 else 0.5
        vig_free_edge = round(best_prob - implied_prob, 4)

        # 4. Confidence & Signal Score
        conf = _entropy_confidence([home_prob, draw_prob, away_prob])
        signal_score = compute_signal_score(
            vig_free_edge=vig_free_edge,
            agreement_pct=consensus["agreement_pct"],
            confidence=conf,
            calibration_applied=calib_meta["is_calibrated"],
            feature_completeness=feature_completeness,
            has_odds=has_odds,
        )

        # 5. Qualification State
        signal_state = classify_signal_state(
            signal_score=signal_score,
            vig_free_edge=vig_free_edge,
            agreement_pct=consensus["agreement_pct"],
            confidence=conf,
            disagreement_score=consensus["disagreement_score"],
            feature_completeness=feature_completeness,
            has_odds=has_odds,
        )

        # 6. Execution Pathway (Market-Aware)
        is_sports = market_type.lower() == "sports"
        execution_path = {
            "market_type": market_type,
            "category": category,
            "wallet_required": not is_sports,
            "action": "view_analysis_and_redirect" if is_sports else "on_chain_stake",
            "redirect_supported": is_sports,
            "settlement_type": "affiliate_external" if is_sports else "oracle_smart_contract",
        }

        # 7. Construct Recommendation Payload
        recommendation = {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "market_type": market_type,
            "category": category,
            "best_selection": {
                "side": best_side,
                "label": home_team if best_side == "home" else (away_team if best_side == "away" else "Draw"),
                "model_prob": round(best_prob, 4),
                "odds": chosen_odds,
                "vig_free_edge": vig_free_edge,
            },
            "signal_metrics": {
                "signal_score": signal_score,
                "signal_state": signal_state,
                "confidence": conf,
                "feature_completeness": round(feature_completeness, 3),
            },
            "model_consensus": consensus,
            "calibration": calib_meta,
            "execution_path": execution_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return recommendation

    async def save_signal_history(
        self,
        match_id: int,
        recommendation: Dict[str, Any],
    ) -> Optional[AISignalCache]:
        """
        Persist or update the signal cache in the database for historical signal tracking.
        """
        if not self.db:
            logger.warning("save_signal_history skipped — no DB session provided")
            return None

        try:
            consensus = recommendation["model_consensus"]
            sig_metrics = recommendation["signal_metrics"]
            best_sel = recommendation["best_selection"]

            result = await self.db.execute(
                select(AISignalCache).where(AISignalCache.match_id == match_id)
            )
            cache = result.scalar_one_or_none()

            probs = recommendation.get("probabilities", {})
            hp = probs.get("home", 0.333)
            dp = probs.get("draw", 0.333)
            ap = probs.get("away", 0.334)

            if not cache:
                cache = AISignalCache(
                    match_id=match_id,
                    consensus_home=hp,
                    consensus_draw=dp,
                    consensus_away=ap,
                    disagreement_score=consensus["disagreement_score"],
                    max_confidence=sig_metrics["confidence"],
                    weighted_home=hp,
                    weighted_draw=dp,
                    weighted_away=ap,
                    per_ai_predictions={
                        "signal_score": sig_metrics["signal_score"],
                        "signal_state": sig_metrics["signal_state"],
                        "best_side": best_sel["side"],
                        "vig_free_edge": best_sel["vig_free_edge"],
                        "market_type": recommendation["market_type"],
                        "category": recommendation["category"],
                        "calibration": recommendation["calibration"],
                    },
                )
                self.db.add(cache)
            else:
                cache.consensus_home = hp
                cache.consensus_draw = dp
                cache.consensus_away = ap
                cache.disagreement_score = consensus["disagreement_score"]
                cache.max_confidence = sig_metrics["confidence"]
                cache.per_ai_predictions = {
                    "signal_score": sig_metrics["signal_score"],
                    "signal_state": sig_metrics["signal_state"],
                    "best_side": best_sel["side"],
                    "vig_free_edge": best_sel["vig_free_edge"],
                    "market_type": recommendation["market_type"],
                    "category": recommendation["category"],
                    "calibration": recommendation["calibration"],
                }

            await self.db.commit()
            await self.db.refresh(cache)
            return cache
        except Exception as e:
            logger.error("Failed to save signal history for match %s: %s", match_id, e)
            await self.db.rollback()
            return None

    async def get_historical_signals(
        self,
        signal_state: Optional[str] = None,
        market_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Query historical signals from the database for performance auditing and tracking.
        """
        if not self.db:
            return []

        try:
            stmt = select(AISignalCache, Match).join(Match, Match.id == AISignalCache.match_id).order_by(desc(AISignalCache.timestamp)).limit(limit)
            results = (await self.db.execute(stmt)).all()

            signals = []
            for cache, match in results:
                meta = cache.per_ai_predictions or {}
                st = meta.get("signal_state", STATE_QUALIFIED_SIGNAL)
                mt = meta.get("market_type", "sports")

                if signal_state and st != signal_state:
                    continue
                if market_type and mt != market_type:
                    continue

                signals.append({
                    "cache_id": cache.id,
                    "match_id": cache.match_id,
                    "home_team": match.home_team,
                    "away_team": match.away_team,
                    "league": match.league,
                    "market_type": mt,
                    "category": meta.get("category", match.sport),
                    "signal_score": meta.get("signal_score", 50.0),
                    "signal_state": st,
                    "best_side": meta.get("best_side", "home"),
                    "vig_free_edge": meta.get("vig_free_edge", 0.0),
                    "disagreement_score": cache.disagreement_score,
                    "max_confidence": cache.max_confidence,
                    "settled": match.actual_outcome is not None,
                    "actual_outcome": match.actual_outcome,
                    "timestamp": cache.timestamp.isoformat() if cache.timestamp else None,
                })

            return signals
        except Exception as e:
            logger.error("Failed to fetch historical signals: %s", e)
            return []
