"""app/services/openai_advanced.py — Advanced OpenAI-powered analytics services.

Four capabilities routed through the shared AI cascade (preferred=openai):
  1. injury_analysis         — injury/suspension impact on match outcome
  2. accumulator_builder     — AI-curated multi-match accumulator selection
  3. market_regime_detection — classify current market as sharp/public/mixed
  4. governance_proposal_ai  — analyse DAO governance proposals with structured verdict
"""

from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── helpers ────────────────────────────────────────────────────────────────────

def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def _call(prompt: str, max_tokens: int = 700, temperature: float = 0.3) -> tuple[Optional[str], str]:
    """Wrapper around the shared AI cascade, preferred=openai. Returns (raw_text, provider)."""
    from app.services.ai_client import call_ai_with_provider
    result = await call_ai_with_provider(prompt, max_tokens=max_tokens, temperature=temperature, preferred="openai")
    if result is None:
        return None, "unavailable"
    return result


# ── 1. Injury / Suspension Impact Analysis ────────────────────────────────────

async def analyze_injuries(
    home_team: str,
    away_team: str,
    league: str,
    home_injuries: list[str],
    away_injuries: list[str],
    base_home_prob: float,
    base_draw_prob: float,
    base_away_prob: float,
) -> dict:
    """
    Assess how reported injuries/suspensions shift the base 1X2 probabilities.

    Returns adjusted probabilities, impact severity, key absences, and a narrative.
    """
    league_label = league.replace("_", " ").title()
    home_inj_str = ", ".join(home_injuries) if home_injuries else "None reported"
    away_inj_str = ", ".join(away_injuries) if away_injuries else "None reported"

    prompt = f"""You are a football injury & suspension analyst.

Match: {home_team} vs {away_team} | League: {league_label}
Base probabilities: Home={base_home_prob*100:.1f}% Draw={base_draw_prob*100:.1f}% Away={base_away_prob*100:.1f}%

Confirmed absences:
- {home_team}: {home_inj_str}
- {away_team}: {away_inj_str}

Adjust probabilities based on the importance of absent players and return ONLY valid JSON:
{{
  "adjusted_home_prob": 0.00,
  "adjusted_draw_prob": 0.00,
  "adjusted_away_prob": 0.00,
  "impact_severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "home_impact_score": 0.0,
  "away_impact_score": 0.0,
  "key_absences": [{{"team": "TeamName", "player": "Name", "role": "GK|CB|CDM|CM|CAM|FW", "impact": "brief note"}}],
  "narrative": "2-3 sentence summary of injury impact on match dynamics",
  "confidence_adjustment": -0.05
}}
Probabilities must sum to 1.0. impact_severity: LOW(<5% swing) MEDIUM(5-10%) HIGH(10-20%) CRITICAL(>20%)."""

    raw, provider = await _call(prompt, max_tokens=600)
    if raw is None:
        home_inj_count = len(home_injuries)
        away_inj_count = len(away_injuries)
        adj_home = max(0.05, base_home_prob - home_inj_count * 0.02)
        adj_away = max(0.05, base_away_prob - away_inj_count * 0.02)
        adj_draw = max(0.05, 1.0 - adj_home - adj_away)
        total = adj_home + adj_draw + adj_away
        adj_home /= total; adj_draw /= total; adj_away /= total
        severity = "NONE" if not home_injuries and not away_injuries else (
            "HIGH" if (home_inj_count + away_inj_count) >= 3 else
            "MEDIUM" if (home_inj_count + away_inj_count) >= 1 else "LOW"
        )
        conf_adj = -(home_inj_count + away_inj_count) * 0.01
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "adjusted_home_prob": round(adj_home, 4),
            "adjusted_draw_prob": round(adj_draw, 4),
            "adjusted_away_prob": round(adj_away, 4),
            "impact_severity": severity,
            "home_impact_score": home_inj_count * 0.15,
            "away_impact_score": away_inj_count * 0.15,
            "key_absences": (
                [{"team": home_team, "player": p, "role": "UNKNOWN", "impact": "Absence noted"} for p in home_injuries] +
                [{"team": away_team, "player": p, "role": "UNKNOWN", "impact": "Absence noted"} for p in away_injuries]
            ),
            "narrative": (
                f"VIT Statistical Engine: live injury AI unavailable. "
                f"{home_team} missing {home_inj_count} player(s); {away_team} missing {away_inj_count}. "
                f"Probabilities adjusted using -2% per reported absence from base ensemble output."
            ),
            "confidence_adjustment": round(conf_adj, 3),
        }

    try:
        parsed = json.loads(_strip_fence(raw))
        hp = float(parsed.get("adjusted_home_prob", base_home_prob))
        dp = float(parsed.get("adjusted_draw_prob", base_draw_prob))
        ap = float(parsed.get("adjusted_away_prob", base_away_prob))
        total = hp + dp + ap
        if total > 0 and abs(total - 1.0) > 0.01:
            hp /= total; dp /= total; ap /= total
        return {
            "available": True,
            "source": provider,
            "adjusted_home_prob": round(hp, 4),
            "adjusted_draw_prob": round(dp, 4),
            "adjusted_away_prob": round(ap, 4),
            "impact_severity": parsed.get("impact_severity", "LOW"),
            "home_impact_score": float(parsed.get("home_impact_score", 0)),
            "away_impact_score": float(parsed.get("away_impact_score", 0)),
            "key_absences": parsed.get("key_absences", []),
            "narrative": parsed.get("narrative", ""),
            "confidence_adjustment": float(parsed.get("confidence_adjustment", 0)),
        }
    except Exception as exc:
        logger.error("injury_analysis parse error: %s", exc)
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "adjusted_home_prob": round(base_home_prob, 4),
            "adjusted_draw_prob": round(base_draw_prob, 4),
            "adjusted_away_prob": round(base_away_prob, 4),
            "impact_severity": "LOW",
            "home_impact_score": 0.0,
            "away_impact_score": 0.0,
            "key_absences": [],
            "narrative": f"Parse error — returning base probabilities for {home_team} vs {away_team}.",
            "confidence_adjustment": 0.0,
        }


# ── 2. Accumulator Builder ─────────────────────────────────────────────────────

async def build_accumulator(
    candidates: list[dict],
    target_odds: float = 5.0,
    max_legs: int = 5,
    min_confidence: float = 0.55,
) -> dict:
    """
    Select the best accumulator legs from a list of candidate predictions.

    Each candidate dict should contain: match, home_team, away_team, league,
    home_prob, draw_prob, away_prob, best_side, best_odds, confidence, edge.

    Returns selected legs, combined odds, implied probability, risk tier.
    """
    if not candidates:
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "selected_indices": [],
            "legs": [],
            "combined_odds": 1.0,
            "implied_probability": 1.0,
            "expected_value": 0.0,
            "risk_tier": "LOW",
            "banker_leg_index": None,
            "narrative": "No candidates provided for accumulator selection.",
            "warnings": ["Supply at least one candidate prediction to build an accumulator."],
        }

    cand_lines = []
    for i, c in enumerate(candidates[:15], 1):
        cand_lines.append(
            f"{i}. {c.get('home_team','?')} vs {c.get('away_team','?')} [{c.get('league','?')}] "
            f"| Best: {str(c.get('best_side','?')).upper()} @ {c.get('best_odds',2.0):.2f} "
            f"| Conf: {float(c.get('confidence',0))*100:.0f}% | Edge: {float(c.get('edge',0))*100:.2f}%"
        )

    prompt = f"""You are a professional accumulator betting analyst.

Available matches (index | fixture | recommended side | odds | confidence | edge):
{chr(10).join(cand_lines)}

Build the optimal accumulator with these constraints:
- Target combined odds: ~{target_odds:.1f}x
- Maximum legs: {max_legs}
- Minimum confidence per leg: {min_confidence*100:.0f}%
- Prioritise independent events (avoid same league/date clusters)
- Prefer HIGH edge + HIGH confidence legs

Return ONLY valid JSON:
{{
  "selected_indices": [1, 3, 5],
  "legs": [
    {{"match": "Home vs Away", "league": "league_name", "side": "home|draw|away", "odds": 2.10, "confidence": 0.68, "rationale": "brief"}}
  ],
  "combined_odds": 9.26,
  "implied_probability": 0.108,
  "expected_value": 0.042,
  "risk_tier": "LOW|MEDIUM|HIGH|SPECULATIVE",
  "banker_leg_index": 0,
  "narrative": "2-sentence summary of the acca selection strategy",
  "warnings": ["any caveats"]
}}"""

    raw, provider = await _call(prompt, max_tokens=800, temperature=0.4)
    if raw is None:
        qualified = sorted(
            [c for c in candidates if float(c.get("confidence", 0)) >= min_confidence],
            key=lambda c: float(c.get("edge", 0)) + float(c.get("confidence", 0)),
            reverse=True,
        )[:max_legs]
        legs = []
        combined = 1.0
        for c in qualified:
            odds = float(c.get("best_odds", 2.0))
            combined *= odds
            legs.append({
                "match": f"{c.get('home_team','?')} vs {c.get('away_team','?')}",
                "league": c.get("league", ""),
                "side": str(c.get("best_side", "home")).lower(),
                "odds": odds,
                "confidence": float(c.get("confidence", 0)),
                "rationale": "Selected by VIT Statistical Engine (highest edge + confidence)",
            })
        implied = round(1.0 / combined, 4) if combined > 0 else 0.0
        risk_tier = "SPECULATIVE" if combined > 10 else "HIGH" if combined > 6 else "MEDIUM" if combined > 3 else "LOW"
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "selected_indices": list(range(len(legs))),
            "legs": legs,
            "combined_odds": round(combined, 2),
            "implied_probability": implied,
            "expected_value": round(implied * combined - 1.0, 4),
            "risk_tier": risk_tier,
            "banker_leg_index": 0 if legs else None,
            "narrative": (
                f"VIT Statistical Engine selected {len(legs)} leg(s) meeting the "
                f"≥{min_confidence*100:.0f}% confidence threshold, targeting ~{target_odds:.1f}x combined odds."
            ),
            "warnings": ["Statistical selection only — verify team news before placing."],
        }

    try:
        parsed = json.loads(_strip_fence(raw))
        return {
            "available": True,
            "source": provider,
            "selected_indices": parsed.get("selected_indices", []),
            "legs": parsed.get("legs", []),
            "combined_odds": float(parsed.get("combined_odds", 1.0)),
            "implied_probability": float(parsed.get("implied_probability", 0)),
            "expected_value": float(parsed.get("expected_value", 0)),
            "risk_tier": parsed.get("risk_tier", "MEDIUM"),
            "banker_leg_index": parsed.get("banker_leg_index", 0),
            "narrative": parsed.get("narrative", ""),
            "warnings": parsed.get("warnings", []),
        }
    except Exception as exc:
        logger.error("accumulator_builder parse error: %s", exc)
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "selected_indices": [],
            "legs": [],
            "combined_odds": 1.0,
            "implied_probability": 1.0,
            "expected_value": 0.0,
            "risk_tier": "LOW",
            "banker_leg_index": None,
            "narrative": "Parse error — accumulator selection unavailable.",
            "warnings": ["Try again or adjust candidate criteria."],
        }


# ── 3. Market Regime Detection ─────────────────────────────────────────────────

async def detect_market_regime(
    league: str,
    recent_results: list[dict],
    odds_movements: list[dict],
    public_betting_percentages: Optional[dict] = None,
) -> dict:
    """
    Classify current market regime for a league/competition.

    recent_results: [{home, away, outcome, pre_odds_home, pre_odds_away, closing_odds_home}]
    odds_movements: [{match, side, open, close, pct_move}]
    public_betting_percentages: {"home_pct": 0.60, "draw_pct": 0.20, "away_pct": 0.20}

    Returns: regime class, sharp money indicators, fade signals, market efficiency score.
    """
    league_label = league.replace("_", " ").title()
    results_str = json.dumps(recent_results[:10], default=str)
    moves_str = json.dumps(odds_movements[:10], default=str)
    public_str = json.dumps(public_betting_percentages or {})

    prompt = f"""You are a market microstructure analyst specialising in football betting markets.

League: {league_label}
Recent results (last 10): {results_str}
Odds movements: {moves_str}
Public betting split: {public_str}

Classify the current market regime and return ONLY valid JSON:
{{
  "regime": "SHARP_DOMINATED|PUBLIC_DOMINATED|EFFICIENT|TRANSITIONAL|VOLATILE",
  "efficiency_score": 0.82,
  "sharp_money_signals": ["signal 1", "signal 2"],
  "fade_opportunities": [{{"match": "Home vs Away", "fade_side": "home|draw|away", "rationale": "brief"}}],
  "clv_trend": "IMPROVING|STABLE|DEGRADING",
  "recommended_strategy": "VALUE_BET|CONTRARIAN|FOLLOW_SHARP|WAIT|AVOID",
  "confidence": 0.75,
  "narrative": "2-3 sentence market analysis",
  "risk_factors": ["factor 1", "factor 2"]
}}"""

    raw, provider = await _call(prompt, max_tokens=600, temperature=0.3)
    if raw is None:
        avg_move = 0.0
        if odds_movements:
            moves = [abs(float(m.get("pct_move", 0))) for m in odds_movements if "pct_move" in m]
            avg_move = sum(moves) / len(moves) if moves else 0.0
        regime = "VOLATILE" if avg_move > 5.0 else "EFFICIENT"
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "regime": regime,
            "efficiency_score": 0.72,
            "sharp_money_signals": ["Insufficient data for sharp money detection"],
            "fade_opportunities": [],
            "clv_trend": "STABLE",
            "recommended_strategy": "WAIT",
            "confidence": 0.4,
            "narrative": (
                f"VIT Statistical Engine: live market regime analysis unavailable for {league_label}. "
                f"Defaulting to EFFICIENT regime based on {len(recent_results)} recent results. "
                f"Average odds movement of {avg_move:.1f}% detected across {len(odds_movements)} data points."
            ),
            "risk_factors": [
                "Live AI regime classification unavailable",
                "Statistical baseline only — verify with market data",
            ],
        }

    try:
        parsed = json.loads(_strip_fence(raw))
        return {
            "available": True,
            "source": provider,
            "regime": parsed.get("regime", "EFFICIENT"),
            "efficiency_score": float(parsed.get("efficiency_score", 0.5)),
            "sharp_money_signals": parsed.get("sharp_money_signals", []),
            "fade_opportunities": parsed.get("fade_opportunities", []),
            "clv_trend": parsed.get("clv_trend", "STABLE"),
            "recommended_strategy": parsed.get("recommended_strategy", "WAIT"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "narrative": parsed.get("narrative", ""),
            "risk_factors": parsed.get("risk_factors", []),
        }
    except Exception as exc:
        logger.error("market_regime parse error: %s", exc)
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "regime": "EFFICIENT",
            "efficiency_score": 0.65,
            "sharp_money_signals": [],
            "fade_opportunities": [],
            "clv_trend": "STABLE",
            "recommended_strategy": "WAIT",
            "confidence": 0.4,
            "narrative": f"Parse error — defaulting to EFFICIENT regime for {league_label}.",
            "risk_factors": ["Parse error in regime detection"],
        }


# ── 4. Governance Proposal AI Analysis ────────────────────────────────────────

async def analyze_governance_proposal(
    proposal_id: str,
    title: str,
    description: str,
    proposer: str,
    current_votes: Optional[dict] = None,
    token_supply: Optional[float] = None,
) -> dict:
    """
    Analyse a DAO governance proposal and return structured verdict with pros/cons.

    Returns: recommendation, risk assessment, stakeholder impact, vote guidance.
    """
    votes_str = json.dumps(current_votes or {})
    supply_str = f"Total VIT supply: {token_supply:,.0f}" if token_supply else ""

    prompt = f"""You are a blockchain DAO governance analyst for VIT Sports Intelligence Network.

Proposal #{proposal_id}: {title}
Proposer: {proposer}
{supply_str}
Current vote tally: {votes_str}

Description:
{description[:1500]}

Analyse this governance proposal and return ONLY valid JSON:
{{
  "recommendation": "APPROVE|REJECT|ABSTAIN|NEEDS_AMENDMENT",
  "confidence": 0.75,
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "pros": ["pro 1", "pro 2", "pro 3"],
  "cons": ["con 1", "con 2"],
  "stakeholder_impact": {{
    "validators": "positive|neutral|negative — brief",
    "stakers": "positive|neutral|negative — brief",
    "platform": "positive|neutral|negative — brief",
    "token_holders": "positive|neutral|negative — brief"
  }},
  "implementation_complexity": "LOW|MEDIUM|HIGH",
  "suggested_amendments": ["amendment if any"],
  "vote_guidance": "2 sentence guidance for token holders",
  "summary": "3 sentence executive summary"
}}"""

    raw, provider = await _call(prompt, max_tokens=700, temperature=0.2)
    if raw is None:
        vote_for = float((current_votes or {}).get("for", 0))
        vote_against = float((current_votes or {}).get("against", 0))
        vote_total = vote_for + vote_against
        approval_rate = round(vote_for / vote_total, 2) if vote_total > 0 else 0.5
        recommendation = (
            "APPROVE" if approval_rate >= 0.66 else
            "REJECT" if approval_rate <= 0.33 else
            "ABSTAIN"
        )
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "proposal_id": proposal_id,
            "recommendation": recommendation,
            "confidence": 0.4,
            "risk_level": "MEDIUM",
            "pros": [
                "Proposal has been formally submitted through governance process",
                f"Current approval rate: {approval_rate*100:.0f}% based on vote tally",
            ],
            "cons": [
                "Full AI analysis unavailable — statistical assessment only",
                "Independent review recommended before voting",
            ],
            "stakeholder_impact": {
                "validators": "neutral — detailed impact analysis requires live AI",
                "stakers": "neutral — detailed impact analysis requires live AI",
                "platform": "neutral — detailed impact analysis requires live AI",
                "token_holders": "neutral — detailed impact analysis requires live AI",
            },
            "implementation_complexity": "MEDIUM",
            "suggested_amendments": [],
            "vote_guidance": (
                f"VIT Statistical Engine: review the proposal description carefully. "
                f"Current vote tally shows {approval_rate*100:.0f}% approval — "
                f"vote according to your assessment of the platform's best interests."
            ),
            "summary": (
                f"Proposal #{proposal_id} — {title} — submitted by {proposer}. "
                f"Statistical assessment only: {approval_rate*100:.0f}% of current votes are in favour. "
                f"Full AI governance analysis unavailable — consult the DAO forum for community discussion."
            ),
        }

    try:
        parsed = json.loads(_strip_fence(raw))
        return {
            "available": True,
            "source": provider,
            "proposal_id": proposal_id,
            "recommendation": parsed.get("recommendation", "ABSTAIN"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "risk_level": parsed.get("risk_level", "MEDIUM"),
            "pros": parsed.get("pros", []),
            "cons": parsed.get("cons", []),
            "stakeholder_impact": parsed.get("stakeholder_impact", {}),
            "implementation_complexity": parsed.get("implementation_complexity", "MEDIUM"),
            "suggested_amendments": parsed.get("suggested_amendments", []),
            "vote_guidance": parsed.get("vote_guidance", ""),
            "summary": parsed.get("summary", ""),
        }
    except Exception as exc:
        logger.error("governance_proposal parse error: %s", exc)
        return {
            "available": True,
            "source": "vit-statistical-engine",
            "proposal_id": proposal_id,
            "recommendation": "ABSTAIN",
            "confidence": 0.3,
            "risk_level": "MEDIUM",
            "pros": [],
            "cons": ["Parse error — full analysis unavailable"],
            "stakeholder_impact": {},
            "implementation_complexity": "MEDIUM",
            "suggested_amendments": [],
            "vote_guidance": "Parse error — review proposal manually and vote based on community consensus.",
            "summary": f"Parse error for proposal #{proposal_id}. Statistical fallback applied.",
        }
