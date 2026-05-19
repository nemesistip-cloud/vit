"""app/services/deterministic_insights.py — Deterministic statistical fallback insights.

When all LLM providers are unavailable, this module generates a fully deterministic,
statistically-grounded insight from the ML ensemble output and market odds.

Algorithm:
  1. Start from the 13-model ensemble probabilities (already computed).
  2. Blend with a small historical prior (home ~45%, draw ~26%, away ~29%).
  3. Derive risk/confidence from ensemble conviction (distance from uniform 33/33/33).
  4. Build templated narrative text — factual, no hallucination, clearly labelled.

The result is always `available=True` so the AI signals panel is never empty.
"""

from __future__ import annotations

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Historical 1X2 prior across top-5 European leagues (approx.) ──────────────
_PRIOR_HOME  = 0.455
_PRIOR_DRAW  = 0.258
_PRIOR_AWAY  = 0.287

# How much weight to give the prior vs. the ML ensemble output.
# At 0.10, a 70% ML home signal becomes ≈ 67.5% blended — barely changed.
_PRIOR_BLEND = 0.10


def _entropy(h: float, d: float, a: float) -> float:
    total = 0.0
    for p in (h, d, a):
        if p > 1e-9:
            total -= p * math.log(p)
    return total


def _conviction_label(top_prob: float) -> str:
    if top_prob >= 0.60:
        return "strong"
    if top_prob >= 0.48:
        return "moderate"
    return "marginal"


def _risk_level(top_prob: float, edge: float) -> str:
    if top_prob >= 0.60 and abs(edge) >= 0.03:
        return "LOW"
    if top_prob >= 0.48 or abs(edge) >= 0.02:
        return "MEDIUM"
    return "HIGH"


def _best_side_label(h: float, d: float, a: float) -> tuple[str, float]:
    """Return (side_name, probability) for the highest probability outcome."""
    return max(
        [("Home Win", h), ("Draw", d), ("Away Win", a)],
        key=lambda x: x[1],
    )


def generate_deterministic_insights(
    home_team: str,
    away_team: str,
    league: str,
    home_prob: float,
    draw_prob: float,
    away_prob: float,
    over_25_prob: Optional[float] = None,
    btts_prob: Optional[float] = None,
    bet_side: Optional[str] = None,
    edge: float = 0.0,
    entry_odds: Optional[float] = None,
    confidence: float = 0.5,
) -> dict:
    """
    Generate statistically-grounded insights without any external AI call.
    Returns the same schema as gemini/openai/grok insights generators.
    """
    # ── 1. Blend ensemble probs with prior ────────────────────────────────────
    hp = (1 - _PRIOR_BLEND) * home_prob + _PRIOR_BLEND * _PRIOR_HOME
    dp = (1 - _PRIOR_BLEND) * draw_prob + _PRIOR_BLEND * _PRIOR_DRAW
    ap = (1 - _PRIOR_BLEND) * away_prob + _PRIOR_BLEND * _PRIOR_AWAY
    total = hp + dp + ap
    if total > 0:
        hp /= total; dp /= total; ap /= total

    # ── 2. Conviction & confidence ────────────────────────────────────────────
    top_label, top_prob = _best_side_label(hp, dp, ap)
    conv   = _conviction_label(top_prob)
    risk   = _risk_level(top_prob, edge)
    max_entropy = math.log(3)
    norm_entropy = _entropy(hp, dp, ap) / max_entropy if max_entropy > 0 else 0.5
    stat_confidence = round(max(0.35, min(0.90, 1.0 - norm_entropy * 0.6)), 4)

    # ── 3. Narrative text ────────────────────────────────────────────────────
    league_label = league.replace("_", " ").title()
    edge_pct     = edge * 100
    odds_str     = f"{entry_odds:.2f}" if entry_odds else "N/A"

    ou_note = ""
    if over_25_prob is not None:
        ou_dir = "Lean Over" if over_25_prob >= 0.55 else ("Lean Under" if over_25_prob <= 0.42 else "Neutral")
        ou_note = f" Goals market signals {ou_dir} ({over_25_prob*100:.0f}% O2.5)."

    btts_note = ""
    if btts_prob is not None and btts_prob >= 0.55:
        btts_note = f" BTTS probability is elevated at {btts_prob*100:.0f}%."

    summary = (
        f"The 13-model ensemble assigns {top_label} a {conv} {top_prob*100:.1f}% probability "
        f"in {home_team} vs {away_team} ({league_label}). "
        f"The home side carries a {hp*100:.1f}% win probability versus {ap*100:.1f}% for the visitors, "
        f"with a draw at {dp*100:.1f}%."
        f"{ou_note}{btts_note}"
    )

    # ── 4. Key factors ────────────────────────────────────────────────────────
    key_factors = [f"ML ensemble conviction: {conv} ({top_prob*100:.1f}% for {top_label})"]

    home_edge = hp - _PRIOR_HOME
    if home_edge > 0.04:
        key_factors.append(f"Home advantage amplified by {home_edge*100:.1f}pp above historical base rate")
    elif home_edge < -0.04:
        key_factors.append(f"Home team underperforms historical base rate by {abs(home_edge)*100:.1f}pp")

    if abs(edge_pct) >= 2.0:
        direction = "positive" if edge_pct > 0 else "negative"
        key_factors.append(f"Market edge is {direction} at {abs(edge_pct):.2f}% vs vig-free fair price")

    if over_25_prob is not None:
        key_factors.append(f"Over 2.5 Goals at {over_25_prob*100:.1f}% — {'above' if over_25_prob >= 0.5 else 'below'} 50% threshold")

    key_factors.append(f"Ensemble entropy at {norm_entropy*100:.0f}% of maximum — {'uncertain' if norm_entropy > 0.6 else 'decisive'} split")

    # ── 5. Value assessment ───────────────────────────────────────────────────
    if abs(edge_pct) >= 3.0:
        val = f"Edge of {edge_pct:.2f}% at {odds_str} represents a {'value bet' if edge_pct > 0 else 'value lay'} opportunity per the ML ensemble."
    elif abs(edge_pct) >= 1.0:
        val = f"Marginal edge of {edge_pct:.2f}% — proceed only with bankroll discipline."
    else:
        val = f"No meaningful edge detected at {odds_str}; pass unless line moves."

    # ── 6. Recommendation ────────────────────────────────────────────────────
    if edge_pct >= 3.0 and bet_side:
        rec = f"BUY — ensemble edge of {edge_pct:.2f}% on {bet_side.upper()} meets minimum threshold."
    elif edge_pct <= -3.0:
        rec = "SELL — negative edge; market has a better read than the ensemble."
    else:
        rec = "HOLD — edge is below the 3% actionable threshold; await better price."

    # ── 7. Insight tags ───────────────────────────────────────────────────────
    tags: list[str] = []
    tags.append(f"conviction:{conv}")
    tags.append(f"risk:{risk.lower()}")
    if over_25_prob is not None:
        tags.append("goals-market")
    if abs(edge_pct) >= 3.0:
        tags.append("edge-bet")
    tags.append("deterministic-fallback")

    return {
        "available":        True,
        "source":           "deterministic",
        "label":            "VIT Statistical Engine",
        "home_prob":        round(hp, 4),
        "draw_prob":        round(dp, 4),
        "away_prob":        round(ap, 4),
        "confidence":       stat_confidence,
        "summary":          summary,
        "key_factors":      key_factors[:5],
        "value_assessment": val,
        "recommendation":   rec,
        "risk_level":       risk,
        "insight_tags":     tags,
        "error":            None,
        "is_fallback":      True,
    }


async def generate_match_insights(
    home_team: str,
    away_team: str,
    league: str,
    home_prob: float,
    draw_prob: float,
    away_prob: float,
    over_25_prob: Optional[float] = None,
    btts_prob: Optional[float] = None,
    bet_side: Optional[str] = None,
    edge: float = 0.0,
    entry_odds: Optional[float] = None,
    confidence: float = 0.5,
) -> dict:
    """Async wrapper — signature matches all other *_insights.py modules."""
    return generate_deterministic_insights(
        home_team=home_team, away_team=away_team, league=league,
        home_prob=home_prob, draw_prob=draw_prob, away_prob=away_prob,
        over_25_prob=over_25_prob, btts_prob=btts_prob,
        bet_side=bet_side, edge=edge, entry_odds=entry_odds,
        confidence=confidence,
    )
