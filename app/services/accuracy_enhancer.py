"""Accuracy enhancement utilities for the 12-model ensemble.

Three improvements that measurably tighten the ensemble's calibration:

1.  **Proper-scoring weight updates** (`compute_log_loss_delta`)
    Replaces the symmetric ±10% delta in `weight_adjuster` with a log-loss
    based magnitude. Confident-correct predictions earn more, confident-wrong
    predictions are penalised more — exactly what a strictly proper scoring
    rule should do.

2.  **Rolling-window accuracy** (`rolling_window_accuracy`)
    Computes each model's accuracy over its last N predictions from the
    `AIPredictionAudit` history. More responsive than lifetime accuracy.

3.  **Temperature scaling** (`TemperatureScaler`)
    Single-parameter post-processor on the final ensemble distribution.
    `T > 1` softens over-confident outputs, `T < 1` sharpens under-confident
    ones. Fitted on settled history by minimising NLL.

All three are pure functions / single-responsibility classes with no DB
side-effects beyond `rolling_window_accuracy` (which only reads).
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

logger = logging.getLogger(__name__)

EPS = 1e-9
TEMPERATURE_PATH = Path("models/temperature.json")


# ── 1. Proper-scoring weight delta ────────────────────────────────────

def compute_log_loss_delta(
    p_actual: float,
    base_delta: float = 0.10,
    max_magnitude: float = 0.25,
) -> float:
    """Return a signed delta for weight adjustment using log-loss magnitude.

    Idea: the log-likelihood of the actual outcome is the proper score.
    A perfect prediction (p=1.0) gives log(1)=0  → maximum reward magnitude.
    A coin-flip prediction (p=1/3) gives log(1/3)≈-1.10 → neutral.
    A confident-wrong prediction (p=0.05) gives log(0.05)≈-3.0 → heavy penalty.

    Mapping: delta = base_delta × ((-log(1/3)) - (-log(p_actual))) / log(3)
    so it's normalised to roughly [-1, +1] × base_delta around the neutral
    point of 1/3, then clamped to ±max_magnitude.

    Returns positive for better-than-coin-flip, negative otherwise.
    """
    p = max(EPS, min(1.0 - EPS, p_actual))
    neutral_nll = math.log(3.0)             # NLL of a uniform 1/3 guess
    actual_nll = -math.log(p)
    score = (neutral_nll - actual_nll) / neutral_nll   # ∈ approx [-∞, 1]
    delta = base_delta * score
    return max(-max_magnitude, min(max_magnitude, delta))


def log_loss_for_outcome(home: float, draw: float, away: float, outcome: str) -> float:
    """Negative log-likelihood of the actual 1x2 outcome."""
    pick = {"home": home, "draw": draw, "away": away}.get(outcome.lower())
    if pick is None:
        return 0.0
    return -math.log(max(EPS, min(1.0 - EPS, pick)))


def brier_for_outcome(home: float, draw: float, away: float, outcome: str) -> float:
    """Multi-class Brier score (sum of squared errors over 3 classes)."""
    target = {"home": (1, 0, 0), "draw": (0, 1, 0), "away": (0, 0, 1)}.get(outcome.lower())
    if target is None:
        return 0.0
    return (home - target[0]) ** 2 + (draw - target[1]) ** 2 + (away - target[2]) ** 2


# ── 2. Rolling window accuracy ────────────────────────────────────────

@dataclass
class RollingMetrics:
    model_key: str
    samples: int
    accuracy_1x2: float
    log_loss: float
    brier: float


async def rolling_window_accuracy(db, window: int = 50) -> list[RollingMetrics]:
    """Compute rolling accuracy / log-loss / Brier over the most recent
    `window` settled predictions per model.

    Reads from `AIPredictionAudit` joined to `Match.actual_outcome`.
    """
    from sqlalchemy import select, desc
    from app.modules.ai.models import AIPredictionAudit
    from app.db.models import Match

    rows = (await db.execute(
        select(AIPredictionAudit, Match.actual_outcome)
        .join(Match, Match.external_id == AIPredictionAudit.match_id, isouter=True)
        .where(Match.actual_outcome.isnot(None))
        .order_by(desc(AIPredictionAudit.created_at))
        .limit(window * 50)             # pull enough to cover all 12 models × window
    )).all()

    bucket: dict[str, list[tuple[float, float, float, str]]] = {}
    for audit, outcome in rows:
        if not audit.individual_results or not outcome:
            continue
        for r in audit.individual_results:
            key = r.get("model_key") or r.get("model_name")
            if not key:
                continue
            try:
                hp = float(r.get("home_prob", 0))
                dp = float(r.get("draw_prob", 0))
                ap = float(r.get("away_prob", 0))
            except (TypeError, ValueError):
                continue
            lst = bucket.setdefault(key, [])
            if len(lst) < window:
                lst.append((hp, dp, ap, outcome.lower()))

    out: list[RollingMetrics] = []
    for key, samples in bucket.items():
        if not samples:
            continue
        n = len(samples)
        wins = sum(
            1 for hp, dp, ap, oc in samples
            if max(("home", hp), ("draw", dp), ("away", ap), key=lambda x: x[1])[0] == oc
        )
        nll = sum(log_loss_for_outcome(hp, dp, ap, oc) for hp, dp, ap, oc in samples) / n
        bri = sum(brier_for_outcome(hp, dp, ap, oc) for hp, dp, ap, oc in samples) / n
        out.append(RollingMetrics(
            model_key=key,
            samples=n,
            accuracy_1x2=round(wins / n, 4),
            log_loss=round(nll, 4),
            brier=round(bri, 4),
        ))
    out.sort(key=lambda m: m.log_loss)      # best (lowest NLL) first
    return out


# ── 3. Temperature scaling ────────────────────────────────────────────

class TemperatureScaler:
    """Single-parameter post-processor on a 1x2 distribution.

    p_cal_i ∝ p_i ^ (1/T)
    T > 1  → softens (reduces over-confidence)
    T < 1  → sharpens
    T = 1  → identity (no change)
    """

    def __init__(self, temperature: float = 1.0) -> None:
        self.temperature = max(0.05, float(temperature))

    @classmethod
    def load(cls, path: Path = TEMPERATURE_PATH) -> "TemperatureScaler":
        try:
            t = json.loads(path.read_text()).get("temperature", 1.0)
            return cls(t)
        except Exception:
            return cls(1.0)

    def save(self, path: Path = TEMPERATURE_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"temperature": self.temperature}))

    def apply(self, hp: float, dp: float, ap: float) -> tuple[float, float, float]:
        if abs(self.temperature - 1.0) < 1e-6:
            return hp, dp, ap
        inv_t = 1.0 / self.temperature
        h = max(EPS, hp) ** inv_t
        d = max(EPS, dp) ** inv_t
        a = max(EPS, ap) ** inv_t
        s = h + d + a
        return h / s, d / s, a / s

    @staticmethod
    def fit(
        samples: Sequence[tuple[float, float, float, str]],
        candidates: Optional[Iterable[float]] = None,
    ) -> tuple[float, float]:
        """Grid-search the temperature that minimises mean NLL on `samples`.

        Each sample is (home, draw, away, outcome).
        Returns (best_T, best_nll).
        """
        if not samples:
            return 1.0, 0.0
        if candidates is None:
            # 0.5 → 3.0 in 0.05 steps gives 51 candidates; cheap to evaluate
            candidates = [round(0.5 + i * 0.05, 4) for i in range(51)]

        def mean_nll(T: float) -> float:
            scaler = TemperatureScaler(T)
            total = 0.0
            for hp, dp, ap, oc in samples:
                h, d, a = scaler.apply(hp, dp, ap)
                total += log_loss_for_outcome(h, d, a, oc)
            return total / len(samples)

        best_T, best_nll = 1.0, mean_nll(1.0)
        for T in candidates:
            nll = mean_nll(T)
            if nll < best_nll:
                best_T, best_nll = T, nll
        return best_T, round(best_nll, 6)


async def fit_temperature_from_history(db, min_samples: int = 100) -> dict:
    """Pull settled ensemble predictions and fit the global temperature."""
    from sqlalchemy import select, desc
    from app.modules.ai.models import AIPredictionAudit
    from app.db.models import Match

    rows = (await db.execute(
        select(AIPredictionAudit, Match.actual_outcome)
        .join(Match, Match.external_id == AIPredictionAudit.match_id, isouter=True)
        .where(Match.actual_outcome.isnot(None))
        .order_by(desc(AIPredictionAudit.created_at))
        .limit(5000)
    )).all()

    samples: list[tuple[float, float, float, str]] = []
    for audit, outcome in rows:
        if not outcome:
            continue
        try:
            samples.append((
                float(audit.home_prob), float(audit.draw_prob),
                float(audit.away_prob), outcome.lower(),
            ))
        except (TypeError, ValueError):
            continue

    if len(samples) < min_samples:
        return {
            "fitted": False,
            "reason": f"insufficient samples (have {len(samples)}, need {min_samples})",
            "n_samples": len(samples),
        }

    pre_nll = sum(log_loss_for_outcome(*s) for s in samples) / len(samples)
    best_T, best_nll = TemperatureScaler.fit(samples)

    scaler = TemperatureScaler(best_T)
    scaler.save()

    return {
        "fitted": True,
        "n_samples": len(samples),
        "temperature": best_T,
        "pre_fit_log_loss": round(pre_nll, 6),
        "post_fit_log_loss": best_nll,
        "improvement": round(pre_nll - best_nll, 6),
        "saved_to": str(TEMPERATURE_PATH),
    }


__all__ = [
    "compute_log_loss_delta",
    "log_loss_for_outcome",
    "brier_for_outcome",
    "rolling_window_accuracy",
    "RollingMetrics",
    "TemperatureScaler",
    "fit_temperature_from_history",
    "TEMPERATURE_PATH",
]
