"""
app/modules/evidence/requirements.py — Market requirement definitions and evaluator.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class MarketRequirementSpec(TypedDict):
    required_features: List[str]
    min_feature_completeness_pct: int
    requires_odds: bool


MARKET_REQUIREMENTS: Dict[str, MarketRequirementSpec] = {
    "1x2": {
        "required_features": ["home_team", "away_team", "league", "kickoff_time"],
        "min_feature_completeness_pct": 70,
        "requires_odds": True,
    },
    "over_under_2_5": {
        "required_features": ["home_team", "away_team", "league", "goal_stats"],
        "min_feature_completeness_pct": 65,
        "requires_odds": False,
    },
    "btts": {
        "required_features": ["home_team", "away_team", "btts_history"],
        "min_feature_completeness_pct": 60,
        "requires_odds": False,
    },
}


def evaluate_market_requirements(
    feature_snapshot: Dict[str, Any],
    market_key: str,
) -> Dict[str, Any]:
    """
    Evaluates whether a feature snapshot meets requirements for a specified market_key.

    Returns:
        {"requirements_met": bool, "reason": str | None}
    """
    req_spec = MARKET_REQUIREMENTS.get(market_key)
    if not req_spec:
        return {
            "requirements_met": False,
            "reason": f"Unknown market key '{market_key}'. Supported: {list(MARKET_REQUIREMENTS.keys())}",
        }

    # Check completeness
    completeness = feature_snapshot.get("feature_completeness_pct", 0)
    if isinstance(completeness, (int, float)):
        completeness_pct = int(completeness)
    else:
        completeness_pct = 0

    if completeness_pct < req_spec["min_feature_completeness_pct"]:
        return {
            "requirements_met": False,
            "reason": (
                f"Feature completeness {completeness_pct}% is below required minimum "
                f"of {req_spec['min_feature_completeness_pct']}% for market '{market_key}'"
            ),
        }

    # Check required features
    features = feature_snapshot.get("features", {})
    if not isinstance(features, dict):
        features = {}

    missing_features = [
        feat for feat in req_spec["required_features"] if features.get(feat) is None
    ]
    if missing_features:
        return {
            "requirements_met": False,
            "reason": f"Missing required features for '{market_key}': {', '.join(missing_features)}",
        }

    # Check odds requirement
    if req_spec["requires_odds"]:
        market_odds = feature_snapshot.get("market_odds") or features.get("market_odds")
        if not market_odds or not isinstance(market_odds, dict):
            return {
                "requirements_met": False,
                "reason": f"Market '{market_key}' requires valid market_odds dict",
            }

    return {
        "requirements_met": True,
        "reason": None,
    }
