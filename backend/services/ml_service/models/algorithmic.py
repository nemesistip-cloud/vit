"""
Algorithmic model wrappers used by VIT's 12-model ensemble.

Each class exposes a ``predict_proba(X) -> ndarray (n, 3)`` method matching
sklearn's interface so the orchestrator's ``_sklearn_predict`` code path can
consume them transparently. The first three feature columns are expected to
be ``lambda_home_est``, ``lambda_away_est``, ``elo_diff`` (see
``scripts/train_remaining_models.FEATURE_COLUMNS``).

These classes MUST live in an importable module so joblib can unpickle them
inside the running FastAPI process.
"""
from __future__ import annotations

import math
import numpy as np

MAX_GOALS = 10


def _factorials(n: int) -> np.ndarray:
    return np.array([math.factorial(k) for k in range(n + 1)], dtype=np.float64)


_FACT = _factorials(MAX_GOALS)


class PoissonModel:
    """Closed-form Poisson 1×2 from (lambda_home, lambda_away)."""

    def __init__(self, max_goals: int = MAX_GOALS, ovd_calibration: float = 1.0):
        self.max_goals = max_goals
        self.ovd_calibration = ovd_calibration

    def _score_matrix(self, lam_h: float, lam_a: float) -> np.ndarray:
        i = np.arange(self.max_goals + 1)
        ph = np.exp(-lam_h) * (lam_h ** i) / _FACT[: self.max_goals + 1]
        pa = np.exp(-lam_a) * (lam_a ** i) / _FACT[: self.max_goals + 1]
        return np.outer(ph, pa)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        out = []
        for row in np.atleast_2d(X):
            lam_h, lam_a = max(0.3, float(row[0])), max(0.3, float(row[1]))
            m = self._score_matrix(lam_h, lam_a)
            ph = np.tril(m, -1).sum()
            pd_ = np.trace(m) * self.ovd_calibration
            pa = np.triu(m, 1).sum()
            s = ph + pd_ + pa
            out.append([ph / s, pd_ / s, pa / s])
        return np.asarray(out)


class DixonColesModel(PoissonModel):
    """Poisson with low-score correlation correction (Dixon–Coles 1997)."""

    def __init__(self, rho: float = -0.10, max_goals: int = MAX_GOALS):
        super().__init__(max_goals=max_goals)
        self.rho = rho

    def _tau(self, h: int, a: int, lam_h: float, lam_a: float) -> float:
        if h == 0 and a == 0:
            return 1.0 - lam_h * lam_a * self.rho
        if h == 0 and a == 1:
            return 1.0 + lam_h * self.rho
        if h == 1 and a == 0:
            return 1.0 + lam_a * self.rho
        if h == 1 and a == 1:
            return 1.0 - self.rho
        return 1.0

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        out = []
        for row in np.atleast_2d(X):
            lam_h, lam_a = max(0.3, float(row[0])), max(0.3, float(row[1]))
            m = self._score_matrix(lam_h, lam_a)
            for h in range(2):
                for a in range(2):
                    m[h, a] *= self._tau(h, a, lam_h, lam_a)
            m = np.clip(m, 0.0, None)
            m /= m.sum()
            ph = np.tril(m, -1).sum()
            pd_ = np.trace(m)
            pa = np.triu(m, 1).sum()
            out.append([ph, pd_, pa])
        return np.asarray(out)


class EloModel:
    """Elo logistic with calibrated draw band on top of elo_diff."""

    def __init__(self, draw_band: float = 0.27, scale: float = 400.0,
                 home_advantage: float = 60.0):
        self.draw_band = draw_band
        self.scale = scale
        self.home_advantage = home_advantage

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        elo_diff = X[:, 2] + self.home_advantage
        p_home_no_draw = 1.0 / (1.0 + 10 ** (-elo_diff / self.scale))
        p_away_no_draw = 1.0 - p_home_no_draw
        d = self.draw_band * (1.0 - np.abs(p_home_no_draw - 0.5))
        ph = p_home_no_draw * (1.0 - d)
        pa = p_away_no_draw * (1.0 - d)
        out = np.stack([ph, d, pa], axis=1)
        out /= out.sum(axis=1, keepdims=True)
        return out


class BayesianNetModel:
    """Conjugate Bayesian update of a market prior with Poisson likelihood."""

    def __init__(self, prior=(0.45, 0.27, 0.28), strength: float = 5.0):
        self.prior = np.asarray(prior, dtype=float)
        self.strength = strength
        self._poisson = PoissonModel()

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        out = []
        for row in np.atleast_2d(X):
            lam_h, lam_a = max(0.3, float(row[0])), max(0.3, float(row[1]))
            m = self._poisson._score_matrix(lam_h, lam_a)
            ph = np.tril(m, -1).sum()
            pd_ = np.trace(m)
            pa = np.triu(m, 1).sum()
            lik = np.array([ph, pd_, pa])
            lik /= lik.sum()
            post = (self.prior ** self.strength) * lik
            post /= post.sum()
            out.append(post)
        return np.asarray(out)


class MarketImpliedModel:
    """Pure market baseline — Poisson on closing-odds-derived lambdas."""

    def __init__(self):
        self._poisson = PoissonModel()

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._poisson.predict_proba(X)


class TinySequenceModel:
    """
    CPU stand-in for lstm_v1 / transformer_v1: a one-layer softmax classifier
    trained on the same engineered features. Stores its weights as plain numpy
    arrays so it can be safely pickled and unpickled inside the API process.
    """

    def __init__(self, weights: np.ndarray, bias: np.ndarray,
                 mean: np.ndarray, std: np.ndarray):
        self.W = np.asarray(weights, dtype=np.float64)
        self.b = np.asarray(bias, dtype=np.float64)
        self.mean = np.asarray(mean, dtype=np.float64)
        std = np.asarray(std, dtype=np.float64)
        self.std = np.where(std > 1e-6, std, 1.0)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = (np.atleast_2d(X) - self.mean) / self.std
        z = X @ self.W + self.b
        z -= z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)


class StackedMetaModel:
    """Meta-learner over stacked base-model probabilities."""

    def __init__(self, base_models: list, meta):
        self.base_models = list(base_models)
        self.meta = meta

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.atleast_2d(X)
        stacked = np.hstack([m.predict_proba(X) for m in self.base_models])
        return self.meta.predict_proba(stacked)
