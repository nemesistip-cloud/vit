# app/services/market_utils.py
# VIT Sports Intelligence Network — v2.1.0
# Fix: Added odds validation to prevent flat 2.75/2.75/2.75 default
# Fix: Added estimate_odds_from_position for when API odds unavailable
# Fix: Added validate_odds_dict helper used by data_loader

import logging
from typing import Dict, Tuple, Optional

from app.config import APP_VERSION

logger = logging.getLogger(__name__)

VERSION = APP_VERSION

# Sane bounds for bookmaker odds
ODDS_MIN = 1.01
ODDS_MAX = 100.0

# Fallback league-average odds (home advantage built in)
_LEAGUE_AVERAGE_ODDS = {
    "premier_league": {"home": 2.20, "draw": 3.35, "away": 3.30},
    "la_liga":        {"home": 2.15, "draw": 3.30, "away": 3.50},
    "bundesliga":     {"home": 2.10, "draw": 3.40, "away": 3.60},
    "serie_a":        {"home": 2.25, "draw": 3.20, "away": 3.40},
    "ligue_1":        {"home": 2.20, "draw": 3.30, "away": 3.45},
    "championship":   {"home": 2.25, "draw": 3.25, "away": 3.20},
    "eredivisie":     {"home": 2.05, "draw": 3.60, "away": 4.20},
    "primeira_liga":  {"home": 2.10, "draw": 3.30, "away": 3.80},
    "scottish_premiership": {"home": 2.40, "draw": 3.20, "away": 2.90},
    "belgian_pro_league": {"home": 2.15, "draw": 3.40, "away": 3.50},
    "default":        {"home": 2.30, "draw": 3.30, "away": 3.10},
}


class MarketUtils:
    """
    Market utility functions for vig removal and edge calculation.

    v2.1.0: Added odds validation and estimation fallbacks so the
    system never silently uses flat 2.75/2.75/2.75 defaults.
    """

    # ------------------------------------------------------------------
    # Odds validation (new in v2.1.0)
    # ------------------------------------------------------------------
    @staticmethod
    def validate_odds(value) -> Optional[float]:
        """
        Return a valid float odds value, or None if invalid.
        Prevents flat 2.75/2.75/2.75 entering the pipeline.
        """
        if value is None:
            return None
        try:
            o = float(value)
            return o if ODDS_MIN <= o <= ODDS_MAX else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def validate_odds_dict(odds: Dict) -> bool:
        """
        Return True if the odds dict is valid and non-degenerate.
        Rejects missing values, out-of-range values, and all-equal odds.
        """
        if not odds:
            return False
        h = MarketUtils.validate_odds(odds.get("home"))
        d = MarketUtils.validate_odds(odds.get("draw"))
        a = MarketUtils.validate_odds(odds.get("away"))
        if h is None or d is None or a is None:
            return False
        # All-equal odds are almost certainly a data error
        if h == d == a:
            return False
        return True

    @staticmethod
    def get_fallback_odds(league: str = "default") -> Dict[str, float]:
        """
        Return league-average odds when no real odds are available.
        Much better than flat 2.75/2.75/2.75.

        v4.10.0: every call is logged at WARNING because it means the live
        odds source failed for this fixture — operators must be able to see
        when the system is running on synthetic odds.
        """
        odds = dict(_LEAGUE_AVERAGE_ODDS.get(league, _LEAGUE_AVERAGE_ODDS["default"]))
        logger.warning(
            "MARKET_ODDS_FALLBACK league=%s — using league-average odds %s "
            "(no valid live odds were supplied)",
            league, odds,
        )
        return odds

    @staticmethod
    def estimate_odds_from_position(
        home_position: Optional[int],
        away_position: Optional[int],
        league_size: int = 20,
        league: str = "default"
    ) -> Dict[str, float]:
        """
        Estimate odds based on league table positions.
        Returns odds that reflect actual home/away strength.

        Used when API odds are unavailable but standings data exists.
        """
        if home_position is None or away_position is None:
            return MarketUtils.get_fallback_odds(league)

        pos_diff = away_position - home_position  # Positive = home is higher ranked

        if pos_diff >= 15:
            return {"home": 1.45, "draw": 4.20, "away": 7.50}
        elif pos_diff >= 10:
            return {"home": 1.65, "draw": 3.80, "away": 5.50}
        elif pos_diff >= 6:
            return {"home": 1.85, "draw": 3.50, "away": 4.20}
        elif pos_diff >= 2:
            return {"home": 2.10, "draw": 3.30, "away": 3.50}
        elif pos_diff >= -2:
            return {"home": 2.40, "draw": 3.20, "away": 2.90}
        elif pos_diff >= -6:
            return {"home": 2.90, "draw": 3.30, "away": 2.40}
        elif pos_diff >= -10:
            return {"home": 4.00, "draw": 3.50, "away": 1.90}
        elif pos_diff >= -15:
            return {"home": 5.50, "draw": 3.80, "away": 1.65}
        else:
            return {"home": 7.50, "draw": 4.20, "away": 1.45}

    # ------------------------------------------------------------------
    # Core probability functions (unchanged from v2.0)
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_implied_probabilities(
        home_odds: float,
        draw_odds: float,
        away_odds: float
    ) -> Dict[str, float]:
        return {
            "home": 1 / home_odds if home_odds > 0 else 0.33,
            "draw": 1 / draw_odds if draw_odds > 0 else 0.33,
            "away": 1 / away_odds if away_odds > 0 else 0.33,
        }

    @staticmethod
    def calculate_overround(
        home_odds: float,
        draw_odds: float,
        away_odds: float
    ) -> float:
        return (1 / home_odds) + (1 / draw_odds) + (1 / away_odds) - 1.0

    @staticmethod
    def remove_vig(
        home_odds: float,
        draw_odds: float,
        away_odds: float
    ) -> Dict[str, float]:
        """Remove vig — returns true market probabilities summing to 1.0"""
        h = 1 / home_odds if home_odds > 0 else 0
        d = 1 / draw_odds if draw_odds > 0 else 0
        a = 1 / away_odds if away_odds > 0 else 0
        total = h + d + a
        if total == 0:
            return {"home": 0.333, "draw": 0.333, "away": 0.333}
        return {"home": h / total, "draw": d / total, "away": a / total}

    @staticmethod
    def calculate_true_edge(
        model_prob: float,
        market_odds: float,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        bet_side: str
    ) -> Tuple[float, float, float]:
        raw_implied  = 1 / market_odds if market_odds > 0 else 0.33
        vig_free     = MarketUtils.remove_vig(home_odds, draw_odds, away_odds)
        vig_free_prob = vig_free.get(bet_side, 0.33)
        raw_edge     = model_prob - raw_implied
        vig_free_edge = model_prob - vig_free_prob
        normalized_edge = (vig_free_edge / vig_free_prob) if vig_free_prob > 0 else 0
        return raw_edge, vig_free_edge, normalized_edge

    @staticmethod
    def calculate_clv(entry_odds: float, closing_odds: float) -> float:
        if closing_odds <= 0:
            return 0.0
        return (entry_odds - closing_odds) / closing_odds

    @staticmethod
    def _remove_vig_two_way(odds_a: float, odds_b: float) -> Tuple[float, float]:
        """Remove bookmaker vig from a 2-way market (BTTS Yes/No, Over/Under)."""
        if odds_a <= 1 or odds_b <= 1:
            return 0.5, 0.5
        ip_a, ip_b = 1 / odds_a, 1 / odds_b
        total = ip_a + ip_b
        if total <= 0:
            return 0.5, 0.5
        return ip_a / total, ip_b / total

    @staticmethod
    def determine_best_bet(
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        min_edge: float = 0.02,
        max_kelly: float = 0.10,
        # v4.6.1: multi-market support — pass any subset; markets without odds are skipped
        over_25_prob: Optional[float] = None,
        under_25_prob: Optional[float] = None,
        over_25_odds: Optional[float] = None,
        under_25_odds: Optional[float] = None,
        btts_prob: Optional[float] = None,
        no_btts_prob: Optional[float] = None,
        btts_yes_odds: Optional[float] = None,
        btts_no_odds: Optional[float] = None,
        # Asian Handicap (v4.6.1)
        ah_line: Optional[float] = None,
        ah_home_prob: Optional[float] = None,
        ah_away_prob: Optional[float] = None,
        ah_home_odds: Optional[float] = None,
        ah_away_odds: Optional[float] = None,
        # Correct Score (v4.6.1) — optional bookmaker odds keyed by "H-A"
        cs_probs: Optional[Dict[str, float]] = None,
        cs_odds: Optional[Dict[str, float]] = None,
    ) -> Dict[str, any]:
        """
        Determine which bet (if any) has the highest edge after vig removal,
        scanning across the 1X2, Over/Under 2.5 and BTTS markets simultaneously.

        v4.6.1: Multi-market scoring. Earlier versions only ranked H/D/A.
        """
        vig_free = MarketUtils.remove_vig(home_odds, draw_odds, away_odds)

        candidates = [
            {
                "market":       "1x2",
                "side":         "home",
                "model_prob":   home_prob,
                "vig_free_prob": vig_free["home"],
                "true_edge":    home_prob - vig_free["home"],
                "raw_edge":     home_prob - (1 / home_odds if home_odds > 0 else 0.33),
                "odds":         home_odds,
            },
            {
                "market":       "1x2",
                "side":         "draw",
                "model_prob":   draw_prob,
                "vig_free_prob": vig_free["draw"],
                "true_edge":    draw_prob - vig_free["draw"],
                "raw_edge":     draw_prob - (1 / draw_odds if draw_odds > 0 else 0.33),
                "odds":         draw_odds,
            },
            {
                "market":       "1x2",
                "side":         "away",
                "model_prob":   away_prob,
                "vig_free_prob": vig_free["away"],
                "true_edge":    away_prob - vig_free["away"],
                "raw_edge":     away_prob - (1 / away_odds if away_odds > 0 else 0.33),
                "odds":         away_odds,
            },
        ]

        # ── Over/Under 2.5 ────────────────────────────────────────────
        if (over_25_prob is not None and over_25_odds and over_25_odds > 1
                and under_25_odds and under_25_odds > 1):
            u_prob = under_25_prob if under_25_prob is not None else max(0.0, 1.0 - float(over_25_prob))
            vf_o, vf_u = MarketUtils._remove_vig_two_way(over_25_odds, under_25_odds)
            candidates.append({
                "market": "over_under_2_5", "side": "over_2_5",
                "model_prob": float(over_25_prob), "vig_free_prob": vf_o,
                "true_edge": float(over_25_prob) - vf_o,
                "raw_edge":  float(over_25_prob) - (1 / over_25_odds),
                "odds":      float(over_25_odds),
            })
            candidates.append({
                "market": "over_under_2_5", "side": "under_2_5",
                "model_prob": float(u_prob), "vig_free_prob": vf_u,
                "true_edge": float(u_prob) - vf_u,
                "raw_edge":  float(u_prob) - (1 / under_25_odds),
                "odds":      float(under_25_odds),
            })

        # ── BTTS Yes/No ───────────────────────────────────────────────
        if (btts_prob is not None and btts_yes_odds and btts_yes_odds > 1
                and btts_no_odds and btts_no_odds > 1):
            n_prob = no_btts_prob if no_btts_prob is not None else max(0.0, 1.0 - float(btts_prob))
            vf_y, vf_n = MarketUtils._remove_vig_two_way(btts_yes_odds, btts_no_odds)
            candidates.append({
                "market": "btts", "side": "btts_yes",
                "model_prob": float(btts_prob), "vig_free_prob": vf_y,
                "true_edge": float(btts_prob) - vf_y,
                "raw_edge":  float(btts_prob) - (1 / btts_yes_odds),
                "odds":      float(btts_yes_odds),
            })
            candidates.append({
                "market": "btts", "side": "btts_no",
                "model_prob": float(n_prob), "vig_free_prob": vf_n,
                "true_edge": float(n_prob) - vf_n,
                "raw_edge":  float(n_prob) - (1 / btts_no_odds),
                "odds":      float(btts_no_odds),
            })

        # ── Asian Handicap (v4.6.1) ───────────────────────────────────
        # Both sides must be priced + at least one model probability provided.
        if (ah_line is not None
                and ah_home_odds and ah_home_odds > 1
                and ah_away_odds and ah_away_odds > 1
                and (ah_home_prob is not None or ah_away_prob is not None)):
            h_p = float(ah_home_prob) if ah_home_prob is not None else max(0.0, 1.0 - float(ah_away_prob))
            a_p = float(ah_away_prob) if ah_away_prob is not None else max(0.0, 1.0 - float(ah_home_prob))
            vf_h, vf_a = MarketUtils._remove_vig_two_way(ah_home_odds, ah_away_odds)
            line_label = f"{ah_line:+g}"
            candidates.append({
                "market": f"ah_{line_label}", "side": f"ah_home_{line_label}",
                "model_prob": h_p, "vig_free_prob": vf_h,
                "true_edge": h_p - vf_h,
                "raw_edge":  h_p - (1 / ah_home_odds),
                "odds":      float(ah_home_odds),
            })
            candidates.append({
                "market": f"ah_{line_label}", "side": f"ah_away_{line_label}",
                "model_prob": a_p, "vig_free_prob": vf_a,
                "true_edge": a_p - vf_a,
                "raw_edge":  a_p - (1 / ah_away_odds),
                "odds":      float(ah_away_odds),
            })

        # ── Correct Score (v4.6.1) ────────────────────────────────────
        # Vig is removed across the priced subset of scorelines.
        if cs_probs and cs_odds:
            priced = {
                lbl: float(o) for lbl, o in cs_odds.items()
                if isinstance(o, (int, float)) and o > 1 and lbl in cs_probs
            }
            if priced:
                inv_total = sum(1.0 / o for o in priced.values()) or 1.0
                for lbl, o in priced.items():
                    p = float(cs_probs[lbl])
                    vf = (1.0 / o) / inv_total
                    candidates.append({
                        "market": "correct_score", "side": f"cs_{lbl}",
                        "model_prob": p, "vig_free_prob": vf,
                        "true_edge": p - vf,
                        "raw_edge":  p - (1 / o),
                        "odds":      o,
                    })

        best = None
        for c in candidates:
            if c["true_edge"] > min_edge:
                if best is None or c["true_edge"] > best["true_edge"]:
                    best = c

        if best:
            b = best["odds"] - 1
            p = best["model_prob"]
            q = 1 - p
            kelly = (b * p - q) / b if b > 0 else 0
            kelly = max(0, min(kelly, max_kelly))

            return {
                "has_edge":      True,
                "best_side":     best["side"],
                "best_market":   best["market"],
                "edge":          best["true_edge"],
                "raw_edge":      best["raw_edge"],
                "vig_free_prob": best["vig_free_prob"],
                "odds":          best["odds"],
                "kelly_stake":   kelly,
                "candidates":    candidates,
            }

        return {
            "has_edge":      False,
            "best_side":     None,
            "best_market":   None,
            "edge":          0,
            "raw_edge":      0,
            "vig_free_prob": 0,
            "odds":          0,
            "kelly_stake":   0,
            "candidates":    candidates,
        }
