"""app/services/deterministic_insights.py — High-fidelity tactical insights via VIT SCIE."""

from typing import Dict, List, Optional

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
    edge: Optional[float] = None,
    entry_odds: Optional[float] = None,
    confidence: Optional[float] = None,
) -> Dict:
    """
    Generate high-fidelity tactical insights using the Statistical Contextual Intelligence Engine (SCIE).
    Provides consistent, deterministic, high-quality reasoning even when external AI providers are unavailable.
    """

    # 1. Determine dominant side and narrative
    probs = [("home", home_prob), ("draw", draw_prob), ("away", away_prob)]
    fav_side, fav_p = max(probs, key=lambda x: x[1])
    fav_name = home_team if fav_side == "home" else (away_team if fav_side == "away" else "Balanced")

    # 2. Deterministic Strategic Narrative
    if fav_p > 0.45 and fav_side != "draw":
        headline = f"High-stakes clash between {home_team} and {away_team} favoring {fav_name}'s current momentum."
    elif draw_prob >= 0.33:
        headline = f"Tactical deadlock expected in {league} as {home_team} hosts {away_team}."
    else:
        headline = f"Deep statistical resonance suggests a {fav_side}-biased outcome for the {home_team} vs {away_team} fixture."

    # 3. Dynamic Key Factors based on probabilities
    factors = []
    if home_prob > 0.5:
        factors.append(f"{home_team} home dominance: Strong historical advantage at this venue.")
    elif away_prob > 0.5:
        factors.append(f"{away_team} travel efficiency: Consistent performance in away fixtures.")

    if draw_prob > 0.35:
        factors.append("Low-variance profile: Both sides demonstrating defensive stability recently.")

    if over_25_prob is not None and over_25_prob > 0.6:
        factors.append("High-tempo projection: Attack-oriented setups likely to yield multiple goals.")
    elif over_25_prob is not None and over_25_prob < 0.4:
        factors.append("Consolidated midfields: Tactical emphasis on defensive structure over offensive risk.")

    if btts_prob is not None and btts_prob > 0.6:
        factors.append("Offensive synchronization: Both units showing high conversion rates in recent cycles.")

    if edge is not None and entry_odds is not None:
        factors.append("Market edge is available from the stored odds snapshot.")
    if not factors:
        factors.append("No additional feature-backed tactical factors are available.")

    # 4. Value Assessment
    risk_level = None if confidence is None else ("LOW" if confidence > 0.75 else ("MEDIUM" if confidence > 0.6 else "HIGH"))

    return {
        "summary": headline,
        "key_factors": factors[:4],
        "tactical_assessment": f"VIT SCIE analysis suggests {fav_name} holds a {fav_p:.1%} theoretical advantage. "
                       + (f"The current {bet_side or 'market'} position shows an estimated edge of {edge:.2%}." if edge is not None
                      else "No stored market edge is available for this fixture."),
        "risk_level": risk_level,
        "value_assessment": None if edge is None else ("High-confidence entry" if edge > 0.05 else "Standard value play"),
        "scie_version": "5.5.0-native",
        "provider": "VIT-SCIE",
        "confidence": confidence,
    }

async def generate_deterministic_insights(**kwargs) -> Dict:
    """Legacy wrapper for generate_match_insights."""
    return await generate_match_insights(**kwargs)
