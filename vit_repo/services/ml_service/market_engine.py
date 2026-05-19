# services/ml_service/market_engine.py
# VIT Sports Intelligence — Market Engine
# Simulates bookmaker behavior: margins, bias, line movement
# Used for self-play training and hybrid loss computation

import math
import random
from typing import Dict, Optional, Tuple

import numpy as np


class MarketEngine:
    """
    Simulate bookmaker pricing behavior.

    Core responsibilities:
    - Convert true model probabilities → priced decimal odds (margin + bias + noise)
    - Remove vig from market odds to recover implied probabilities
    - Simulate line movement (opening → closing) as information is priced in
    - Compute Closing Line Value (CLV) for bet evaluation
    """

    def __init__(
        self,
        default_margin: float = 0.075,   # 7.5% overround
        home_bias: float = 0.015,         # books shade home slightly
        noise_sd: float = 0.025,          # random pricing noise
        seed: Optional[int] = None,
    ):
        self.default_margin = default_margin
        self.home_bias = home_bias
        self.noise_sd = noise_sd
        self._rng = random.Random(seed)

    # ── Probability → Odds ────────────────────────────────────────────────────
    def generate_odds(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        margin: Optional[float] = None,
        bias: Optional[float] = None,
        noise_sd: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        Convert true outcome probabilities to priced decimal odds.

        Applies:
          1. Home bias (popular team overpriced)
          2. Overround (bookmaker margin)
          3. Gaussian noise (pricing uncertainty)

        Returns {"home": X.XX, "draw": X.XX, "away": X.XX}
        """
        margin   = self.default_margin if margin is None else margin
        bias     = self.home_bias if bias is None else bias
        noise_sd = self.noise_sd if noise_sd is None else noise_sd

        # Normalise input probs
        total = home_prob + draw_prob + away_prob
        if total <= 0:
            home_prob = draw_prob = away_prob = 1/3
        else:
            home_prob /= total; draw_prob /= total; away_prob /= total

        # Apply home bias
        hp_adj = home_prob * (1 + bias)
        dp_adj = draw_prob
        ap_adj = away_prob * (1 - bias * 0.3)
        adj_total = hp_adj + dp_adj + ap_adj
        if adj_total > 0:
            hp_adj /= adj_total; dp_adj /= adj_total; ap_adj /= adj_total

        # Apply margin (overround)
        marg = 1 + margin
        home_odds = max(1.01, (1 / (hp_adj * marg)) * self._rng.gauss(1.0, noise_sd))
        draw_odds = max(1.01, (1 / (dp_adj * marg)) * self._rng.gauss(1.0, noise_sd))
        away_odds = max(1.01, (1 / (ap_adj * marg)) * self._rng.gauss(1.0, noise_sd))

        return {
            "home": round(home_odds, 2),
            "draw": round(draw_odds, 2),
            "away": round(away_odds, 2),
        }

    # ── Odds → Implied Probabilities (with vig removal) ─────────────────────
    @staticmethod
    def vig_free_probs(
        home_odds: float,
        draw_odds: float,
        away_odds: float,
    ) -> Dict[str, float]:
        """
        Remove bookmaker vig and return true market-implied probabilities.
        Method: normalise inverse odds.
        """
        h = 1 / max(1.01, home_odds)
        d = 1 / max(1.01, draw_odds)
        a = 1 / max(1.01, away_odds)
        total = h + d + a
        if total <= 0: total = 1.0
        return {
            "home": round(h / total, 4),
            "draw": round(d / total, 4),
            "away": round(a / total, 4),
        }

    # ── Line movement simulation ──────────────────────────────────────────────
    def simulate_line_movement(
        self,
        opening_odds: Dict[str, float],
        info_factor: float = 0.5,
        model_probs: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Simulate closing odds from opening odds.

        info_factor: how much "information" gets priced in (0=none, 1=full)
        model_probs: if provided, used as the informed signal (e.g. sharp money)
        """
        if model_probs is None:
            # Random drift (no information)
            drift = self._rng.gauss(0, 0.04 * info_factor)
            return {
                "home": max(1.01, round(opening_odds["home"] * (1 + drift), 2)),
                "draw": max(1.01, round(opening_odds["draw"] * (1 + self._rng.gauss(0, 0.03)), 2)),
                "away": max(1.01, round(opening_odds["away"] * (1 - drift), 2)),
            }

        # Blend opening toward informed probs
        open_probs = self.vig_free_probs(
            opening_odds["home"], opening_odds["draw"], opening_odds["away"]
        )
        blended = {
            k: open_probs[k] * (1 - info_factor) + model_probs.get(k, open_probs[k]) * info_factor
            for k in ["home", "draw", "away"]
        }
        return self.generate_odds(
            blended["home"], blended["draw"], blended["away"],
            margin=self.default_margin * 0.80,   # tighter at close
            noise_sd=self.noise_sd * 0.4,
        )

    # ── Closing Line Value (CLV) ──────────────────────────────────────────────
    @staticmethod
    def compute_clv(
        bet_odds: float,
        closing_odds: float,
    ) -> float:
        """
        CLV = (bet_odds / closing_odds) - 1
        Positive CLV means you beat the closing line — long-run edge signal.
        """
        if closing_odds <= 1.0:
            return 0.0
        return round((bet_odds / closing_odds) - 1.0, 4)

    # ── Hybrid loss components ────────────────────────────────────────────────
    @staticmethod
    def hybrid_loss(
        model_probs: Dict[str, float],
        actual_result: str,
        closing_probs: Dict[str, float],
        alpha: float = 0.7,
        beta: float = 0.3,
    ) -> float:
        """
        Hybrid objective: Loss = α × prediction_error + β × market_error

        prediction_error: log-loss vs actual result
        market_error:     KL divergence from model to market (closing line)

        alpha + beta should sum to 1.0 (but not enforced).
        """
        result_map = {"H": "home", "D": "draw", "A": "away"}
        outcome_key = result_map.get(actual_result, "home")

        # Prediction log-loss
        p_correct = max(1e-6, model_probs.get(outcome_key, 1/3))
        prediction_error = -math.log(p_correct)

        # Market KL divergence (model || market)
        market_error = 0.0
        for k in ["home", "draw", "away"]:
            p = max(1e-6, model_probs.get(k, 1/3))
            q = max(1e-6, closing_probs.get(k, 1/3))
            market_error += p * math.log(p / q)

        return round(alpha * prediction_error + beta * market_error, 6)

    # ── Expected value calculation ────────────────────────────────────────────
    @staticmethod
    def expected_value(
        model_prob: float,
        decimal_odds: float,
    ) -> float:
        """EV = model_prob × (odds - 1) - (1 - model_prob)"""
        return round(model_prob * (decimal_odds - 1) - (1 - model_prob), 4)

    # ── Edge detection ────────────────────────────────────────────────────────
    def detect_edge(
        self,
        model_probs: Dict[str, float],
        market_odds: Dict[str, float],
        threshold: float = 0.02,
    ) -> Optional[Dict]:
        """
        Return the best edge if above threshold, else None.
        edge = model_prob - implied_market_prob
        """
        implied = self.vig_free_probs(market_odds["home"], market_odds["draw"], market_odds["away"])
        edges = {
            "home": model_probs.get("home", 1/3) - implied["home"],
            "draw": model_probs.get("draw", 1/3) - implied["draw"],
            "away": model_probs.get("away", 1/3) - implied["away"],
        }
        best_outcome = max(edges, key=edges.get)
        best_edge = edges[best_outcome]
        if best_edge < threshold:
            return None

        odds_map = {"home": market_odds["home"], "draw": market_odds["draw"], "away": market_odds["away"]}
        prob_map = {"home": model_probs.get("home", 1/3), "draw": model_probs.get("draw", 1/3), "away": model_probs.get("away", 1/3)}

        return {
            "outcome": best_outcome,
            "edge": round(best_edge, 4),
            "model_prob": round(prob_map[best_outcome], 4),
            "market_prob": round(implied[best_outcome], 4),
            "odds": odds_map[best_outcome],
            "ev": self.expected_value(prob_map[best_outcome], odds_map[best_outcome]),
        }

    # ── Vig percentage ────────────────────────────────────────────────────────
    @staticmethod
    def vig_pct(home_odds: float, draw_odds: float, away_odds: float) -> float:
        """Return overround as a percentage."""
        total = 1/home_odds + 1/draw_odds + 1/away_odds
        return round((total - 1.0) * 100, 2)
