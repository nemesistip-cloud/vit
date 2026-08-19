import logging
import math
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.schemas.schemas import PredictionResponse, ModelInsight

logger = logging.getLogger(__name__)

def _poisson_over25(lambda_total: float) -> float:
    """P(total goals > 2.5) using Poisson(lambda_total)."""
    p_under = math.exp(-lambda_total) * (
        1 + lambda_total + (lambda_total ** 2) / 2.0
    )
    return round(max(0.01, min(0.99, 1.0 - p_under)), 4)

def _poisson_btts(lambda_home: float, lambda_away: float) -> float:
    """P(both teams score) = P(home>=1) * P(away>=1) via Poisson."""
    p_home_scores = 1.0 - math.exp(-lambda_home)
    p_away_scores = 1.0 - math.exp(-lambda_away)
    return round(max(0.01, min(0.99, p_home_scores * p_away_scores)), 4)

def _implied_lambda(prob: float, fallback: float) -> float:
    """Approximate Poisson λ from a team win probability (rough proxy for scoring rate)."""
    p = max(0.05, min(0.90, prob))
    return max(0.5, -math.log(1.0 - p) * 1.8 + fallback * 0.3)

class MultiSportOrchestrator:
    """
    Enhanced orchestrator to handle non-football sports with dynamic logic.
    Provides a unified interface for all sports while supporting specialized models.
    Supports 'Hybrid Mode' (ML + SCIE Fallback).
    All probability outputs are derived deterministically from market odds/priors —
    no random stubs.
    """

    def __init__(self, football_orchestrator=None):
        self.football_orchestrator = football_orchestrator
        self.use_real_ml = os.getenv("USE_REAL_ML_MODELS", "false").lower() == "true"

    async def predict(self, features: Dict[str, Any], idempotency_key: str = None, sport: str = "football") -> Dict[str, Any]:
        """Dispatch prediction request to the appropriate engine based on sport."""
        sport = (sport or "football").lower()

        if sport == "football":
            return await self._predict_football(features, idempotency_key)
        elif sport == "basketball":
            return self._predict_basketball(features)
        elif sport == "tennis":
            return self._predict_tennis(features)
        else:
            return self._generate_base_prediction(features, sport)

    async def _predict_football(self, features: Dict[str, Any], idempotency_key: str = None) -> Dict[str, Any]:
        """Hybrid football prediction: ML Ensemble with SCIE Fallback."""
        if self.football_orchestrator and self.use_real_ml:
            try:
                if self.football_orchestrator.num_models_ready() > 0:
                    if asyncio.iscoroutinefunction(self.football_orchestrator.predict_ensemble):
                        return await self.football_orchestrator.predict_ensemble(features)
                    else:
                        return self.football_orchestrator.predict_ensemble(features)
                else:
                    logger.info("[orchestrator] ML models not ready, falling back to SCIE")
            except Exception as e:
                logger.error(f"[orchestrator] ML Ensemble failed: {e}")

        return self._generate_scie_football(features)

    def _generate_scie_football(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """High-fidelity statistical fallback for football — fully deterministic."""
        mkt = features.get("market_odds", {})
        odds = {
            side: mkt.get(side) if isinstance(mkt, dict) else None
            for side in ("home", "draw", "away")
        }
        has_valid_market = all(
            isinstance(value, (int, float)) and math.isfinite(value) and value > 1.0
            for value in odds.values()
        )
        if has_valid_market:
            h, d, a = (float(odds[side]) for side in ("home", "draw", "away"))
            confidence_1x2 = 0.68
            data_source = "vit_scie_v5_fallback"
        else:
            # Missing odds must not silently encode a home advantage. Use a
            # neutral prior and publish lower confidence until real inputs exist.
            h = d = a = 3.0
            confidence_1x2 = 0.34
            data_source = "vit_scie_v5_neutral_fallback"

        total_implied = (1/h) + (1/d) + (1/a)
        hp, dp, ap = (1/h)/total_implied, (1/d)/total_implied, (1/a)/total_implied
        hp, dp, ap = self._normalise(hp, dp, ap)

        # Derive Poisson λ values from vig-free win probabilities
        lambda_home = _implied_lambda(hp, 1.45)
        lambda_away = _implied_lambda(ap, 1.15)
        lambda_total = lambda_home + lambda_away

        over25 = _poisson_over25(lambda_total)
        under25 = round(1.0 - over25, 4)
        btts = _poisson_btts(lambda_home, lambda_away)

        return {
            "predictions": {
                "home_prob": round(hp, 4),
                "draw_prob": round(dp, 4),
                "away_prob": round(ap, 4),
                "over_25_prob": over25,
                "over_2_5_prob": over25,
                "under_25_prob": under25,
                "btts_prob": btts,
                "confidence": {"1x2": confidence_1x2, "over_under": 0.65 if has_valid_market else 0.40},
                "models_used": 0,
                "models_total": 13,
                "data_source": data_source
            },
            "individual_results": [],
            "scie_mode": True
        }

    def _predict_basketball(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Market-derived basketball prediction — no random stubs."""
        mkt = features.get("market_odds", {})
        h_odds = float(mkt.get("home", 1.9))
        a_odds = float(mkt.get("away", 1.9))

        total_implied = (1/h_odds) + (1/a_odds)
        h_prob = round((1/h_odds) / total_implied, 4)
        a_prob = round(1.0 - h_prob, 4)

        # Basketball almost always exceeds 2.5 total points — use 95% as baseline,
        # nudged by match competitiveness (closer game → slightly lower scoring pace).
        balance = 1.0 - abs(h_prob - a_prob)
        over_total = round(min(0.97, 0.93 + balance * 0.03), 4)

        return {
            "predictions": {
                "home_prob": h_prob,
                "draw_prob": 0.0,
                "away_prob": a_prob,
                "over_25_prob": over_total,
                "btts_prob": 0.0,
                "confidence": {"moneyline": 0.75},
                "models_used": 2,
                "models_total": 13,
                "data_source": "basketball_scie_v2"
            },
            "individual_results": []
        }

    def _predict_tennis(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Market-derived tennis prediction — no random stubs."""
        mkt = features.get("market_odds", {})
        h_odds = float(mkt.get("home", 1.8))
        a_odds = float(mkt.get("away", 2.0))

        total_implied = (1/h_odds) + (1/a_odds)
        h_prob = round((1/h_odds) / total_implied, 4)
        a_prob = round(1.0 - h_prob, 4)

        return {
            "predictions": {
                "home_prob": h_prob,
                "draw_prob": 0.0,
                "away_prob": a_prob,
                "over_25_prob": 0.0,
                "btts_prob": 0.0,
                "confidence": {"winner": 0.8},
                "models_used": 1,
                "models_total": 13,
                "data_source": "tennis_scie_v2"
            },
            "individual_results": []
        }

    def _generate_base_prediction(self, features: Dict[str, Any], sport: str) -> Dict[str, Any]:
        """Generic market-derived fallback prediction."""
        mkt = features.get("market_odds", {})
        h = float(mkt.get("home", 2.0))
        d = float(mkt.get("draw", 3.0))
        a = float(mkt.get("away", 3.0))

        total = (1/h) + (1/d) + (1/a)
        hp, dp, ap = (1/h)/total, (1/d)/total, (1/a)/total

        return {
            "predictions": {
                "home_prob": round(hp, 4),
                "draw_prob": round(dp, 4),
                "away_prob": round(ap, 4),
                "over_25_prob": 0.5,
                "btts_prob": 0.5,
                "confidence": {"general": 0.5},
                "models_used": 0,
                "models_total": 13,
                "data_source": f"{sport}_base_scie"
            },
            "individual_results": []
        }

    def _normalise(self, h: float, d: float, a: float):
        total = h + d + a
        return h / total, d / total, a / total
