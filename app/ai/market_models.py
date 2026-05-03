"""
app/ai/market_models.py — Phase 2: Specialized Market Models

Dedicated neural network architectures for:
  - BTTS (Both Teams To Score)
  - Over/Under 2.5 goals
  - Correct Score (top-N probability matrix)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Optional


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

class _ResidualBlock(nn.Module):
    """Simple residual block for deeper market models."""
    def __init__(self, size: int, dropout: float = 0.2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(size, size),
            nn.LayerNorm(size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(size, size),
            nn.LayerNorm(size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.gelu(x + self.net(x))


# ---------------------------------------------------------------------------
# Phase 2a — BTTS Model
# ---------------------------------------------------------------------------

class BTTSModel(nn.Module):
    """
    Specialised binary classifier for Both Teams To Score.

    Key input features:
      - xG attack/defence stats for both teams
      - Form GF/GA per game
      - H2H BTTS rate
      - Poisson lambda estimates
      - Referee discipline index (many cards → open game)
      - Market BTTS odds implied probability

    Output: [P(btts_no), P(btts_yes)]  (softmax)
    """
    MODEL_KEY = "btts_v2"

    def __init__(self, input_size: int = 32, hidden_size: int = 128, dropout: float = 0.25):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.res1 = _ResidualBlock(hidden_size, dropout)
        self.res2 = _ResidualBlock(hidden_size, dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.GELU(),
            nn.Linear(32, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.stem(x)
        h = self.res1(h)
        h = self.res2(h)
        return self.head(h)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Return softmax probabilities [P(no), P(yes)]."""
        with torch.no_grad():
            return F.softmax(self.forward(x), dim=-1)


# ---------------------------------------------------------------------------
# Phase 2b — Over/Under Model
# ---------------------------------------------------------------------------

class OverUnderModel(nn.Module):
    """
    Specialised classifier for goal totals market.

    Outputs 5-class distribution over common goal bands:
      0: 0–1 goals   (under 2)
      1: exactly 2   (under 2.5 but over 1.5)
      2: exactly 3
      3: 4–5 goals
      4: 6+  goals

    This allows computing P(over N.5) for any N by summing the tail.

    Key additional features vs the main model:
      - lambda_home / lambda_away (Poisson estimates)
      - xG total expected
      - poisson_over25_prob
      - Referee fouls/penalty rate (high activity → more goals)
    """
    MODEL_KEY = "over_under_v2"

    # Map class index → actual goals range for UI display
    CLASS_LABELS = ["0–1", "2", "3", "4–5", "6+"]

    def __init__(self, input_size: int = 36, hidden_size: int = 128, dropout: float = 0.2):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.res1 = _ResidualBlock(hidden_size, dropout)
        self.res2 = _ResidualBlock(hidden_size, dropout)
        self.res3 = _ResidualBlock(hidden_size, dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(64, 5),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.stem(x)
        h = self.res1(h)
        h = self.res2(h)
        h = self.res3(h)
        return self.head(h)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return F.softmax(self.forward(x), dim=-1)

    def over_n5_prob(self, x: torch.Tensor, n: float = 2.5) -> float:
        """Compute P(total goals > n) from the 5-class distribution."""
        proba = self.predict_proba(x).squeeze()
        # Band lower bounds: 0, 2, 3, 4, 6
        band_mins = [0, 2, 3, 4, 6]
        # P(goals > n) = sum of bands whose lower bound >= ceil(n)
        threshold = int(n) + 1
        total = 0.0
        for i, lower in enumerate(band_mins):
            if lower >= threshold:
                total += proba[i].item()
            elif lower < threshold and i + 1 < len(band_mins) and band_mins[i + 1] > threshold:
                # Partial overlap — approximate 50% of the band
                total += proba[i].item() * 0.5
        return round(min(1.0, max(0.0, total)), 4)


# ---------------------------------------------------------------------------
# Phase 2c — Correct Score Model
# ---------------------------------------------------------------------------

class CorrectScoreModel(nn.Module):
    """
    Score probability matrix model outputting probabilities for the
    most common exact scores (home 0–4, away 0–4 = 25 classes + 'other').

    Output: 26-class softmax
    """
    MODEL_KEY = "correct_score_v2"

    # 25 explicit scores + catch-all "other"
    SCORE_CLASSES: List[str] = [
        f"{h}-{a}" for h in range(5) for a in range(5)
    ] + ["other"]

    N_CLASSES = 26

    def __init__(self, input_size: int = 40, hidden_size: int = 192, dropout: float = 0.25):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.res1 = _ResidualBlock(hidden_size, dropout)
        self.res2 = _ResidualBlock(hidden_size, dropout)
        self.res3 = _ResidualBlock(hidden_size, dropout)
        self.res4 = _ResidualBlock(hidden_size, dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden_size, 96),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(96, self.N_CLASSES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.stem(x)
        h = self.res1(h)
        h = self.res2(h)
        h = self.res3(h)
        h = self.res4(h)
        return self.head(h)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return F.softmax(self.forward(x), dim=-1)

    def top_scores(self, x: torch.Tensor, n: int = 5) -> List[dict]:
        """Return top-N most probable exact scores with probabilities."""
        proba = self.predict_proba(x).squeeze().tolist()
        ranked = sorted(
            zip(self.SCORE_CLASSES, proba),
            key=lambda t: t[1],
            reverse=True,
        )
        return [{"score": s, "probability": round(p, 4)} for s, p in ranked[:n]]


# ---------------------------------------------------------------------------
# Feature vector builders for each market model
# ---------------------------------------------------------------------------

_BTTS_FEATURE_KEYS = [
    "home_xg_per_game", "away_xg_per_game",
    "home_xg_against_per_game", "away_xg_against_per_game",
    "home_form_gf", "home_form_ga", "away_form_gf", "away_form_ga",
    "home_form_games", "away_form_games",
    "h2h_btts_rate", "h2h_avg_goals",
    "poisson_btts_prob", "poisson_over25_prob",
    "lambda_home", "lambda_away",
    "ref_discipline_index", "ref_fouls_per_game",
    "market_btts_prob_vf", "market_over25_prob_vf",
    "home_injury_score", "away_injury_score",
    "home_rest_days", "away_rest_days",
    "xg_total_expected", "home_shots_per_game", "away_shots_per_game",
    "home_shot_accuracy", "away_shot_accuracy",
    "home_form_ppg", "away_form_ppg",
    "injury_balance",
]

_OU_FEATURE_KEYS = [
    "home_xg_per_game", "away_xg_per_game",
    "home_xg_against_per_game", "away_xg_against_per_game",
    "lambda_home", "lambda_away",
    "xg_total_expected", "poisson_over25_prob",
    "home_form_gf", "home_form_ga", "away_form_gf", "away_form_ga",
    "home_form_games", "away_form_games",
    "h2h_avg_goals", "h2h_btts_rate",
    "market_over25_prob_vf", "market_btts_prob_vf",
    "ref_fouls_per_game", "ref_penalty_rate_per_game",
    "home_injury_score", "away_injury_score",
    "home_rest_days", "away_rest_days",
    "home_shots_per_game", "away_shots_per_game",
    "steam_home", "steam_away",
    "odds_drift_home", "odds_drift_away",
    "odds_velocity_total",
    "home_form_ppg", "away_form_ppg",
    "home_goal_threat", "away_goal_threat",
    "injury_balance",
]

_CS_FEATURE_KEYS = [
    "home_xg_per_game", "away_xg_per_game",
    "home_xg_against_per_game", "away_xg_against_per_game",
    "lambda_home", "lambda_away",
    "xg_total_expected", "xg_dominance",
    "home_form_gf", "home_form_ga", "away_form_gf", "away_form_ga",
    "home_form_games", "away_form_games",
    "h2h_home_win_rate", "h2h_draw_rate", "h2h_away_win_rate",
    "h2h_avg_goals", "h2h_btts_rate",
    "market_home_prob_vf", "market_draw_prob_vf", "market_away_prob_vf",
    "market_over25_prob_vf", "market_btts_prob_vf",
    "home_position", "away_position", "position_gap",
    "ref_fouls_per_game", "ref_yellows_per_game",
    "home_injury_score", "away_injury_score",
    "home_rest_days", "away_rest_days",
    "home_shots_per_game", "away_shots_per_game",
    "home_form_ppg", "away_form_ppg",
    "home_goal_threat", "away_goal_threat",
]


def build_feature_vector(
    feature_dict: dict,
    keys: List[str],
    default: float = 0.0,
) -> torch.Tensor:
    """Convert a flat feature dict into a float32 tensor using ordered keys."""
    vec = []
    for k in keys:
        v = feature_dict.get(k)
        try:
            vec.append(float(v) if v is not None else default)
        except (TypeError, ValueError):
            vec.append(default)
    return torch.tensor(vec, dtype=torch.float32).unsqueeze(0)


def build_btts_vector(features: dict) -> torch.Tensor:
    return build_feature_vector(features, _BTTS_FEATURE_KEYS)


def build_ou_vector(features: dict) -> torch.Tensor:
    return build_feature_vector(features, _OU_FEATURE_KEYS)


def build_cs_vector(features: dict) -> torch.Tensor:
    return build_feature_vector(features, _CS_FEATURE_KEYS)
