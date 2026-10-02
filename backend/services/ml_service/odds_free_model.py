"""Odds-independent Dixon-Coles football score model."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, gammaln

MODEL_VERSION = "vit-dixon-coles-1.0.0"
FEATURE_VERSION = "match-results-xg-schedule-1.1.0"
MAX_SCORE_TAIL = 1e-8
MAX_MODEL_SEASONS = 12


@dataclass(frozen=True)
class HistoricalResult:
    date: datetime
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_xg: float | None = None
    away_xg: float | None = None
    closing_odds_home: float | None = None
    closing_odds_draw: float | None = None
    closing_odds_away: float | None = None


@dataclass(frozen=True)
class DixonColesFit:
    teams: tuple[str, ...]
    attack: np.ndarray
    defence: np.ndarray
    log_goal_rate: float
    home_advantage: float
    rho: float
    dataset_version: str
    training_matches: int


@dataclass(frozen=True)
class PlattMap:
    slope: float
    intercept: float

    def predict(self, values: Iterable[float]) -> np.ndarray:
        return expit(np.clip(self.slope * np.asarray(list(values), dtype=float) + self.intercept, -60.0, 60.0))


def _team_key(value: str) -> str:
    return " ".join(str(value).casefold().replace("&", "and").split())


def _finite_number(value: Any, minimum: float | None = None, exclusive: bool = False) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if minimum is not None and (number <= minimum if exclusive else number < minimum):
        return None
    return number


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


def _coerce_results(rows: Iterable[Any]) -> list[HistoricalResult]:
    results = []
    for row in rows:
        try:
            date = _row_value(row, "date", _row_value(row, "kickoff_time"))
            home = _row_value(row, "home_team")
            away = _row_value(row, "away_team")
            home_goals = _row_value(row, "home_goals")
            away_goals = _row_value(row, "away_goals")
            statistics = _row_value(row, "statistics")
            statistics = statistics if isinstance(statistics, dict) else {}
            closing_market = _row_value(row, "closing_odds")
            closing_market = closing_market if isinstance(closing_market, dict) else {}
            home_xg = _row_value(row, "home_xg", statistics.get("home_xg"))
            away_xg = _row_value(row, "away_xg", statistics.get("away_xg"))
            closing_odds = tuple(
                _row_value(row, f"closing_odds_{side}")
                or closing_market.get(side)
                for side in ("home", "draw", "away")
            )
            if isinstance(date, str):
                date = datetime.fromisoformat(date.replace("Z", "+00:00"))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            else:
                date = date.astimezone(timezone.utc)
            if not home or not away or home_goals is None or away_goals is None:
                continue
            home_goals, away_goals = int(home_goals), int(away_goals)
            if home_goals < 0 or away_goals < 0 or _team_key(home) == _team_key(away):
                continue
            home_xg = _finite_number(home_xg, minimum=0.0)
            away_xg = _finite_number(away_xg, minimum=0.0)
            closing_odds = tuple(_finite_number(price, minimum=1.0, exclusive=True) for price in closing_odds)
            results.append(HistoricalResult(
                date, str(home).strip(), str(away).strip(), home_goals, away_goals,
                home_xg, away_xg, *closing_odds,
            ))
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            continue
    return sorted(results, key=lambda result: result.date)


def _dataset_version(results: list[HistoricalResult]) -> str:
    signature = [
        (
            result.date.isoformat(), _team_key(result.home_team), _team_key(result.away_team),
            result.home_goals, result.away_goals, result.home_xg, result.away_xg,
        )
        for result in results
    ]
    return hashlib.sha256(json.dumps(signature, separators=(",", ":")).encode("utf-8")).hexdigest()


def fit_platt_calibrators(
    observations: list[tuple[np.ndarray, int]],
    min_samples: int = 100,
) -> dict[str, PlattMap]:
    """Fit regularized one-vs-rest Platt maps on earlier OOS forecasts only."""
    if len(observations) < min_samples:
        return {}
    from sklearn.linear_model import LogisticRegression

    probabilities = np.asarray([item[0] for item in observations], dtype=float)
    labels = np.asarray([item[1] for item in observations], dtype=int)
    maps = {}
    for class_index, class_name in enumerate(("home", "draw", "away")):
        targets = (labels == class_index).astype(int)
        if len(np.unique(targets)) < 2:
            continue
        estimator = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000).fit(
            probabilities[:, class_index].reshape(-1, 1), targets
        )
        maps[class_name] = PlattMap(
            slope=float(estimator.coef_[0, 0]),
            intercept=float(estimator.intercept_[0]),
        )
    return maps


def platt_calibration_artifact(
    calibrators: dict[str, PlattMap],
    results: list[HistoricalResult],
    training_samples: int,
) -> dict[str, Any] | None:
    if not calibrators or not results:
        return None
    calibration_data = {
        key: {"slope": calibrators[key].slope, "intercept": calibrators[key].intercept}
        for key in sorted(calibrators)
    }
    version = hashlib.sha256(
        json.dumps(calibration_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "calibration_method": "platt",
        "calibration_version": version,
        "dataset_version": _dataset_version(results),
        "training_cutoff": max(result.date for result in results).isoformat(),
        "training_samples": training_samples,
        "calibrators": calibration_data,
    }


def load_platt_calibrators(artifact: dict[str, Any]) -> dict[str, PlattMap]:
    if artifact.get("model_version") != MODEL_VERSION or artifact.get("calibration_method") != "platt":
        return {}
    output = {}
    for class_name, thresholds in (artifact.get("calibrators") or {}).items():
        try:
            slope = float(thresholds["slope"])
            intercept = float(thresholds["intercept"])
            if math.isfinite(slope) and math.isfinite(intercept):
                output[class_name] = PlattMap(slope, intercept)
        except (KeyError, TypeError, ValueError):
            continue
    return output


def _dc_tau(home_goals: int, away_goals: int, lam_home: float, lam_away: float, rho: float) -> float:
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lam_home * lam_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lam_home * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + lam_away * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def fit_dixon_coles(rows: Iterable[Any]) -> DixonColesFit:
    """Fit attack, defence, home advantage and low-score correlation by MLE."""
    results = _coerce_results(rows)
    if len(results) < 2:
        raise ValueError("At least two valid historical results are required to fit Dixon-Coles")

    teams = tuple(sorted({_team_key(result.home_team) for result in results} | {
        _team_key(result.away_team) for result in results
    }))
    team_index = {team: index for index, team in enumerate(teams)}
    home_idx = np.asarray([team_index[_team_key(result.home_team)] for result in results], dtype=int)
    away_idx = np.asarray([team_index[_team_key(result.away_team)] for result in results], dtype=int)
    home_goals = np.asarray([result.home_goals for result in results], dtype=int)
    away_goals = np.asarray([result.away_goals for result in results], dtype=int)
    observed_mean = float(np.mean(np.concatenate((home_goals, away_goals))))
    initial = np.zeros(2 * len(teams) + 3, dtype=float)
    initial[0] = math.log(max(observed_mean, np.finfo(float).tiny))

    def objective(params: np.ndarray) -> float:
        log_rate = params[0]
        home_advantage = params[1]
        attack = params[2:2 + len(teams)]
        defence = params[2 + len(teams):2 + 2 * len(teams)]
        rho = params[-1]
        attack = attack - attack.mean()
        defence = defence - defence.mean()
        log_home = log_rate + home_advantage + attack[home_idx] - defence[away_idx]
        log_away = log_rate + attack[away_idx] - defence[home_idx]
        if np.any(np.abs(log_home) > 20) or np.any(np.abs(log_away) > 20):
            return np.finfo(float).max / 100
        lam_home, lam_away = np.exp(log_home), np.exp(log_away)
        tau = np.ones_like(lam_home)
        zero_zero = (home_goals == 0) & (away_goals == 0)
        zero_one = (home_goals == 0) & (away_goals == 1)
        one_zero = (home_goals == 1) & (away_goals == 0)
        one_one = (home_goals == 1) & (away_goals == 1)
        tau[zero_zero] = 1.0 - lam_home[zero_zero] * lam_away[zero_zero] * rho
        tau[zero_one] = 1.0 + lam_home[zero_one] * rho
        tau[one_zero] = 1.0 + lam_away[one_zero] * rho
        tau[one_one] = 1.0 - rho
        if np.any(tau <= 0) or not np.all(np.isfinite(tau)):
            return np.finfo(float).max / 100
        log_likelihood = (
            home_goals * log_home - lam_home - gammaln(home_goals + 1)
            + away_goals * log_away - lam_away - gammaln(away_goals + 1)
            + np.log(tau)
        )
        return -float(np.sum(log_likelihood))

    bounds = [(None, None)] * (len(initial) - 1) + [(-0.5, 0.5)]
    fit = minimize(objective, initial, method="L-BFGS-B", bounds=bounds)
    if not fit.success and not np.isfinite(fit.fun):
        raise ValueError("Dixon-Coles maximum-likelihood fit did not converge")
    params = fit.x
    attack = params[2:2 + len(teams)]
    defence = params[2 + len(teams):2 + 2 * len(teams)]
    attack = attack - attack.mean()
    defence = defence - defence.mean()
    dataset_version = _dataset_version(results)
    return DixonColesFit(
        teams=teams,
        attack=attack,
        defence=defence,
        log_goal_rate=float(params[0]),
        home_advantage=float(params[1]),
        rho=float(params[-1]),
        dataset_version=dataset_version,
        training_matches=len(results),
    )


def predict_score_distribution(
    fit: DixonColesFit,
    home_team: str,
    away_team: str,
    calibration: dict[str, PlattMap] | None = None,
) -> dict[str, Any]:
    """Return a normalized scoreline distribution and derived football markets."""
    team_index = {team: index for index, team in enumerate(fit.teams)}
    home_key, away_key = _team_key(home_team), _team_key(away_team)
    home_attack = fit.attack[team_index[home_key]] if home_key in team_index else 0.0
    away_attack = fit.attack[team_index[away_key]] if away_key in team_index else 0.0
    home_defence = fit.defence[team_index[home_key]] if home_key in team_index else 0.0
    away_defence = fit.defence[team_index[away_key]] if away_key in team_index else 0.0
    lam_home = math.exp(fit.log_goal_rate + fit.home_advantage + home_attack - away_defence)
    lam_away = math.exp(fit.log_goal_rate + away_attack - home_defence)

    max_goals = max(8, int(math.ceil(max(lam_home, lam_away) + 8 * math.sqrt(max(lam_home, lam_away)))))
    goals = np.arange(max_goals + 1)
    home_pmf = np.exp(-lam_home + goals * math.log(lam_home) - gammaln(goals + 1))
    away_pmf = np.exp(-lam_away + goals * math.log(lam_away) - gammaln(goals + 1))
    matrix = np.outer(home_pmf, away_pmf)
    matrix[0, 0] *= _dc_tau(0, 0, lam_home, lam_away, fit.rho)
    matrix[0, 1] *= _dc_tau(0, 1, lam_home, lam_away, fit.rho)
    matrix[1, 0] *= _dc_tau(1, 0, lam_home, lam_away, fit.rho)
    matrix[1, 1] *= _dc_tau(1, 1, lam_home, lam_away, fit.rho)
    matrix = np.clip(matrix, 0.0, None)
    total = float(matrix.sum())
    if not math.isfinite(total) or total <= 0:
        raise ValueError("Fitted goal rates did not produce a valid scoreline distribution")
    matrix /= total

    calibration_applied = False
    if calibration:
        outcome_masks = (
            np.tril(np.ones_like(matrix, dtype=bool), -1),
            np.eye(max_goals + 1, dtype=bool),
            np.triu(np.ones_like(matrix, dtype=bool), 1),
        )
        outcome_names = ("home", "draw", "away")
        raw_marginals = [float(matrix[mask].sum()) for mask in outcome_masks]
        target_marginals = []
        for name, raw_probability in zip(outcome_names, raw_marginals):
            calibrator = calibration.get(name)
            if calibrator is None:
                target_marginals.append(raw_probability)
                continue
            target_marginals.append(float(calibrator.predict([raw_probability])[0]))
            calibration_applied = True
        target_sum = sum(target_marginals)
        if calibration_applied and target_sum > 0:
            target_marginals = [value / target_sum for value in target_marginals]
            for mask, raw_probability, target_probability in zip(
                outcome_masks, raw_marginals, target_marginals
            ):
                if raw_probability > 0:
                    matrix[mask] *= target_probability / raw_probability
            matrix /= matrix.sum()

    home_probability = float(np.tril(matrix, -1).sum())
    draw_probability = float(np.trace(matrix))
    away_probability = float(np.triu(matrix, 1).sum())
    over_25 = float(sum(matrix[h, a] for h in range(max_goals + 1) for a in range(max_goals + 1) if h + a > 2))
    btts = float(matrix[1:, 1:].sum())
    scorelines = {
        f"{home_goals}-{away_goals}": float(matrix[home_goals, away_goals])
        for home_goals in range(max_goals + 1)
        for away_goals in range(max_goals + 1)
    }
    return {
        "home_prob": home_probability,
        "draw_prob": draw_probability,
        "away_prob": away_probability,
        "over_25_prob": over_25,
        "under_25_prob": 1.0 - over_25,
        "btts_prob": btts,
        "no_btts_prob": 1.0 - btts,
        "market_probabilities": {
            "over_1_5": float(sum(matrix[h, a] for h in range(max_goals + 1) for a in range(max_goals + 1) if h + a > 1)),
            "over_2_5": over_25,
            "over_3_5": float(sum(matrix[h, a] for h in range(max_goals + 1) for a in range(max_goals + 1) if h + a > 3)),
            "btts_yes": btts,
            "btts_no": 1.0 - btts,
        },
        "home_goals_expectation": lam_home,
        "away_goals_expectation": lam_away,
        "scoreline_probabilities": scorelines,
        "calibration_applied": calibration_applied,
    }


def _outcome_index(home_goals: int, away_goals: int) -> int:
    return 0 if home_goals > away_goals else 1 if home_goals == away_goals else 2


def _scoring_metrics(observations: list[tuple[np.ndarray, int]]) -> dict[str, Any]:
    if not observations:
        return {"sample_size": 0, "log_loss": None, "brier_score": None, "rps": None, "reliability": {}}

    probabilities = np.asarray([item[0] for item in observations], dtype=float)
    labels = np.asarray([item[1] for item in observations], dtype=int)
    one_hot = np.eye(3)[labels]
    clipped = np.clip(probabilities, np.finfo(float).tiny, 1.0)
    log_loss = -float(np.log(clipped[np.arange(len(labels)), labels]).mean())
    brier = float(np.square(probabilities - one_hot).sum(axis=1).mean())

    ordered_probabilities = probabilities[:, [2, 1, 0]]
    ordered_labels = (2 - labels)
    ordered_one_hot = np.eye(3)[ordered_labels]
    rps = float(np.square(
        np.cumsum(ordered_probabilities, axis=1)[:, :2]
        - np.cumsum(ordered_one_hot, axis=1)[:, :2]
    ).sum(axis=1).mean() / 2.0)

    reliability = {}
    for class_index, class_name in enumerate(("home", "draw", "away")):
        class_probabilities = probabilities[:, class_index]
        class_labels = one_hot[:, class_index]
        bins = []
        calibration_error = 0.0
        for bin_index in range(10):
            lower, upper = bin_index / 10.0, (bin_index + 1) / 10.0
            in_bin = (class_probabilities >= lower) & (
                (class_probabilities <= upper) if bin_index == 9 else (class_probabilities < upper)
            )
            count = int(in_bin.sum())
            if count:
                predicted = float(class_probabilities[in_bin].mean())
                observed = float(class_labels[in_bin].mean())
                calibration_error += count / len(labels) * abs(predicted - observed)
                bins.append({
                    "lower": lower,
                    "upper": upper,
                    "count": count,
                    "mean_probability": predicted,
                    "observed_frequency": observed,
                })
        reliability[class_name] = {"expected_calibration_error": calibration_error, "bins": bins}

    return {
        "sample_size": len(observations),
        "log_loss": log_loss,
        "brier_score": brier,
        "rps": rps,
        "reliability": reliability,
    }


def _closing_market_probabilities(result: HistoricalResult) -> np.ndarray | None:
    prices = (result.closing_odds_home, result.closing_odds_draw, result.closing_odds_away)
    if any(price is None or not math.isfinite(price) or price <= 1.0 for price in prices):
        return None
    implied = np.reciprocal(np.asarray(prices, dtype=float))
    return implied / implied.sum()


def _single_distribution_metric(probabilities: np.ndarray, label: int, metric: str) -> float:
    probabilities = np.asarray(probabilities, dtype=float)
    if metric == "log_loss":
        clipped = np.clip(probabilities, np.finfo(float).tiny, 1.0)
        return float(-math.log(clipped[label]))
    if metric == "brier":
        one_hot = np.eye(3)[label]
        return float(np.sum((probabilities - one_hot) ** 2))
    if metric == "rps":
        ordered = probabilities[[2, 1, 0]]
        ordered_label = np.eye(3)[(2 - label)][[2, 1, 0]]
        cdf_pred = np.cumsum(ordered)
        cdf_true = np.cumsum(ordered_label)
        return float(np.sum((cdf_pred[:-1] - cdf_true[:-1]) ** 2) / 2.0)
    raise ValueError(f"Unsupported metric: {metric}")


def _paired_metric_summary(
    raw_observations: list[tuple[np.ndarray, int]],
    candidate_observations: list[tuple[np.ndarray, int]],
    metric: str,
) -> dict[str, Any]:
    if not raw_observations or not candidate_observations:
        return {"n": 0, "mean_difference": None, "std_error": None, "ci95": [None, None], "candidate_better": None, "ci_excludes_zero": None}
    if len(raw_observations) != len(candidate_observations):
        raise ValueError("Paired comparisons require identical fixture sets")
    diffs = []
    for (raw_probs, label), (candidate_probs, _) in zip(raw_observations, candidate_observations):
        diffs.append(
            _single_distribution_metric(raw_probs, label, metric)
            - _single_distribution_metric(candidate_probs, label, metric)
        )
    diffs = np.asarray(diffs, dtype=float)
    mean_diff = float(np.mean(diffs))
    std_error = float(np.std(diffs, ddof=1) / math.sqrt(len(diffs))) if len(diffs) > 1 else 0.0
    ci95 = [mean_diff - 1.96 * std_error, mean_diff + 1.96 * std_error]
    return {
        "n": len(diffs),
        "mean_difference": mean_diff,
        "std_error": std_error,
        "ci95": ci95,
        "candidate_better": mean_diff < 0.0,
        "ci_excludes_zero": ci95[0] > 0.0 or ci95[1] < 0.0,
    }


def walk_forward_evaluate(
    rows: Iterable[Any],
    min_train_matches: int = 760,
    fold_period_months: int = 12,
    min_calibration_samples: int = 100,
) -> dict[str, Any]:
    """Evaluate expanding chronological forecasts; close odds are benchmark-only."""
    if not 1 <= fold_period_months <= 12:
        raise ValueError("fold_period_months must be between 1 and 12")
    results = _coerce_results(rows)
    if results:
        latest_season = max(
            result.date.year if result.date.month >= 7 else result.date.year - 1
            for result in results
        )
        first_season = latest_season - MAX_MODEL_SEASONS + 1
        results = [
            result for result in results
            if (result.date.year if result.date.month >= 7 else result.date.year - 1) >= first_season
        ]

    grouped: dict[tuple[int, int], list[HistoricalResult]] = {}
    for result in results:
        season = result.date.year if result.date.month >= 7 else result.date.year - 1
        season_month = (result.date.month - 7) % 12
        period = season_month // fold_period_months
        grouped.setdefault((season, period), []).append(result)

    model_observations: list[tuple[np.ndarray, int]] = []
    calibrated_observations: list[tuple[np.ndarray, int]] = []
    market_observations: list[tuple[np.ndarray, int]] = []
    prior_oos_observations: list[tuple[np.ndarray, int]] = []
    oos_results: list[HistoricalResult] = []
    folds = []
    for (season, period), test_results in sorted(grouped.items()):
        test_start = min(result.date for result in test_results)
        training = [result for result in results if result.date < test_start]
        if len(training) < min_train_matches:
            continue
        latest_training_season = max(
            result.date.year if result.date.month >= 7 else result.date.year - 1
            for result in training
        )
        training = [
            result for result in training
            if (result.date.year if result.date.month >= 7 else result.date.year - 1)
            >= latest_training_season - MAX_MODEL_SEASONS + 1
        ]
        if len(training) < min_train_matches:
            continue
        fitted = fit_dixon_coles(training)
        period_calibrators = (
            fit_platt_calibrators(
                prior_oos_observations, min_samples=min_calibration_samples
            )
            if len(prior_oos_observations) >= min_calibration_samples
            else {}
        )
        fold_oos_observations = []
        for result in test_results:
            prediction = predict_score_distribution(fitted, result.home_team, result.away_team)
            probabilities = np.asarray([
                prediction["home_prob"], prediction["draw_prob"], prediction["away_prob"]
            ])
            label = _outcome_index(result.home_goals, result.away_goals)
            model_observations.append((probabilities, label))
            fold_oos_observations.append((probabilities, label))
            if period_calibrators:
                calibrated_prediction = predict_score_distribution(
                    fitted, result.home_team, result.away_team, calibration=period_calibrators
                )
                calibrated_observations.append((np.asarray([
                    calibrated_prediction["home_prob"],
                    calibrated_prediction["draw_prob"],
                    calibrated_prediction["away_prob"],
                ]), label))
            market_probabilities = _closing_market_probabilities(result)
            if market_probabilities is not None:
                market_observations.append((market_probabilities, label))
        prior_oos_observations.extend(fold_oos_observations)
        oos_results.extend(test_results)
        folds.append({
            "period": f"{season}-P{period + 1}",
            "training_matches": len(training),
            "test_matches": len(test_results),
            "training_end": max(result.date for result in training).isoformat(),
            "test_start": test_start.isoformat(),
        })

    model_metrics = _scoring_metrics(model_observations)
    calibrated_metrics = _scoring_metrics(calibrated_observations)
    market_metrics = _scoring_metrics(market_observations)
    model_metrics["validation_method"] = "expanding_seasonal_period"
    calibrated_metrics["validation_method"] = "prior_oos_isotonic_on_expanding_periods"
    market_metrics["validation_method"] = "closing_odds_de_vig_benchmark"
    final_calibrators = fit_platt_calibrators(
        prior_oos_observations, min_samples=min_calibration_samples
    )
    calibration_artifact = platt_calibration_artifact(
        final_calibrators, oos_results, len(prior_oos_observations)
    )
    return {
        "model_version": MODEL_VERSION,
        "dataset_version": _dataset_version(results) if len(results) >= 2 else None,
        "folds": folds,
        "out_of_sample": model_metrics,
        "calibrated_out_of_sample": calibrated_metrics,
        "closing_odds_benchmark": market_metrics,
        "calibration_artifact": calibration_artifact,
        "paired_log_loss_difference": (
            model_metrics["log_loss"] - market_metrics["log_loss"]
            if model_metrics["log_loss"] is not None and market_metrics["log_loss"] is not None
            else None
        ),
    }