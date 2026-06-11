from __future__ import annotations
import logging
import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.api.middleware.auth import verify_api_key

router = APIRouter(prefix="/api/ai-intel", tags=["AI Analytics"])
logger = logging.getLogger(__name__)

# ── Injury analytics ─────────────────────────────────────────────────────────

_POSITION_WEIGHTS: Dict[str, float] = {
    "goalkeeper": 0.18, "keeper": 0.18, "gk": 0.18,
    "centre-back": 0.12, "center-back": 0.12, "cb": 0.12,
    "defender": 0.10, "fullback": 0.09, "right-back": 0.09, "left-back": 0.09,
    "midfielder": 0.10, "defensive mid": 0.12, "cdm": 0.12, "cm": 0.10,
    "attacking mid": 0.13, "cam": 0.13,
    "winger": 0.11, "right-winger": 0.11, "left-winger": 0.11,
    "forward": 0.14, "striker": 0.15, "cf": 0.15, "st": 0.15,
}

_SEVERITY_FACTORS: Dict[str, float] = {
    "season-ending": 1.0, "long-term": 0.85, "major": 0.9,
    "suspended": 0.70, "ban": 0.70, "red card": 0.75,
    "doubt": 0.40, "minor": 0.30, "knock": 0.25,
}


def _player_impact(description: str) -> float:
    """Estimate absence impact from a player description string."""
    desc = description.lower()
    pos_weight = 0.10
    for kw, w in _POSITION_WEIGHTS.items():
        if kw in desc:
            pos_weight = max(pos_weight, w)
    sev_factor = 0.60
    for kw, s in _SEVERITY_FACTORS.items():
        if kw in desc:
            sev_factor = max(sev_factor, s)
    return round(pos_weight * sev_factor, 4)


def _injury_adjustment(
    home_prob: float, draw_prob: float, away_prob: float,
    home_injuries: List[str], away_injuries: List[str],
) -> Dict[str, Any]:
    home_delta = min(sum(_player_impact(p) for p in home_injuries) * 0.25, 0.25)
    away_delta = min(sum(_player_impact(p) for p in away_injuries) * 0.25, 0.25)

    adj_home = home_prob - home_prob * home_delta + away_prob * away_delta * 0.60
    adj_draw  = draw_prob + home_prob * home_delta * 0.40 + away_prob * away_delta * 0.40
    adj_away  = away_prob - away_prob * away_delta + home_prob * home_delta * 0.60

    total = adj_home + adj_draw + adj_away
    if total > 0:
        adj_home, adj_draw, adj_away = adj_home/total, adj_draw/total, adj_away/total

    adj_home = round(max(0.01, min(0.98, adj_home)), 4)
    adj_draw  = round(max(0.01, min(0.98, adj_draw)),  4)
    adj_away  = round(max(0.01, min(0.98, adj_away)),  4)

    total_shift = abs(adj_home - home_prob) + abs(adj_away - away_prob)
    severity = "high" if total_shift >= 0.12 else "moderate" if total_shift >= 0.05 else "low" if total_shift >= 0.01 else "negligible"

    all_inj = (
        [(p, "home", _player_impact(p)) for p in home_injuries] +
        [(p, "away", _player_impact(p)) for p in away_injuries]
    )
    key_absences = [
        {"player": p, "side": side, "impact_score": score}
        for p, side, score in sorted(all_inj, key=lambda x: x[2], reverse=True)[:5]
        if score > 0
    ]

    home_change = round(adj_home - home_prob, 4)
    away_change = round(adj_away - away_prob, 4)
    parts = []
    if home_injuries:
        parts.append(f"{len(home_injuries)} home absence(s) shift home win prob by {home_change:+.1%}")
    if away_injuries:
        parts.append(f"{len(away_injuries)} away absence(s) shift away win prob by {away_change:+.1%}")

    return {
        "adjusted_home_prob": adj_home,
        "adjusted_draw_prob": adj_draw,
        "adjusted_away_prob": adj_away,
        "impact_severity": severity,
        "key_absences": key_absences,
        "home_prob_change": home_change,
        "away_prob_change": away_change,
        "narrative": "; ".join(parts) if parts else "No significant injury impact detected.",
    }


class InjuryAnalyticsRequest(BaseModel):
    home_team: str
    away_team: str
    league: str
    home_injuries: List[str] = []
    away_injuries: List[str] = []
    base_home_prob: float = 0.333
    base_draw_prob: float = 0.333
    base_away_prob: float = 0.334


@router.post("/injuries")
async def injury_analytics(body: InjuryAnalyticsRequest, _user=Depends(verify_api_key)):
    """Compute injury-adjusted match outcome probabilities using positional impact heuristics."""
    return _injury_adjustment(
        body.base_home_prob, body.base_draw_prob, body.base_away_prob,
        body.home_injuries, body.away_injuries,
    )


# ── Accumulator builder ───────────────────────────────────────────────────────

class AccumulatorRequest(BaseModel):
    legs: List[Dict[str, Any]] = Field(default_factory=list)
    max_legs: int = 5
    min_value_edge: float = 0.02


@router.post("/accumulator")
async def build_accumulator(body: AccumulatorRequest, _user=Depends(verify_api_key)):
    """
    Filter and rank accumulator legs by value edge, then compute combined odds.
    Each leg: {selection, odds, model_prob, match}.
    """
    if not body.legs:
        return {"selected_legs": [], "combined_odds": 1.0, "risk_tier": "none", "narrative": "No legs provided."}

    scored = []
    for leg in body.legs:
        try:
            odds = float(leg.get("odds", 1.0))
            prob = float(leg.get("model_prob", 0.5))
            edge = round(prob * odds - 1.0, 4)
            scored.append({**leg, "value_edge": edge})
        except (ValueError, TypeError):
            continue

    value_legs = sorted(
        [l for l in scored if l["value_edge"] >= body.min_value_edge],
        key=lambda x: x["value_edge"], reverse=True,
    )[:body.max_legs]

    if not value_legs:
        return {
            "selected_legs": [], "combined_odds": 1.0, "risk_tier": "none",
            "narrative": "No legs meet the minimum value-edge threshold.",
        }

    combined_odds = round(math.prod(float(l["odds"]) for l in value_legs), 2)
    n = len(value_legs)
    risk_tier = "low" if n <= 2 else "moderate" if n <= 4 else "high"
    avg_edge = sum(l["value_edge"] for l in value_legs) / n

    return {
        "selected_legs": value_legs,
        "combined_odds": combined_odds,
        "risk_tier": risk_tier,
        "narrative": (
            f"{n} value leg{'s' if n != 1 else ''} selected — "
            f"combined odds {combined_odds:.2f}x, avg edge {avg_edge:.1%} ({risk_tier} risk)."
        ),
    }


# ── Market regime ─────────────────────────────────────────────────────────────

@router.post("/market-regime")
async def market_regime(body: Any, _user=Depends(verify_api_key)):
    """Classify market efficiency from the vig embedded in the odds."""
    try:
        odds = body.get("odds", {}) if isinstance(body, dict) else {}
        home_o = float(odds.get("home", 2.5))
        draw_o = float(odds.get("draw", 3.2))
        away_o = float(odds.get("away", 2.8))
        vig = (1/home_o + 1/draw_o + 1/away_o) - 1.0
        regime = "efficient" if vig < 0.04 else "overround" if vig < 0.08 else "high_vig"
        return {"regime_type": regime, "vig": round(vig, 4)}
    except Exception:
        return {"regime_type": "unknown", "vig": None}


# ── Form narrative ────────────────────────────────────────────────────────────

@router.post("/form-narrative")
async def form_narrative(body: Any, _user=Depends(verify_api_key)):
    """Generate a form rating from recent W/D/L strings (e.g. ['W','W','D','L','W'])."""
    try:
        results = body.get("recent_results", []) if isinstance(body, dict) else []
        recent = [r.upper() for r in results[-5:] if isinstance(r, str)]
        if not recent:
            return {"form_rating": 5.0, "recent_results": [], "points_per_game": 0.0}
        points = sum(3 if r == "W" else 1 if r == "D" else 0 for r in recent)
        rating = round((points / (len(recent) * 3)) * 10, 1)
        return {
            "form_rating": rating,
            "recent_results": recent,
            "points_per_game": round(points / len(recent), 2),
        }
    except Exception:
        return {"form_rating": 5.0}


# ── Stub endpoints (require external data sources) ────────────────────────────

@router.post("/governance")
async def governance_analytics(body: Any, _user=Depends(verify_api_key)):
    return {"recommendation": "neutral"}


@router.post("/sentiment")
async def social_sentiment(body: Any, _user=Depends(verify_api_key)):
    return {"sentiment_score": 0.5, "source": "unavailable", "note": "External sentiment API not configured."}


@router.post("/news-momentum")
async def news_momentum(body: Any, _user=Depends(verify_api_key)):
    return {"predicted_movement": "stable", "note": "External news API not configured."}


@router.post("/breaking-news")
async def breaking_news_scan(body: Any, _user=Depends(verify_api_key)):
    return {"alert_level": "none", "note": "Real-time news scanning requires external API configuration."}


@router.get("/health")
async def ai_intel_health():
    return {
        "status": "healthy",
        "available_providers": 1,
        "priority": ["native"],
        "capabilities": {
            "injuries": "heuristic_positional",
            "accumulator": "value_edge_filter",
            "market_regime": "vig_analysis",
            "form_narrative": "results_based",
            "sentiment": "unavailable",
            "news_momentum": "unavailable",
            "breaking_news": "unavailable",
        },
    }
