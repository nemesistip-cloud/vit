import logging
import math
import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.schemas.schemas import PredictionResponse, ModelInsight
from app.services.predict_features import (
    get_fresh_football_form,
    has_fresh_verified_match_history,
)

logger = logging.getLogger(__name__)

TWO_WAY_STATISTICAL_FALLBACK_SPORTS = frozenset({
    "basketball", "tennis", "rugby", "american_football", "rugby_union",
    "baseball", "ice_hockey", "mma", "boxing",
})
ODDS_OPTIONAL_MATCH_WINNER_SPORTS = frozenset({
    "football",
    *TWO_WAY_STATISTICAL_FALLBACK_SPORTS,
})


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _safe_normalize(home: float, away: float) -> tuple[float, float]:
    total = home + away
    if total <= 0:
        return 0.5, 0.5
    return home / total, away / total

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


def _require_two_way_odds(features: Dict[str, Any]) -> tuple[float, float]:
    market = features.get("market_odds") or {}
    try:
        home = float(market["home"])
        away = float(market["away"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("provider home/away odds are required for this sport") from exc
    if not all(math.isfinite(value) and value > 1.0 for value in (home, away)):
        raise ValueError("provider home/away odds must be greater than 1.0")
    return home, away


class MultiSportOrchestrator:
    """
    Enhanced orchestrator to handle non-football sports with dynamic logic.
    Provides a unified interface for all sports while supporting specialized models.
    Supports 'Hybrid Mode' (ML + SCIE Fallback).
    Probabilities come from market inputs or validated historical form; no random
    stubs are used.
    """

    def __init__(self, football_orchestrator=None):
        self.football_orchestrator = football_orchestrator
        default_real_ml = "true" if os.getenv("ENVIRONMENT", "").lower() == "production" else "false"
        self.use_real_ml = os.getenv("USE_REAL_ML_MODELS", default_real_ml).lower() == "true"

    async def predict(self, features: Dict[str, Any], idempotency_key: str = None, sport: str = "football") -> Dict[str, Any]:
        """Dispatch prediction request to the appropriate engine based on sport."""
        sport = (sport or "football").lower()

        if sport == "football":
            return await self._predict_football(features, idempotency_key)
        elif sport in {"basketball", "tennis", "rugby", "american_football", "rugby_union", "baseball", "ice_hockey", "mma", "boxing", "formula1", "esports"}:
            market = (features.get("market_odds") or {})
            if (
                (market.get("home") is None or market.get("away") is None)
                and sport in TWO_WAY_STATISTICAL_FALLBACK_SPORTS
            ):
                return self._predict_two_way_statistical(features, sport)
            if sport == "basketball":
                return self._predict_basketball(features)
            if sport == "tennis":
                return self._predict_tennis(features)
            if sport in {"rugby", "rugby_union", "american_football", "baseball", "ice_hockey", "mma", "boxing", "formula1", "esports"}:
                return self._predict_two_way(features, f"{sport}_scie_v3")
            return self._predict_two_way(features, f"{sport}_scie_v3")
        elif sport == "basketball":
            return self._predict_basketball(features)
        elif sport == "tennis":
            return self._predict_tennis(features)
        elif sport == "cricket":
            return self._predict_two_way(features, "cricket_scie_v3")
        else:
            return self._predict_two_way(features, f"{sport}_scie_v3")

    def _predict_two_way_statistical(self, features: Dict[str, Any], sport: str) -> Dict[str, Any]:
        """Return a no-odds prediction only when real, recent team history is sufficient."""
        match_features = features.get("match_features") or {}
        completeness = float(match_features.get("feature_completeness", 0.0) or 0.0)
        home_hist = int(match_features.get("home_history_sample_size", 0) or 0)
        away_hist = int(match_features.get("away_history_sample_size", 0) or 0)
        history_sample = int(match_features.get("history_sample_size", 0) or 0)
        reasons: List[str] = []

        if completeness < 0.55:
            reasons.append(f"feature completeness {completeness:.2f} below the required 0.55 threshold")
        if history_sample < 3:
            reasons.append(f"insufficient historical sample size ({history_sample}), need at least 3 recent matches")
        if home_hist < 3 or away_hist < 3:
            reasons.append(f"insufficient per-team history ({home_hist}/{away_hist}), need at least 3 matches each")
        if not has_fresh_verified_match_history(match_features):
            reasons.append("trusted, fresh match history is required for an odds-free prediction")

        now = datetime.now(timezone.utc)
        for label, key in (("home", "home_history_latest"), ("away", "away_history_latest")):
            raw_date = match_features.get(key)
            if not raw_date:
                reasons.append(f"{label} historical evidence date is unavailable")
                continue
            try:
                latest = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                if latest.tzinfo is None:
                    latest = latest.replace(tzinfo=timezone.utc)
                else:
                    latest = latest.astimezone(timezone.utc)
                age_days = (now - latest).total_seconds() / 86400
                if age_days < 0:
                    reasons.append(f"{label} historical evidence is future-dated")
                elif age_days > 540:
                    reasons.append(f"{label} historical evidence is stale ({int(age_days)} days old; maximum 540)")
            except (TypeError, ValueError):
                reasons.append(f"{label} historical evidence has an invalid date")

        if reasons:
            return {
                "status": "unavailable",
                "reasons": reasons,
                "predictions": {
                    "home_prob": 0.0,
                    "draw_prob": 0.0,
                    "away_prob": 0.0,
                    "confidence": {"moneyline": 0.0},
                },
                "source": f"{sport}_statistical_fallback_unavailable",
            }

        home_form = float(match_features.get("home_form_pts_10", 1.3) or 1.3)
        away_form = float(match_features.get("away_form_pts_10", 1.2) or 1.2)
        home_win_rate = min(1.0, max(0.0, home_form / 3.0))
        away_win_rate = min(1.0, max(0.0, away_form / 3.0))
        logit = 1.1 * (home_win_rate - away_win_rate) + 0.1
        home_prob = round(min(0.85, max(0.15, _sigmoid(logit))), 4)
        away_prob = round(1.0 - home_prob, 4)

        confidence = min(0.65, 0.40 + completeness * 0.25)
        return {
            "status": "ready",
            "reasons": [],
            "predictions": {
                "home_prob": home_prob,
                "draw_prob": 0.0,
                "away_prob": away_prob,
                "confidence": {"moneyline": round(confidence, 4)},
                "models_used": 0,
                "models_total": 0,
                "data_source": f"{sport}_statistical_fallback",
            },
            "source": f"{sport}_statistical_fallback",
        }

    async def _predict_football(self, features: Dict[str, Any], idempotency_key: str = None) -> Dict[str, Any]:
        """Hybrid football prediction: ML Ensemble with SCIE Fallback."""
        if self.football_orchestrator and self.use_real_ml:
            try:
                if self.football_orchestrator.num_models_ready() > 0:
                    predict = self.football_orchestrator.predict
                    if asyncio.iscoroutinefunction(predict):
                        return await predict(
                            features,
                            match_id=idempotency_key or "unknown",
                            sport="soccer",
                        )
                    return predict(
                        features,
                        match_id=idempotency_key or "unknown",
                        sport="soccer",
                    )
                else:
                    logger.info("[orchestrator] ML models not ready, falling back to SCIE")
            except Exception as e:
                logger.error(f"[orchestrator] ML Ensemble failed: {e}")

        return self._generate_scie_football(features)

    def _generate_scie_football(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """High-fidelity statistical fallback for football — fully deterministic."""
        mkt = features.get("market_odds", {})
        match_features = features.get("match_features") or {}
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

        current_form = get_fresh_football_form(match_features)
        providers = set(current_form["providers"]) if current_form else set()
        if current_form:
            hp *= math.exp(current_form["form_shift"])
            ap *= math.exp(-current_form["form_shift"])
            hp, dp, ap = self._normalise(hp, dp, ap)
            data_source = "vit_scie_v6_market_plus_real_form"
            lambda_home = current_form["lambda_home"]
            lambda_away = current_form["lambda_away"]
        else:
            # Without recent football evidence, keep secondary markets as
            # lower-confidence market-derived estimates.
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
                "data_source": data_source,
                "evidence_providers": sorted(providers),
            },
            "individual_results": [],
            "scie_mode": True
        }

    def _predict_basketball(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Market-derived basketball prediction — no random stubs."""
        market = features.get("market_odds") or {}
        if market.get("home") is None or market.get("away") is None:
            return self._predict_two_way_statistical(features, "basketball")

        h_odds, a_odds = _require_two_way_odds(features)

        total_implied = (1/h_odds) + (1/a_odds)
        h_prob = round((1/h_odds) / total_implied, 4)
        a_prob = round(1.0 - h_prob, 4)

        balance = 1.0 - abs(h_prob - a_prob)
        over_total = round(min(0.97, 0.93 + balance * 0.03), 4)

        return {
            "predictions": {
                "home_prob": h_prob,
                "draw_prob": 0.0,
                "away_prob": a_prob,
                "over_25_prob": over_total,
                "btts_prob": 0.0,
                "confidence": {"moneyline": self._two_way_confidence(h_prob, a_prob)},
                "models_used": 0,
                "models_total": 0,
                "data_source": "basketball_scie_v2"
            },
            "individual_results": []
        }

    def _predict_tennis(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Market-derived tennis prediction — no random stubs."""
        market = features.get("market_odds") or {}
        if market.get("home") is None or market.get("away") is None:
            return self._predict_two_way_statistical(features, "tennis")

        h_odds, a_odds = _require_two_way_odds(features)

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
                "confidence": {"winner": self._two_way_confidence(h_prob, a_prob)},
                "models_used": 0,
                "models_total": 0,
                "data_source": "tennis_scie_v2"
            },
            "individual_results": []
        }

    def _predict_two_way(self, features: Dict[str, Any], source: str) -> Dict[str, Any]:
        h_odds, a_odds = _require_two_way_odds(features)
        total = (1 / h_odds) + (1 / a_odds)
        hp, ap = (1 / h_odds) / total, (1 / a_odds) / total

        return {
            "predictions": {
                "home_prob": round(hp, 4), "draw_prob": 0.0, "away_prob": round(ap, 4),
                "over_25_prob": None, "btts_prob": None,
                "confidence": {"winner": self._two_way_confidence(hp, ap)},
                "models_used": 0,
                "models_total": 0, "data_source": source,
            },
            "individual_results": []
        }

    @staticmethod
    def _two_way_confidence(home_prob: float, away_prob: float) -> float:
        # Market-implied probabilities are not calibrated model confidence.
        # Keep confidence at zero until a sport-specific model is validated.
        return 0.0

    def _normalise(self, h: float, d: float, a: float):
        total = h + d + a
        return h / total, d / total, a / total
