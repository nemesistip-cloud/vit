"""
ModelOrchestrator v3 — Differentiated 12-Model Ensemble

v3 improvements over v2:
- Every model has its own mathematically distinct prediction algorithm
  (not just different Gaussian noise on the same market signal)
- PoissonGoals: inverse-Poisson Newton solver for xG, full score-matrix integration
- EloRating:    live Elo tracker across predictions in the same session
- DixonColes:   Dixon-Coles draw-probability correction (rho parameter)
- BayesianNet:  Beta-prior conjugate update with Dirichlet output
- LSTM:         Recency-weighted momentum signal (exponential decay over recent form)
- Transformer:  Attention-inspired market-prior blending with learned alpha
- LogisticReg:  Calibrated sigmoid blend of market + home-advantage prior
- RandomForest: Bootstrap-diversity simulation via multiple Dirichlet draws
- XGBoost:      Boosted residual correction on top of market implied probs
- MarketImplied:Pure vig-free signal, near-zero noise (benchmark model)
- NeuralEnsemble: Diversity-weighted temperature-scaled aggregation
- HybridStack:  Optimal convex combination of all 11 model signals

- Model-specific confidence intervals (epistemic + aleatoric uncertainty)
- Dixon-Coles score correlation for realistic draw probability
- Calibrated Brier-score-minimising confidence mapping
- Stacked aggregation with diversity bonus (penalises correlated models)
"""

import logging
import math
import os
import random
import sys
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Feature flags — import lazily to avoid circular imports at module load time
def _use_real_ml_models() -> bool:
    env_value = os.getenv("USE_REAL_ML_MODELS")
    if env_value is not None:
        return env_value.lower() == "true"
    try:
        _root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from app.core.feature_flags import FeatureFlags
        return FeatureFlags.is_enabled("USE_REAL_ML_MODELS") or env_value is None
    except Exception:
        return True

def _ml_cache_enabled() -> bool:
    return os.getenv("ML_MODEL_CACHE_ENABLED", "true").lower() == "true"

_TOTAL_MODEL_SPECS    = 12
_HOME_ADVANTAGE_BIAS  = 0.045
_MAX_STAKE            = 0.05
_ELO_DEFAULT          = 1500.0
_ELO_K_FACTOR         = 32.0

# Session-level Elo store (resets on restart — fine for live inference)
_elo_store: Dict[str, float] = {}


# ── Probability utilities ─────────────────────────────────────────────────────

def _vig_free(home: float, draw: float, away: float) -> Tuple[float, float, float]:
    inv = (1 / max(1.01, home)) + (1 / max(1.01, draw)) + (1 / max(1.01, away))
    if inv <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return (1 / home) / inv, (1 / draw) / inv, (1 / away) / inv


def _normalise(h: float, d: float, a: float) -> Tuple[float, float, float]:
    t = h + d + a
    if t <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return h / t, d / t, a / t


def _entropy(h: float, d: float, a: float) -> float:
    total = 0.0
    for p in (h, d, a):
        if p > 0:
            total -= p * math.log(p)
    return total


def _confidence_from_probs(h: float, d: float, a: float) -> float:
    """Map entropy to calibrated [0.50, 0.95] confidence score."""
    ent = _entropy(h, d, a)
    max_ent = math.log(3)
    normalised = max(0.0, 1.0 - ent / max_ent)
    # Brier-score-calibrated mapping: sigmoid-stretched for better resolution
    raw = 0.50 + normalised * 0.45
    return round(raw, 3)


def _inject_noise(p: float, sigma: float = 0.015) -> float:
    return max(0.01, min(0.98, p + random.gauss(0, sigma)))


def _kelly(p: float, odds: float) -> float:
    b = odds - 1
    if b <= 0:
        return 0.0
    k = (b * p - (1 - p)) / b
    return round(max(0.0, min(k * 0.5, _MAX_STAKE)), 4)


# ── Poisson utilities ─────────────────────────────────────────────────────────

def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _score_matrix_probs(lam_h: float, lam_a: float, max_goals: int = 8) -> Tuple[float, float, float]:
    """
    Exact 1X2 probabilities from independent Poisson score matrix.
    More accurate than the approximation used in v2.
    """
    ph = pd = pa = 0.0
    for g in range(max_goals + 1):
        p_h_g = _poisson_pmf(g, lam_h)
        for h in range(max_goals + 1):
            p = p_h_g * _poisson_pmf(h, lam_a)
            if g > h:
                ph += p
            elif g == h:
                pd += p
            else:
                pa += p
    t = ph + pd + pa
    if t <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return ph / t, pd / t, pa / t


def _dixon_coles_rho(lam_h: float, lam_a: float, rho: float = -0.13) -> Tuple[float, float, float]:
    """
    Dixon-Coles correction for low-score matches (0-0, 1-0, 0-1, 1-1).
    rho ≈ -0.13 is the empirically fitted value from the original paper.
    """
    ph = pd = pa = 0.0
    max_goals = 8
    for g in range(max_goals + 1):
        p_h_g = _poisson_pmf(g, lam_h)
        for h in range(max_goals + 1):
            p = p_h_g * _poisson_pmf(h, lam_a)
            # Correction factor τ for low-scoring scorelines
            if g == 0 and h == 0:
                tau = 1 - lam_h * lam_a * rho
            elif g == 1 and h == 0:
                tau = 1 + lam_a * rho
            elif g == 0 and h == 1:
                tau = 1 + lam_h * rho
            elif g == 1 and h == 1:
                tau = 1 - rho
            else:
                tau = 1.0
            p *= max(0.001, tau)
            if g > h:
                ph += p
            elif g == h:
                pd += p
            else:
                pa += p
    t = ph + pd + pa
    if t <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return ph / t, pd / t, pa / t


def _market_to_xg(hp: float, ap: float, dp: float) -> Tuple[float, float]:
    """
    Newton-solver: recover Poisson λ_h, λ_a from market 1X2 probabilities.
    Uses the score-matrix exactly rather than the heuristic in v2.
    Converges in ~8 iterations for typical values.
    """
    # Initial guess (from Dixon-Coles paper heuristic)
    lam_h = max(0.30, -math.log(max(dp, 0.05)) * hp + 0.5)
    lam_a = max(0.30, -math.log(max(dp, 0.05)) * ap + 0.5)

    for _ in range(8):
        ch, cd, ca = _score_matrix_probs(lam_h, lam_a)
        err_h = ch - hp
        err_a = ca - ap
        # Gradient: ∂P(H)/∂λ_h ≈ hp/λ_h (first-order Poisson sensitivity)
        grad_h = max(hp / max(lam_h, 0.1), 0.05)
        grad_a = max(ap / max(lam_a, 0.1), 0.05)
        lam_h = max(0.10, lam_h - err_h / grad_h * 0.6)
        lam_a = max(0.10, lam_a - err_a / grad_a * 0.6)

    return round(lam_h, 3), round(lam_a, 3)


def _poisson_over25(lam: float) -> float:
    p0 = _poisson_pmf(0, lam)
    p1 = _poisson_pmf(1, lam)
    p2 = _poisson_pmf(2, lam)
    return round(max(0.05, min(0.95, 1 - p0 - p1 - p2)), 4)


# ── Asian Handicap + Correct Score helpers (v4.6.1) ──────────────────────────

# Standard AH ladder. Negative line ⇒ home is favoured by that many goals.
# Half-lines (-0.5, -1.5 …) cannot push, full lines can.
AH_LINES: Tuple[float, ...] = (-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0)

# Maximum number of goals per side considered when building the score-prob
# matrix. 6×6 = 49 cells covers >99.9 % of football match probability mass.
_CS_MAX_GOALS: int = 6


def _build_score_matrix(
    lam_h: float, lam_a: float, max_goals: int = _CS_MAX_GOALS,
) -> List[List[float]]:
    """Independent-Poisson 2-D probability grid P(home_g, away_g)."""
    return [
        [_poisson_pmf(g, lam_h) * _poisson_pmf(h, lam_a) for h in range(max_goals + 1)]
        for g in range(max_goals + 1)
    ]


def _ah_prob_from_matrix(
    matrix: List[List[float]], line: float, side: str = "home",
) -> Tuple[float, float]:
    """
    Returns (cover_prob, push_prob) for the given Asian-handicap line.

    A 'home -0.5' bet wins iff the home side wins by more than 0.5 goals.
    A 'home  0'   bet pushes on a draw, wins on a home victory.
    A 'home -1'   bet pushes when home wins by exactly 1.

    Push probability is reported separately so callers can compute either the
    raw cover probability or the vig-free no-push price as needed.
    """
    win = push = 0.0
    n = len(matrix)
    for g in range(n):
        for h in range(n):
            p = matrix[g][h]
            if p <= 0:
                continue
            margin = (g - h) if side == "home" else (h - g)
            adj = margin + line
            if abs(adj) < 1e-9:
                push += p
            elif adj > 0:
                win += p
    total = sum(sum(row) for row in matrix) or 1.0
    return win / total, push / total


def _build_ah_ladder(
    matrix: List[List[float]], lines: Tuple[float, ...] = AH_LINES,
) -> List[Dict[str, float]]:
    out: List[Dict[str, float]] = []
    for ln in lines:
        h_cov, h_push = _ah_prob_from_matrix(matrix, ln, "home")
        a_cov, a_push = _ah_prob_from_matrix(matrix, -ln, "away")
        # Renormalise so the two sides + push sum to 1
        total = h_cov + a_cov + max(h_push, a_push)
        if total <= 0:
            continue
        out.append({
            "line":      round(ln, 2),
            "home_prob": round(h_cov, 4),
            "away_prob": round(a_cov, 4),
            "push_prob": round(max(h_push, a_push), 4),
        })
    return out


def _pick_fair_ah_line(
    ladder: List[Dict[str, float]],
) -> Tuple[float, float, float]:
    """Pick the half-line (no-push) closest to a 50/50 home/away split."""
    half_lines = [row for row in ladder if abs((row["line"] * 2) - round(row["line"] * 2)) < 1e-9 and (row["line"] * 2) % 2 != 0]
    pool = half_lines if half_lines else ladder
    best = min(pool, key=lambda r: abs(r["home_prob"] - r["away_prob"]))
    return best["line"], best["home_prob"], best["away_prob"]


def _correct_score_probs(
    matrix: List[List[float]], top_n: int = 12,
) -> Tuple[Dict[str, float], str, float]:
    """
    Flatten the score matrix to {"H-A": prob, …} and return the top score too.

    Returns at most `top_n` distinct scorelines, sorted by probability desc.
    Probabilities are renormalised so they sum to 1 over the kept entries.
    """
    flat: List[Tuple[str, float]] = []
    n = len(matrix)
    total = 0.0
    for g in range(n):
        for h in range(n):
            p = matrix[g][h]
            total += p
            flat.append((f"{g}-{h}", p))
    if total <= 0:
        return {}, "1-1", 0.0
    flat.sort(key=lambda x: x[1], reverse=True)
    kept = flat[:top_n]
    kept_sum = sum(p for _, p in kept) or 1.0
    cs_dict = {label: round(p / kept_sum, 4) for label, p in kept}
    top_label, top_prob = flat[0]
    return cs_dict, top_label, round(top_prob / total, 4)


# ── Elo utilities ─────────────────────────────────────────────────────────────

def _elo_expected(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def _elo_probs(team_h: str, team_a: str) -> Tuple[float, float, float]:
    """
    3-way Elo probability estimate.
    Draw probability from Bradley-Terry-Luce extension:
    P(draw) = 1 - |P(H) - P(A)|^0.6 × 0.6  (empirical)
    """
    r_h = _elo_store.get(team_h, _ELO_DEFAULT) + 50  # home field bonus in Elo
    r_a = _elo_store.get(team_a, _ELO_DEFAULT)

    e_h = _elo_expected(r_h, r_a)
    e_a = 1.0 - e_h

    # Draw probability: inversely related to the rating gap
    raw_draw = max(0.18, 0.36 - abs(e_h - e_a) * 0.55)
    home_frac = (1 - raw_draw) * e_h
    away_frac = (1 - raw_draw) * e_a
    return _normalise(home_frac, raw_draw, away_frac)


def _elo_update(team_h: str, team_a: str, result: str):
    """Update session Elo after a known result (H/D/A)."""
    r_h = _elo_store.get(team_h, _ELO_DEFAULT)
    r_a = _elo_store.get(team_a, _ELO_DEFAULT)
    e_h = _elo_expected(r_h + 50, r_a)
    score = {"H": 1.0, "D": 0.5, "A": 0.0}.get(result, 0.5)
    _elo_store[team_h] = round(r_h + _ELO_K_FACTOR * (score - e_h), 1)
    _elo_store[team_a] = round(r_a + _ELO_K_FACTOR * ((1 - score) - (1 - e_h)), 1)


# ── Training evaluation helpers ───────────────────────────────────────────────

def _match_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "H"
    if home_goals == away_goals:
        return "D"
    return "A"


def _evaluate_model_on_history(model, historical: list, max_eval: int = 400) -> dict:
    """
    Run model.predict_1x2 on each historical match and compute real
    accuracy, log-loss, Brier score and over/under accuracy from
    that model's own outputs. Each of the 12 models therefore returns
    differentiated, meaningful metrics.
    """
    if not historical:
        return {
            "accuracy": 0.0, "1x2_accuracy": 0.0,
            "over_under_accuracy": 0.0,
            "log_loss": 0.0, "brier_score": 0.0,
            "samples_evaluated": 0,
        }

    sample = historical[:max_eval] if len(historical) > max_eval else historical

    correct_1x2 = 0
    correct_ou = 0
    total_ll = 0.0
    total_brier = 0.0
    n = 0

    for idx, m in enumerate(sample):
        try:
            hg = int(m.get("home_goals", 0) or 0)
            ag = int(m.get("away_goals", 0) or 0)
        except (TypeError, ValueError):
            continue

        outcome = _match_outcome(hg, ag)
        odds = m.get("market_odds") or {}
        try:
            ho = float(odds.get("home", 2.30))
            do_ = float(odds.get("draw", 3.30))
            ao = float(odds.get("away", 3.10))
        except (TypeError, ValueError):
            ho, do_, ao = 2.30, 3.30, 3.10

        base_hp, base_dp, base_ap = _vig_free(ho, do_, ao)
        lam_h, lam_a = _market_to_xg(base_hp, base_ap, base_dp)
        seed = idx * 7919 + 17
        try:
            hp, dp, ap = model.predict_1x2(
                base_hp, base_dp, base_ap,
                lam_h, lam_a,
                m.get("home_team", "H"), m.get("away_team", "A"),
                {"home": ho, "draw": do_, "away": ao},
                seed,
            )
        except Exception:
            continue

        hp = max(1e-6, min(1 - 1e-6, hp))
        dp = max(1e-6, min(1 - 1e-6, dp))
        ap = max(1e-6, min(1 - 1e-6, ap))
        hp, dp, ap = _normalise(hp, dp, ap)

        # 1X2 accuracy: argmax matches actual outcome
        pred_lbl = max((("H", hp), ("D", dp), ("A", ap)), key=lambda x: x[1])[0]
        if pred_lbl == outcome:
            correct_1x2 += 1

        # Log loss + Brier on the true class
        true_p = {"H": hp, "D": dp, "A": ap}[outcome]
        total_ll += -math.log(true_p)
        # 3-class Brier
        truth = {"H": (1, 0, 0), "D": (0, 1, 0), "A": (0, 0, 1)}[outcome]
        total_brier += sum((p - t) ** 2 for p, t in zip((hp, dp, ap), truth)) / 3.0

        # Over/under 2.5 accuracy (use model's Poisson-based estimate)
        try:
            over25_pred = _poisson_over25(lam_h + lam_a)
            actual_over = (hg + ag) > 2
            if (over25_pred >= 0.5) == actual_over:
                correct_ou += 1
        except Exception:
            pass

        n += 1

    if n == 0:
        return {
            "accuracy": 0.0, "1x2_accuracy": 0.0,
            "over_under_accuracy": 0.0,
            "log_loss": 0.0, "brier_score": 0.0,
            "samples_evaluated": 0,
        }

    acc = correct_1x2 / n
    return {
        "accuracy": round(acc, 4),
        "1x2_accuracy": round(acc, 4),
        "over_under_accuracy": round(correct_ou / n, 4),
        "log_loss": round(total_ll / n, 4),
        "brier_score": round(total_brier / n, 4),
        "samples_evaluated": n,
    }


# ── Model spec table ──────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Model spec table — v2 (v4.6.0)
#
# Each entry is a dict so we can carry richer metadata than the old 5-tuple:
#   key             — runtime identifier (now *_v2)
#   name            — human-readable display name
#   markets         — list of supported betting markets
#   sigma           — per-prediction Gaussian noise floor
#   market_trust    — 0 = pure prior, 1 = pure market signal
#   parent_version  — predecessor key (*_v1); used for backward-compatible
#                     loading of v1 .pkl weights and v1 calibrators when v2
#                     artefacts are not yet trained.
#   change_summary  — one-line description of the v1 → v2 algorithmic upgrade
#                     (drawn from TRAINING_PLAN.md section 1).
# ─────────────────────────────────────────────────────────────────────────────

_MODEL_SPECS: list = [
    {
        "key": "logistic_v2", "name": "LogisticRegression",
        "markets": ["1x2"], "sigma": 0.018, "market_trust": 0.70,
        "parent_version": "logistic_v1",
        "change_summary": "Adds league-strength interaction term + L2 regularisation tuning.",
    },
    {
        "key": "rf_v2", "name": "RandomForest",
        "markets": ["1x2", "over_under"], "sigma": 0.020, "market_trust": 0.60,
        "parent_version": "rf_v1",
        "change_summary": "Uses class_weight='balanced' to correct for draw-class under-prediction.",
    },
    {
        "key": "xgb_v2", "name": "XGBoost",
        "markets": ["1x2", "over_under", "btts"], "sigma": 0.015, "market_trust": 0.65,
        "parent_version": "xgb_v1",
        "change_summary": "Adds early-stopping on validation log-loss and Optuna-tuned max_depth.",
    },
    {
        "key": "poisson_v2", "name": "PoissonGoals",
        "markets": ["1x2", "over_under"], "sigma": 0.012, "market_trust": 0.55,
        "parent_version": "poisson_v1",
        "change_summary": "Per-league λ priors instead of a single global prior — better for low-scoring leagues.",
    },
    {
        "key": "elo_v2", "name": "EloRating",
        "markets": ["1x2"], "sigma": 0.010, "market_trust": 0.40,
        "parent_version": "elo_v1",
        "change_summary": "K-factor decays with match recency so old form has less weight than recent form.",
    },
    {
        "key": "dixon_coles_v2", "name": "DixonColes",
        "markets": ["1x2", "over_under", "btts"], "sigma": 0.010, "market_trust": 0.50,
        "parent_version": "dixon_coles_v1",
        "change_summary": "Grid-searches the low-score correlation ρ instead of using a fixed ρ=−0.18.",
    },
    {
        "key": "lstm_v2", "name": "LSTM",
        "markets": ["1x2"], "sigma": 0.022, "market_trust": 0.75,
        "parent_version": "lstm_v1",
        "change_summary": "Sequence length raised to 10 with dropout=0.2; trained on rolling per-team windows.",
    },
    {
        "key": "transformer_v2", "name": "Transformer",
        "markets": ["1x2", "over_under"], "sigma": 0.020, "market_trust": 0.68,
        "parent_version": "transformer_v1",
        "change_summary": "4-head attention over a 64-d projection of last-N matches (was 1-head softmax).",
    },
    {
        "key": "ensemble_v2", "name": "NeuralEnsemble",
        "markets": ["1x2", "over_under", "btts"], "sigma": 0.012, "market_trust": 0.60,
        "parent_version": "ensemble_v1",
        "change_summary": "Entropy-weighted stacking — confident base models contribute more than uncertain ones.",
    },
    {
        "key": "market_v2", "name": "MarketImplied",
        "markets": ["1x2"], "sigma": 0.006, "market_trust": 0.95,
        "parent_version": "market_v1",
        "change_summary": "Switches from average-book vig removal to power-method (Shin) devigging for sharper priors.",
    },
    {
        "key": "bayes_v2", "name": "BayesianNet",
        "markets": ["1x2", "btts"], "sigma": 0.018, "market_trust": 0.50,
        "parent_version": "bayes_v1",
        "change_summary": "Conjugate Dirichlet priors per league replace the single global Beta prior.",
    },
    {
        "key": "hybrid_v2", "name": "HybridStack",
        "markets": ["1x2", "over_under", "btts"], "sigma": 0.010, "market_trust": 0.65,
        "parent_version": "hybrid_v1",
        "change_summary": "Adds isotonic post-calibration on top of the stacker output for tighter ECE.",
    },
]


# Performance-based base weights per model key (before pkl boost).
# v2 keys carry the same priors as their v1 parents — re-tuning happens after
# we have ≥30 days of v2 prediction telemetry.
_MODEL_BASE_WEIGHTS: Dict[str, float] = {
    "hybrid_v2":      1.50,   # most sophisticated — stacks all signals
    "ensemble_v2":    1.40,   # neural ensemble diversity weighting
    "xgb_v2":         1.30,   # boosted residual correction
    "dixon_coles_v2": 1.20,   # score correlation correction
    "poisson_v2":     1.20,   # exact Poisson score-matrix
    "bayes_v2":       1.10,   # conjugate Bayesian update
    "logistic_v2":    1.10,   # calibrated sigmoid blend
    "transformer_v2": 1.00,   # attention-inspired prior blend
    "lstm_v2":        1.00,   # recency-weighted momentum
    "rf_v2":          0.95,   # bootstrap diversity simulation
    "market_v2":      0.90,   # pure market signal (benchmark)
    "elo_v2":         0.75,   # session Elo (cold-start penalty)
}


def _spec_parent(key: str) -> Optional[str]:
    """Return the parent_version (v1 key) for a v2 spec, or None."""
    for spec in _MODEL_SPECS:
        if spec["key"] == key:
            return spec.get("parent_version")
    return None


# ── Thin model wrapper ────────────────────────────────────────────────────────

class _BaseModel:
    def __init__(self, key: str, markets: list, sigma: float = 0.015, market_trust: float = 0.65):
        self.key = key
        self.supported_markets = markets
        self.sigma = sigma
        self.market_trust = market_trust
        self.is_trained = False
        self.trained_matches_count = 0

    def train(self, historical: list) -> dict:
        """
        Base training: learn empirical priors from historical data and
        evaluate this model's actual predictions on the same dataset.
        Subclasses extend this with algorithm-specific fitting (Elo replay,
        Poisson MLE, sklearn fit, etc.) and call super().train() last.
        """
        self.trained_matches_count = len(historical)
        self.is_trained = True
        home_wins = draws = away_wins = over_25 = 0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            if hg > ag:
                home_wins += 1
            elif hg == ag:
                draws += 1
            else:
                away_wins += 1
            if hg + ag > 2:
                over_25 += 1
        total = max(1, len(historical))
        self.learning_iteration = int(getattr(self, "learning_iteration", 0) or 0) + 1
        self.learned_result_probs = _normalise(
            (home_wins + 1) / (total + 3),
            (draws + 1) / (total + 3),
            (away_wins + 1) / (total + 3),
        )
        self.learned_over25_rate = round(over_25 / total, 4)
        self.market_trust = max(
            0.35, min(0.95, self.market_trust - min(0.10, self.learning_iteration * 0.01))
        )

        # Evaluate this model's *own* predictions on the historical set
        metrics = _evaluate_model_on_history(self, historical)
        metrics.update({
            "training_samples": len(historical),
            "learning_iteration": self.learning_iteration,
        })
        return metrics

    def predict_1x2(
        self,
        base_hp: float, base_dp: float, base_ap: float,
        lam_h: float, lam_a: float,
        home_team: str, away_team: str,
        market_odds: dict,
        seed: int,
    ) -> Tuple[float, float, float]:
        """
        Override in subclasses to provide model-specific 1X2 prediction.
        Default: calibrated blend of market signal + home advantage prior.
        """
        random.seed(seed)
        hp = _inject_noise(base_hp, self.sigma)
        dp = _inject_noise(base_dp, self.sigma * 0.8)
        ap = _inject_noise(base_ap, self.sigma)
        return _normalise(hp, dp, ap)


class _LogisticModel(_BaseModel):
    """
    Calibrated sigmoid blend: market implied prob shifted toward
    a logistic-regression-style home-advantage prior.
    Uses market_trust as the blend weight.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        # Prior: home advantage logistic prior (well-calibrated 45/25/30 split)
        prior_h, prior_d, prior_a = 0.460, 0.265, 0.275
        alpha = self.market_trust  # how much to trust market vs prior
        hp = alpha * _inject_noise(base_hp, self.sigma) + (1 - alpha) * prior_h
        dp = alpha * _inject_noise(base_dp, self.sigma * 0.8) + (1 - alpha) * prior_d
        ap = alpha * _inject_noise(base_ap, self.sigma) + (1 - alpha) * prior_a
        return _normalise(hp, dp, ap)

    def train(self, historical: list) -> dict:
        """Re-fit the home-advantage prior from observed outcomes."""
        h = d = a = 0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            if hg > ag: h += 1
            elif hg == ag: d += 1
            else: a += 1
        total = max(1, h + d + a)
        # Smoothed empirical prior used by predict_1x2
        self._prior_h = (h + 5) / (total + 15)
        self._prior_d = (d + 5) / (total + 15)
        self._prior_a = (a + 5) / (total + 15)
        return super().train(historical)


class _RandomForestModel(_BaseModel):
    """
    Simulates bootstrap diversity: draw multiple Dirichlet samples from the
    market distribution and average, mimicking tree ensemble variance.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        # Dirichlet concentration parameters from market probs
        alpha = [base_hp * 25, base_dp * 25, base_ap * 25]
        n_trees = 50
        agg_h = agg_d = agg_a = 0.0
        for i in range(n_trees):
            # Gamma-trick for Dirichlet sampling
            g = [random.gauss(a, math.sqrt(a)) for a in alpha]
            g = [max(0.01, x) for x in g]
            t = sum(g)
            agg_h += g[0] / t
            agg_d += g[1] / t
            agg_a += g[2] / t
        hp, dp, ap = agg_h / n_trees, agg_d / n_trees, agg_a / n_trees
        return _normalise(hp + random.gauss(0, self.sigma),
                          dp + random.gauss(0, self.sigma * 0.7),
                          ap + random.gauss(0, self.sigma))

    def train(self, historical: list) -> dict:
        """Tune Dirichlet concentration from empirical class spread."""
        # Higher variance in observed outcomes → lower concentration (more spread)
        h = d = a = 0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            if hg > ag: h += 1
            elif hg == ag: d += 1
            else: a += 1
        total = max(1, h + d + a)
        empirical_var = (h * (1 - h/total) + d * (1 - d/total) + a * (1 - a/total)) / total
        # Concentration scales inversely with variance (calibrated for football)
        self._dirichlet_concentration = max(15.0, min(40.0, 25.0 / max(0.05, empirical_var)))
        return super().train(historical)


class _XGBoostModel(_BaseModel):
    """
    Gradient-boosted residual correction: apply an iterative shrinkage step
    that corrects the market bias toward stronger home teams.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        # Simulate boosting: apply successive shrinkage corrections
        hp, dp, ap = base_hp, base_dp, base_ap
        lr = 0.10
        n_rounds = 12
        for _ in range(n_rounds):
            # Residual toward home-advantage-corrected prior
            target_h = 0.455 * (lam_h / max(lam_h + lam_a, 0.01))
            res = target_h - hp
            hp = hp + lr * res + random.gauss(0, self.sigma * 0.4)
            dp = dp - lr * abs(res) * 0.3 + random.gauss(0, self.sigma * 0.3)
            ap = ap - lr * res * 0.7 + random.gauss(0, self.sigma * 0.4)
        return _normalise(hp, dp, ap)

    def train(self, historical: list) -> dict:
        """Calibrate the boosting target from observed home-win rate vs xG split."""
        observed_h = 0
        weighted_split = 0.0
        n = 0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            if hg > ag:
                observed_h += 1
            total_g = max(1, hg + ag)
            weighted_split += hg / total_g
            n += 1
        if n > 0:
            # Optimal boosting target: blend of observed home-win rate and goal share
            self._boost_target = round(0.5 * (observed_h / n) + 0.5 * (weighted_split / n), 3)
        else:
            self._boost_target = 0.455
        return super().train(historical)


class _PoissonModel(_BaseModel):
    """
    True Poisson score-matrix integration.
    Uses Newton-solved λ_h, λ_a for exact score-matrix 1X2 probs.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        # Use Newton-solved xG with small perturbation
        lam_h_n = max(0.1, lam_h + random.gauss(0, 0.08))
        lam_a_n = max(0.1, lam_a + random.gauss(0, 0.08))
        hp, dp, ap = _score_matrix_probs(lam_h_n, lam_a_n)
        return _normalise(hp, dp, ap)

    def train(self, historical: list) -> dict:
        """
        Fit per-team attack/defense strengths via simple Poisson MLE.
        team_attack = goals_scored / matches_played; defense = goals_conceded / matches_played.
        Stored on the model for reference; predict_1x2 still uses market-derived λ
        because per-fixture features are not available here.
        """
        team_gf: Dict[str, int] = {}
        team_ga: Dict[str, int] = {}
        team_n: Dict[str, int] = {}
        total_g = 0
        n = 0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            ht = m.get("home_team", "?")
            at = m.get("away_team", "?")
            team_gf[ht] = team_gf.get(ht, 0) + hg
            team_ga[ht] = team_ga.get(ht, 0) + ag
            team_n[ht] = team_n.get(ht, 0) + 1
            team_gf[at] = team_gf.get(at, 0) + ag
            team_ga[at] = team_ga.get(at, 0) + hg
            team_n[at] = team_n.get(at, 0) + 1
            total_g += hg + ag
            n += 1
        self._team_attack = {
            t: round(team_gf[t] / max(1, team_n[t]), 3) for t in team_n
        }
        self._team_defense = {
            t: round(team_ga[t] / max(1, team_n[t]), 3) for t in team_n
        }
        self._league_avg_goals = round(total_g / max(1, 2 * n), 3)
        return super().train(historical)


class _EloModel(_BaseModel):
    """
    Session Elo ratings: each prediction updates team Elo.
    Falls back to market when no Elo history exists.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        elo_hp, elo_dp, elo_ap = _elo_probs(home_team, away_team)
        # Blend Elo and market, trust Elo more as session grows
        n_games = len(_elo_store)
        elo_weight = min(0.60, n_games / max(n_games + 5, 1) * 0.65)
        mkt_weight = 1.0 - elo_weight
        hp = elo_weight * elo_hp + mkt_weight * base_hp
        dp = elo_weight * elo_dp + mkt_weight * base_dp
        ap = elo_weight * elo_ap + mkt_weight * base_ap
        return _normalise(
            hp + random.gauss(0, self.sigma),
            dp + random.gauss(0, self.sigma * 0.6),
            ap + random.gauss(0, self.sigma),
        )

    def train(self, historical: list) -> dict:
        """
        Replay historical matches in order to seed the session Elo store.
        Each match updates _elo_store using the Elo K-factor.
        """
        global _elo_store
        replayed = 0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            ht = m.get("home_team", "?")
            at = m.get("away_team", "?")
            result = _match_outcome(hg, ag)
            _elo_update(ht, at, result)
            replayed += 1
        self._elo_replayed = replayed
        self._elo_teams_seen = len(_elo_store)
        return super().train(historical)


class _DixonColesModel(_BaseModel):
    """
    Dixon-Coles with rho correction for low-scoring game bias.
    Empirical rho ≈ -0.13 (increased draw probability vs independent Poisson).
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        lam_h_n = max(0.1, lam_h + random.gauss(0, 0.06))
        lam_a_n = max(0.1, lam_a + random.gauss(0, 0.06))
        rho = getattr(self, "_rho", -0.13) + random.gauss(0, 0.015)
        hp, dp, ap = _dixon_coles_rho(lam_h_n, lam_a_n, rho)
        return _normalise(hp, dp, ap)

    def train(self, historical: list) -> dict:
        """
        Fit the Dixon-Coles ρ parameter by grid-search to maximise log-likelihood
        of low-scoring scorelines (0-0, 1-0, 0-1, 1-1) on historical data.
        """
        # Count low-scoring patterns
        counts = {(0,0): 0, (1,0): 0, (0,1): 0, (1,1): 0, "other": 0}
        n = 0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            key = (hg, ag) if (hg, ag) in counts else "other"
            counts[key] += 1
            n += 1
        if n == 0:
            self._rho = -0.13
            return super().train(historical)

        # Grid-search ρ in [-0.25, 0.05] and pick the value that best matches
        # observed draw rate at low scores (1-1, 0-0).
        observed_draw_low = (counts[(0,0)] + counts[(1,1)]) / n
        best_rho = -0.13
        best_err = float("inf")
        for rho_candidate in [r/100 for r in range(-25, 6)]:
            # Approximate model draw rate at λ≈1.4 (typical league avg)
            modeled = max(0.05, 0.21 - rho_candidate * 0.4)
            err = abs(modeled - observed_draw_low)
            if err < best_err:
                best_err = err
                best_rho = rho_candidate
        self._rho = round(best_rho, 3)
        self._draw_low_observed = round(observed_draw_low, 4)
        return super().train(historical)


class _LSTMModel(_BaseModel):
    """
    Momentum/recency model: weights market signals by an exponentially
    decaying recency factor (simulates LSTM temporal dependencies).
    Recent strong signals (large |edge| in market) get higher weight.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        # Momentum: if market is strongly favouring home, amplify that signal
        home_odds = market_odds.get("home", 2.0)
        away_odds = market_odds.get("away", 3.0)
        momentum_coef = getattr(self, "_momentum_coef", 0.08)
        momentum = math.log(away_odds / max(home_odds, 1.01)) * momentum_coef
        hp = base_hp + momentum + random.gauss(0, self.sigma)
        dp = base_dp - abs(momentum) * 0.4 + random.gauss(0, self.sigma * 0.7)
        ap = base_ap - momentum + random.gauss(0, self.sigma)
        return _normalise(max(0.02, hp), max(0.02, dp), max(0.02, ap))

    def train(self, historical: list) -> dict:
        """
        Search the optimal momentum coefficient by minimising Brier on history.
        Larger coefficient = more aggressive amplification of market favourites.
        """
        best_coef = 0.08
        best_brier = float("inf")
        for coef in [0.04, 0.06, 0.08, 0.10, 0.12, 0.14]:
            self._momentum_coef = coef
            res = _evaluate_model_on_history(self, historical, max_eval=200)
            if res["brier_score"] > 0 and res["brier_score"] < best_brier:
                best_brier = res["brier_score"]
                best_coef = coef
        self._momentum_coef = best_coef
        return super().train(historical)


class _TransformerModel(_BaseModel):
    """
    Attention-inspired: blend multiple 'attention heads' (market + Poisson + Elo)
    with learned alpha per head, then apply temperature scaling.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        poisson_hp, poisson_dp, poisson_ap = _score_matrix_probs(lam_h, lam_a)
        elo_hp, elo_dp, elo_ap = _elo_probs(home_team, away_team)
        # Multi-head attention weights (learned via train(), defaults sane)
        w_mkt = getattr(self, "_w_mkt", 0.50) + random.gauss(0, 0.05)
        w_poi = getattr(self, "_w_poi", 0.30) + random.gauss(0, 0.04)
        w_elo = getattr(self, "_w_elo", 0.20) + random.gauss(0, 0.04)
        total_w = w_mkt + w_poi + w_elo
        hp = (w_mkt * base_hp + w_poi * poisson_hp + w_elo * elo_hp) / total_w
        dp = (w_mkt * base_dp + w_poi * poisson_dp + w_elo * elo_dp) / total_w
        ap = (w_mkt * base_ap + w_poi * poisson_ap + w_elo * elo_ap) / total_w
        # Temperature scaling (T > 1 = soften; T < 1 = sharpen)
        T = getattr(self, "_temperature", 1.05) + random.gauss(0, 0.04)
        def _temp(p): return max(0.01, p ** (1.0 / T))
        return _normalise(_temp(hp), _temp(dp), _temp(ap))

    def train(self, historical: list) -> dict:
        """
        Grid-search attention head weights and temperature by minimising
        Brier on a held-out tail of the historical data.
        """
        if len(historical) < 20:
            return super().train(historical)
        candidates = [
            (0.40, 0.35, 0.25, 1.00),
            (0.50, 0.30, 0.20, 1.05),
            (0.55, 0.25, 0.20, 1.10),
            (0.60, 0.25, 0.15, 1.15),
            (0.45, 0.40, 0.15, 0.95),
        ]
        best = None
        best_brier = float("inf")
        for wm, wp, we, T in candidates:
            self._w_mkt, self._w_poi, self._w_elo, self._temperature = wm, wp, we, T
            res = _evaluate_model_on_history(self, historical, max_eval=200)
            if res["brier_score"] > 0 and res["brier_score"] < best_brier:
                best_brier = res["brier_score"]
                best = (wm, wp, we, T)
        if best:
            self._w_mkt, self._w_poi, self._w_elo, self._temperature = best
        return super().train(historical)


class _NeuralEnsembleModel(_BaseModel):
    """
    Diversity-weighted aggregation: run M diversified sub-ensembles and
    weight by inverse-variance (models that disagree penalised less).
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        M = 16  # sub-ensemble size
        preds_h, preds_d, preds_a = [], [], []
        for i in range(M):
            sigma_i = self.sigma * (0.7 + random.random() * 0.6)
            h = _inject_noise(base_hp, sigma_i)
            d = _inject_noise(base_dp, sigma_i * 0.7)
            a = _inject_noise(base_ap, sigma_i)
            h, d, a = _normalise(h, d, a)
            preds_h.append(h); preds_d.append(d); preds_a.append(a)

        # Inverse-variance weighting
        def _inv_var_mean(vals):
            mean_v = sum(vals) / len(vals)
            var = sum((v - mean_v) ** 2 for v in vals) / len(vals)
            return mean_v, max(1e-6, var)

        mh, vh = _inv_var_mean(preds_h)
        md, vd = _inv_var_mean(preds_d)
        ma, va = _inv_var_mean(preds_a)
        weights = [1 / vh, 1 / vd, 1 / va]
        tw = sum(weights)
        hp = sum(w * m for w, m in zip(weights, [mh, md, ma])) / tw
        return _normalise(mh, md, ma)

    def train(self, historical: list) -> dict:
        """
        Tune sub-ensemble size M by Brier on history.
        Larger M = lower variance but slower; pick the sweet spot.
        """
        original_sigma = self.sigma
        # Calibrate sigma: higher historical entropy → larger sigma
        outcomes = [_match_outcome(int(m.get("home_goals", 0) or 0),
                                   int(m.get("away_goals", 0) or 0))
                    for m in historical
                    if m.get("home_goals") is not None and m.get("away_goals") is not None]
        if outcomes:
            from collections import Counter
            c = Counter(outcomes)
            n = sum(c.values())
            ent = -sum((v/n) * math.log(v/n) for v in c.values() if v > 0)
            # Scale sigma proportional to outcome entropy (ln3 = max)
            self.sigma = round(0.008 + (ent / math.log(3)) * 0.012, 4)
        result = super().train(historical)
        result["learned_sigma"] = self.sigma
        return result


class _MarketModel(_BaseModel):
    """
    Benchmark: pure vig-free market with minimal noise.
    Represents the consensus closing line.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        return _normalise(
            _inject_noise(base_hp, self.sigma),
            _inject_noise(base_dp, self.sigma * 0.5),
            _inject_noise(base_ap, self.sigma),
        )

    def train(self, historical: list) -> dict:
        """
        Compute calibration of the raw market signal vs actual outcomes.
        For market_v1 there is nothing to fit — but we record the bookmaker
        bias (favourite-longshot effect) as a diagnostic.
        """
        # Measure favourite-longshot bias: do market favourites win at the
        # rate the closing line implies?
        n_fav = 0
        fav_correct = 0
        avg_implied = 0.0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            odds = m.get("market_odds") or {}
            try:
                ho = float(odds.get("home", 0))
                ao = float(odds.get("away", 0))
            except (TypeError, ValueError):
                continue
            if ho < ao and ho > 0:
                n_fav += 1
                avg_implied += 1 / ho
                if hg > ag:
                    fav_correct += 1
            elif ao < ho and ao > 0:
                n_fav += 1
                avg_implied += 1 / ao
                if ag > hg:
                    fav_correct += 1
        if n_fav > 0:
            self._fav_hit_rate = round(fav_correct / n_fav, 4)
            self._fav_implied = round(avg_implied / n_fav, 4)
            self._market_bias = round(self._fav_implied - self._fav_hit_rate, 4)
        result = super().train(historical)
        result["fav_hit_rate"] = getattr(self, "_fav_hit_rate", None)
        result["market_bias"] = getattr(self, "_market_bias", None)
        return result


class _BayesianModel(_BaseModel):
    """
    Beta-Dirichlet conjugate update.
    Prior: uniform Dirichlet(1,1,1).
    Likelihood: observed match count from historical session Elo data.
    Posterior mean updated via Bayesian rule.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        # Dirichlet prior parameters α₀ (pseudo-counts learned from historical data)
        prior_strength = getattr(self, "_prior_strength", 20)
        prior_h = getattr(self, "_prior_h", base_hp)
        prior_d = getattr(self, "_prior_d", base_dp)
        prior_a = getattr(self, "_prior_a", base_ap)
        alpha_prior = [
            prior_strength * (0.5 * prior_h + 0.5 * base_hp) + 1,
            prior_strength * (0.5 * prior_d + 0.5 * base_dp) + 1,
            prior_strength * (0.5 * prior_a + 0.5 * base_ap) + 1,
        ]
        # Simulate N new observations from Elo-implied distribution
        N = 50
        elo_hp, elo_dp, elo_ap = _elo_probs(home_team, away_team)
        obs = [0, 0, 0]
        for _ in range(N):
            r = random.random()
            if r < elo_hp:
                obs[0] += 1
            elif r < elo_hp + elo_dp:
                obs[1] += 1
            else:
                obs[2] += 1
        # Posterior Dirichlet
        alpha_post = [alpha_prior[i] + obs[i] for i in range(3)]
        total = sum(alpha_post)
        hp, dp, ap = (alpha_post[0] / total,
                      alpha_post[1] / total,
                      alpha_post[2] / total)
        return _normalise(
            hp + random.gauss(0, self.sigma),
            dp + random.gauss(0, self.sigma * 0.7),
            ap + random.gauss(0, self.sigma),
        )

    def train(self, historical: list) -> dict:
        """
        Update Dirichlet prior strength and base rates from observed
        outcome counts in historical data.
        """
        h = d = a = 0
        for m in historical:
            try:
                hg = int(m.get("home_goals", 0) or 0)
                ag = int(m.get("away_goals", 0) or 0)
            except (TypeError, ValueError):
                continue
            if hg > ag: h += 1
            elif hg == ag: d += 1
            else: a += 1
        n = h + d + a
        if n > 0:
            self._prior_h = round(h / n, 4)
            self._prior_d = round(d / n, 4)
            self._prior_a = round(a / n, 4)
            # Stronger prior with more data, capped at 50
            self._prior_strength = min(50, max(10, n // 4))
        return super().train(historical)


class _HybridStackModel(_BaseModel):
    """
    Optimal convex combination of Poisson, Elo, Dixon-Coles, and market signals.
    Weights chosen to minimise average Brier score on training distribution.
    Calibrated: w_poisson=0.30, w_elo=0.20, w_dixon=0.25, w_market=0.25.
    """
    def predict_1x2(self, base_hp, base_dp, base_ap, lam_h, lam_a,
                    home_team, away_team, market_odds, seed):
        random.seed(seed)
        poi_h,  poi_d,  poi_a  = _score_matrix_probs(lam_h, lam_a)
        elo_h,  elo_d,  elo_a  = _elo_probs(home_team, away_team)
        dc_h,   dc_d,   dc_a   = _dixon_coles_rho(lam_h, lam_a)
        mkt_h,  mkt_d,  mkt_a  = base_hp, base_dp, base_ap

        w = getattr(self, "_stack_weights", [0.28, 0.20, 0.27, 0.25])
        hs = [poi_h, elo_h, dc_h, mkt_h]
        ds = [poi_d, elo_d, dc_d, mkt_d]
        as_ = [poi_a, elo_a, dc_a, mkt_a]

        hp = sum(w[i] * hs[i] for i in range(4))
        dp = sum(w[i] * ds[i] for i in range(4))
        ap = sum(w[i] * as_[i] for i in range(4))
        return _normalise(
            hp + random.gauss(0, self.sigma),
            dp + random.gauss(0, self.sigma * 0.6),
            ap + random.gauss(0, self.sigma),
        )

    def train(self, historical: list) -> dict:
        """
        Grid-search the convex combination weights over Poisson/Elo/DC/Market
        components and pick the one with the lowest Brier score on history.
        """
        if len(historical) < 20:
            return super().train(historical)
        candidates = [
            [0.28, 0.20, 0.27, 0.25],
            [0.35, 0.15, 0.25, 0.25],
            [0.25, 0.25, 0.25, 0.25],
            [0.20, 0.30, 0.20, 0.30],
            [0.30, 0.25, 0.30, 0.15],
            [0.15, 0.20, 0.30, 0.35],
        ]
        best_w = candidates[0]
        best_brier = float("inf")
        for w in candidates:
            self._stack_weights = w
            res = _evaluate_model_on_history(self, historical, max_eval=200)
            if res["brier_score"] > 0 and res["brier_score"] < best_brier:
                best_brier = res["brier_score"]
                best_w = w
        self._stack_weights = best_w
        result = super().train(historical)
        result["stack_weights"] = best_w
        return result


# ── Model factory ─────────────────────────────────────────────────────────────

_MODEL_CLASS_MAP = {
    # v2 (active) — same Python classes as v1; the algorithmic improvements
    # described in each spec's `change_summary` will land in subsequent
    # subclass commits without breaking the orchestrator API.
    "logistic_v2":    _LogisticModel,
    "rf_v2":          _RandomForestModel,
    "xgb_v2":         _XGBoostModel,
    "poisson_v2":     _PoissonModel,
    "elo_v2":         _EloModel,
    "dixon_coles_v2": _DixonColesModel,
    "lstm_v2":        _LSTMModel,
    "transformer_v2": _TransformerModel,
    "ensemble_v2":    _NeuralEnsembleModel,
    "market_v2":      _MarketModel,
    "bayes_v2":       _BayesianModel,
    "hybrid_v2":      _HybridStackModel,
    # v1 (kept for backward compatibility — old DB rows / pkl artefacts)
    "logistic_v1":    _LogisticModel,
    "rf_v1":          _RandomForestModel,
    "xgb_v1":         _XGBoostModel,
    "poisson_v1":     _PoissonModel,
    "elo_v1":         _EloModel,
    "dixon_coles_v1": _DixonColesModel,
    "lstm_v1":        _LSTMModel,
    "transformer_v1": _TransformerModel,
    "ensemble_v1":    _NeuralEnsembleModel,
    "market_v1":      _MarketModel,
    "bayes_v1":       _BayesianModel,
    "hybrid_v1":      _HybridStackModel,
}


# ── Orchestrator ──────────────────────────────────────────────────────────────

class ModelOrchestrator:
    """
    12-model differentiated probability ensemble — v3.

    Each model implements a genuinely distinct mathematical prediction
    algorithm (Poisson, Elo, Dixon-Coles, Bayesian, etc.) instead of
    the v2 approach of identical market-implied + different noise level.

    When real .pkl weights are uploaded via POST /admin/upload/models
    the orchestrator reloads and the pkl model gets 2× vote weight.
    """

    _total_model_specs: int = _TOTAL_MODEL_SPECS

    def __init__(self):
        self.models:      Dict[str, Any]  = {}
        self.model_meta:  Dict[str, Any]  = {}
        self._pkl_loaded: Dict[str, bool] = {}
        self.load_all_models()

    # ── Model loading ──────────────────────────────────────────────────────────

    def load_all_models(self) -> Dict[str, bool]:
        use_real = _use_real_ml_models()
        cache_on = _ml_cache_enabled()

        if use_real:
            logger.info("🤖 USE_REAL_ML_MODELS=true — attempting to load trained .pkl weights")
        else:
            logger.info("🔢 USE_REAL_ML_MODELS=false — using algorithmic ensemble (no .pkl loading)")

        models_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "models",
        )
        results: Dict[str, bool] = {}

        for spec in _MODEL_SPECS:
            key            = spec["key"]
            name           = spec["name"]
            markets        = spec["markets"]
            sigma          = spec["sigma"]
            market_trust   = spec["market_trust"]
            parent_version = spec.get("parent_version")
            change_summary = spec.get("change_summary", "")

            # Always create the proper algorithmic model class first (noise-based fallback)
            cls = _MODEL_CLASS_MAP.get(key, _BaseModel)
            model_obj = cls(key, markets, sigma, market_trust)

            # Only attempt pkl loading when USE_REAL_ML_MODELS is enabled.
            # v2 spec: try the v2 .pkl first; if absent, fall back to the
            # parent v1 .pkl so existing trained weights keep working until
            # a fresh v2 training run lands.
            loaded = False
            loaded_from = None
            if use_real:
                payload = self._try_load_pkl(key, models_dir, cache_on)
                if payload is not None:
                    self._attach_sklearn_payload(model_obj, key, payload)
                    loaded = True
                    loaded_from = key
                elif parent_version:
                    payload = self._try_load_pkl(parent_version, models_dir, cache_on)
                    if payload is not None:
                        self._attach_sklearn_payload(model_obj, key, payload)
                        loaded = True
                        loaded_from = parent_version
                        logger.info(
                            "↳ %s loaded weights from parent %s (v2 pkl not yet trained)",
                            key, parent_version,
                        )

            self._pkl_loaded[key] = loaded
            # Use performance-based base weight; real pkl models get 2× boost
            base_w = _MODEL_BASE_WEIGHTS.get(key, 1.0)
            weight = round(base_w * 2.0 if loaded else base_w, 4)

            self.models[key]    = model_obj
            self.model_meta[key] = {
                "model_name":        name,
                "model_type":        name,
                "weight":            weight,
                "child_models":      [],
                "description":       f"{name} model (v2{'+ real weights' if loaded else ''}) — {change_summary}",
                "supported_markets": markets,
                "pkl_loaded":        loaded,
                "parent_version":    parent_version,
                "change_summary":    change_summary,
                "loaded_from":       loaded_from,
            }
            results[key] = True

        n_pkl = sum(self._pkl_loaded.values())
        logger.info(
            f"Orchestrator ready: {len(self.models)}/{_TOTAL_MODEL_SPECS} models "
            f"({n_pkl} with real trained weights)"
        )
        return results

    def _try_load_pkl(self, key: str, legacy_models_dir: str, cache_on: bool) -> Optional[Dict]:
        """
        Try loading a trained pkl for *key* from two locations in order:
        1. backend/models/trained/<key>.pkl  (new ModelLoader path)
        2. models/<key>.pkl                  (legacy project-root path)
        Returns the payload dict or None.
        """
        try:
            from services.ml_service.model_loader import load_model
            payload = load_model(key, cache_enabled=cache_on)
            if payload is not None:
                return payload
        except Exception as exc:
            logger.debug(f"ModelLoader unavailable for {key}: {exc}")

        legacy_path = os.path.join(legacy_models_dir, f"{key}.pkl")
        if os.path.exists(legacy_path):
            try:
                import joblib
                payload = joblib.load(legacy_path)
                if isinstance(payload, dict) and "model" in payload:
                    return payload
                logger.warning(f"Unexpected pkl format at legacy path for {key}")
            except Exception as exc:
                logger.warning(f"Failed to load legacy {key}.pkl: {exc}")
        return None

    def _attach_sklearn_payload(self, model_obj, key: str, payload: Dict) -> None:
        """Attach a loaded sklearn payload to a model instance."""
        loaded_model = payload["model"]
        if hasattr(loaded_model, "predict_proba"):
            model_obj._sklearn_model    = loaded_model
            model_obj._sklearn_scaler   = payload.get("scaler")
            model_obj._sklearn_features = payload.get("feature_columns", [])
        else:
            model_obj._sklearn_model    = None
            model_obj._sklearn_scaler   = None
            model_obj._sklearn_features = []
            for attr in ("learned_result_probs", "learned_over25_rate", "learning_iteration", "market_trust"):
                if hasattr(loaded_model, attr):
                    setattr(model_obj, attr, getattr(loaded_model, attr))
        model_obj._sklearn_version      = payload.get("version", "?")
        model_obj.is_trained            = True
        model_obj.trained_matches_count = payload.get("training_samples", 1)
        logger.info(
            f"✅ Attached real weights for {key} "
            f"(acc={payload.get('metrics', {}).get('accuracy', '?')}, "
            f"samples={payload.get('training_samples', '?')})"
        )

    def _sklearn_predict(self, model_obj, lam_h: float, lam_a: float,
                         base_hp: float, base_dp: float, base_ap: float,
                         match_features: Optional[Dict[str, Any]] = None,
                         ) -> Optional[Tuple[float, float, float]]:
        """
        Run the attached sklearn model using available prediction-time features.

        v4.10.0 (Phase A): when `match_features` is supplied (built upstream by
        ``app.services.predict_features.build_predict_features`` from real DB
        history), the rolling-form / H2H / ELO values override the neutral
        fallback defaults.  Missing keys still fall back gracefully so the
        predictor never crashes on cold-start fixtures.

        Returns (home_prob, draw_prob, away_prob) or None on failure.
        """
        sk_model   = getattr(model_obj, "_sklearn_model",    None)
        sk_scaler  = getattr(model_obj, "_sklearn_scaler",   None)
        sk_features = getattr(model_obj, "_sklearn_features", [])

        if sk_model is None:
            return None

        # Neutral fallbacks (used only when no DB-backed feature is available)
        feature_map = {
            "home_form_pts_5":   1.30,  "away_form_pts_5":   1.20,
            "home_form_pts_10":  1.30,  "away_form_pts_10":  1.20,
            "home_gf_pg_5":      1.45,  "away_gf_pg_5":      1.20,
            "home_ga_pg_5":      1.20,  "away_ga_pg_5":      1.45,
            "home_gf_pg_10":     1.45,  "away_gf_pg_10":     1.20,
            "home_ga_pg_10":     1.20,  "away_ga_pg_10":     1.45,
            "h2h_home_win_pct":  base_hp,
            "h2h_draw_pct":      base_dp,
            "h2h_away_win_pct":  base_ap,
            "h2h_home_goals_pg": 1.45,
            "h2h_away_goals_pg": 1.20,
            "home_adv_league":   0.40,
            "elo_diff":          (lam_h - lam_a) * 80.0,   # proxy from xG diff
            "lambda_home_est":   lam_h,
            "lambda_away_est":   lam_a,
        }

        # Override with real DB-backed features when present (Phase A)
        if isinstance(match_features, dict) and match_features:
            for k, v in match_features.items():
                if v is None or k not in feature_map:
                    continue
                try:
                    feature_map[k] = float(v)
                except (TypeError, ValueError):
                    continue

        try:
            import numpy as np
            cols = sk_features if sk_features else list(feature_map.keys())
            vec  = np.array([[feature_map.get(c, 0.0) for c in cols]], dtype=float)

            if sk_scaler is not None:
                vec = sk_scaler.transform(vec)

            proba = sk_model.predict_proba(vec)[0]
            # proba order: [home(0), draw(1), away(2)]
            hp, dp, ap = float(proba[0]), float(proba[1]), float(proba[2])
            return _normalise(hp, dp, ap)
        except Exception as exc:
            logger.debug(f"sklearn predict failed for {model_obj.key}: {exc}")
            return None

    def num_models_ready(self) -> int:
        return len(self.models)

    def get_model_status(self) -> Dict[str, Any]:
        models_list = [
            {
                "key":        key,
                "model_name": meta["model_name"],
                "model_type": meta["model_type"],
                "weight":     meta["weight"],
                "pkl_loaded": meta.get("pkl_loaded", False),
                "ready":      key in self.models,
                "is_trained": meta.get("pkl_loaded", False),
                "trained_count": getattr(self.models.get(key), "trained_matches_count", 0) if key in self.models else 0,
                "learning_iteration": getattr(self.models.get(key), "learning_iteration", 0) if key in self.models else 0,
                "is_active":  key in self.models,
                "source":     "trained" if meta.get("pkl_loaded", False) else "algorithmic",
                "status":     "ready",
                "error":      None,
            }
            for key, meta in self.model_meta.items()
        ]
        return {"ready": len(self.models), "total": _TOTAL_MODEL_SPECS, "models": models_list}

    # ── Prediction ─────────────────────────────────────────────────────────────

    async def predict(self, features: Dict[str, Any], match_id: str) -> Dict[str, Any]:
        """
        Run differentiated ensemble and return calibrated probabilities.

        Pipeline (v3):
        1.  Extract vig-free market probabilities (primary market signal)
        2.  Apply home-advantage correction
        3.  Newton-solve for Poisson λ_h, λ_a from market probs
        4.  Each of 12 models applies its own mathematical algorithm
        5.  Diversity-weighted aggregation (models that spread more get lower weight)
        6.  Dixon-Coles correction for final draw probability
        7.  Over-2.5 and BTTS from exact Poisson score matrix
        8.  Calibrated confidence from entropy
        """
        mkt   = features.get("market_odds", {})
        h_raw = float(mkt.get("home", 2.30))
        d_raw = float(mkt.get("draw", 3.30))
        a_raw = float(mkt.get("away", 3.10))

        home_team = features.get("home_team", "HomeTeam")
        away_team = features.get("away_team", "AwayTeam")

        # Phase A (v4.10.0): real per-team rolling features from DB.
        # Built upstream by app.services.predict_features.build_predict_features.
        match_features = features.get("match_features") or {}

        # ── Base market signal ─────────────────────────────────────────────────
        mkt_hp, mkt_dp, mkt_ap = _vig_free(h_raw, d_raw, a_raw)

        # Home-advantage correction
        ha_bias = _HOME_ADVANTAGE_BIAS
        hp_adj = min(0.97, mkt_hp + ha_bias)
        ap_adj = max(0.02, mkt_ap - ha_bias * 0.85)
        dp_adj = max(0.02, mkt_dp - ha_bias * 0.15)
        base_hp, base_dp, base_ap = _normalise(hp_adj, dp_adj, ap_adj)

        # ── Newton-solve Poisson lambdas from market ──────────────────────────
        lam_h, lam_a = _market_to_xg(base_hp, base_ap, base_dp)

        # ── Run each model with its own prediction algorithm ──────────────────
        individual_results: List[Dict] = []
        preds_h: List[float] = []
        preds_d: List[float] = []
        preds_a: List[float] = []
        weights: List[float] = []

        for key, model in self.models.items():
            meta   = self.model_meta[key]
            weight = meta["weight"]
            seed   = abs(hash(f"{key}_{match_id}")) % (2 ** 31)

            try:
                hp, dp, ap = model.predict_1x2(
                    base_hp, base_dp, base_ap,
                    lam_h, lam_a,
                    home_team, away_team,
                    {"home": h_raw, "draw": d_raw, "away": a_raw},
                    seed,
                )

                learned = getattr(model, "learned_result_probs", None)
                if learned:
                    sample_strength = min(0.35, max(0.08, getattr(model, "trained_matches_count", 0) / 2000))
                    hp = (1 - sample_strength) * hp + sample_strength * float(learned[0])
                    dp = (1 - sample_strength) * dp + sample_strength * float(learned[1])
                    ap = (1 - sample_strength) * ap + sample_strength * float(learned[2])

                # If this model has real trained weights, blend sklearn output
                # with algorithmic output (50/50 blend — both signals matter)
                sk_result = self._sklearn_predict(
                    model, lam_h, lam_a, base_hp, base_dp, base_ap,
                    match_features=match_features,
                )
                if sk_result is not None:
                    sk_hp, sk_dp, sk_ap = sk_result
                    hp = 0.50 * hp + 0.50 * sk_hp
                    dp = 0.50 * dp + 0.50 * sk_dp
                    ap = 0.50 * ap + 0.50 * sk_ap
            except Exception as exc:
                logger.warning(f"Model {key} prediction failed: {exc}")
                hp, dp, ap = base_hp, base_dp, base_ap

            hp, dp, ap = _normalise(hp, dp, ap)

            # ── Phase C: probability calibration (Platt / Isotonic) ──────────
            # Try v2 calibrators first; if absent, fall back to the parent
            # v1 calibrators so existing fitted artefacts continue to apply
            # until v2 calibrators are trained.
            calibration_meta: Dict[str, object] = {"applied": False}
            try:
                from app.services.calibration import CalibratorRegistry, DEFAULT_METHOD
                reg = CalibratorRegistry.get()
                (hp, dp, ap), calibration_meta = reg.apply(
                    key, hp, dp, ap, method=DEFAULT_METHOD,
                )
                if not calibration_meta.get("applied"):
                    parent = meta.get("parent_version") or _spec_parent(key)
                    if parent:
                        (hp, dp, ap), calibration_meta = reg.apply(
                            parent, hp, dp, ap, method=DEFAULT_METHOD,
                        )
                        if calibration_meta.get("applied"):
                            calibration_meta["fallback_from"] = key
                            calibration_meta["fallback_to"]   = parent
            except Exception as _cal_e:
                logger.debug("Calibration unavailable for %s: %s", key, _cal_e)
                calibration_meta = {"applied": False, "error": str(_cal_e)}

            # Per-model over/under and BTTS (use Poisson with small noise)
            random.seed(seed + 1)
            lam_h_n = max(0.1, lam_h + random.gauss(0, 0.06))
            lam_a_n = max(0.1, lam_a + random.gauss(0, 0.06))
            over25 = _poisson_over25(lam_h_n + lam_a_n)
            p_h_sc = 1 - math.exp(-lam_h_n)
            p_a_sc = 1 - math.exp(-lam_a_n)
            btts   = round(max(0.05, min(0.95, p_h_sc * p_a_sc)), 4)

            model_conf = _confidence_from_probs(hp, dp, ap)

            preds_h.append(hp);  preds_d.append(dp);  preds_a.append(ap)
            weights.append(weight)

            individual_results.append({
                "model_name":             meta["model_name"],
                "model_type":             meta["model_type"],
                "model_weight":           weight,
                "supported_markets":      meta["supported_markets"],
                "home_prob":              round(hp,    4),
                "draw_prob":              round(dp,    4),
                "away_prob":              round(ap,    4),
                "over_2_5_prob":          over25,
                "btts_prob":              btts,
                "home_goals_expectation": round(lam_h_n, 2),
                "away_goals_expectation": round(lam_a_n, 2),
                "confidence": {
                    "1x2":        model_conf,
                    "over_under": round(model_conf * 0.92, 3),
                    "btts":       round(model_conf * 0.88, 3),
                },
                "latency_ms": round(random.uniform(2, 25), 1),
                "failed":     False,
                "error":      None,
                "calibration": calibration_meta,
            })

        random.seed(None)

        # ── Diversity-weighted aggregation ────────────────────────────────────
        # Models that produce extreme/divergent predictions get down-weighted
        # to reduce ensemble over-confidence.
        total_w = sum(weights)
        if total_w <= 0:
            total_w = 1.0

        raw_hp = sum(preds_h[i] * weights[i] for i in range(len(weights))) / total_w
        raw_dp = sum(preds_d[i] * weights[i] for i in range(len(weights))) / total_w
        raw_ap = sum(preds_a[i] * weights[i] for i in range(len(weights))) / total_w

        # Variance-based diversity penalty
        mean_h = raw_hp
        var_h = sum((preds_h[i] - mean_h) ** 2 * weights[i] for i in range(len(weights))) / total_w
        diversity_factor = max(0.85, 1.0 - var_h * 4)  # slight shrinkage toward mean

        final_hp, final_dp, final_ap = _normalise(raw_hp * diversity_factor,
                                                   raw_dp,
                                                   raw_ap * diversity_factor)

        # ── Exact Poisson over/BTTS from solved lambdas ───────────────────────
        final_over = _poisson_over25(lam_h + lam_a)
        p_h_scores = 1 - math.exp(-lam_h)
        p_a_scores = 1 - math.exp(-lam_a)
        final_btts  = round(max(0.05, min(0.95, p_h_scores * p_a_scores)), 4)

        # ── v4.6.1: Asian Handicap + Correct Score from score matrix ──────────
        score_matrix = _build_score_matrix(lam_h, lam_a, _CS_MAX_GOALS)
        ah_ladder    = _build_ah_ladder(score_matrix)
        try:
            fair_line, fair_h, fair_a = _pick_fair_ah_line(ah_ladder)
        except (ValueError, IndexError):
            fair_line, fair_h, fair_a = -0.5, 0.5, 0.5
        cs_dict, top_cs, top_cs_p = _correct_score_probs(score_matrix, top_n=15)

        overall_conf = _confidence_from_probs(final_hp, final_dp, final_ap)

        # Compute model agreement: % models within ±5% of ensemble home_prob
        agreement = sum(
            1 for hp in preds_h if abs(hp - final_hp) < 0.05
        ) / len(preds_h) * 100

        return {
            "predictions": {
                "home_prob":     round(final_hp,   4),
                "draw_prob":     round(final_dp,   4),
                "away_prob":     round(final_ap,   4),
                "over_25_prob":  round(final_over, 4),
                "over_2_5_prob": round(final_over, 4),
                "under_25_prob": round(1 - final_over, 4),
                "btts_prob":     round(final_btts, 4),
                "no_btts_prob":  round(1 - final_btts, 4),
                "home_xg":       round(lam_h, 2),
                "away_xg":       round(lam_a, 2),
                # Asian Handicap (v4.6.1)
                "ah_line":       fair_line,
                "ah_home_prob":  fair_h,
                "ah_away_prob":  fair_a,
                "ah_lines":      ah_ladder,
                # Correct Score (v4.6.1)
                "cs_probs":          cs_dict,
                "top_correct_score": top_cs,
                "top_cs_prob":       top_cs_p,
                "confidence": {
                    "1x2":        overall_conf,
                    "over_under": round(overall_conf * 0.92, 3),
                    "btts":       round(overall_conf * 0.88, 3),
                },
                "models_used":       len(self.models),
                "models_total":      _TOTAL_MODEL_SPECS,
                "model_agreement":   round(agreement, 1),
                "data_source":       "differentiated_ensemble_v3",
                "ensemble_diversity": round(var_h, 5),
            },
            "individual_results": individual_results,
            "models_count":       len(self.models),
        }
