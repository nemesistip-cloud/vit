from datetime import datetime, timedelta, timezone

import numpy as np

from services.ml_service.odds_free_model import (
    fit_dixon_coles,
    load_platt_calibrators,
    predict_score_distribution,
    walk_forward_evaluate,
)


def _results():
    rows = []
    teams = ("A", "B", "C", "D")
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    for round_number in range(40):
        for home_index, home in enumerate(teams):
            away = teams[(home_index + round_number % (len(teams) - 1) + 1) % len(teams)]
            rows.append({
                "date": start + timedelta(days=round_number * 7 + home_index),
                "home_team": home,
                "away_team": away,
                "home_goals": (home_index + round_number) % 4,
                "away_goals": (home_index * 2 + round_number) % 3,
                "closing_odds_home": 99.0,
                "closing_odds_draw": 99.0,
                "closing_odds_away": 99.0,
            })
    return rows


def test_fit_uses_results_only_and_derives_markets_from_score_matrix():
    rows = _results()
    fitted = fit_dixon_coles(rows)
    prediction = predict_score_distribution(fitted, "A", "B")

    assert fitted.training_matches == len(rows)
    assert len(fitted.dataset_version) == 64
    assert np.isclose(
        prediction["home_prob"] + prediction["draw_prob"] + prediction["away_prob"],
        1.0,
    )
    assert np.isclose(sum(prediction["scoreline_probabilities"].values()), 1.0)
    assert np.isclose(
        prediction["over_25_prob"] + prediction["under_25_prob"], 1.0,
    )
    assert np.isclose(prediction["btts_prob"] + prediction["no_btts_prob"], 1.0)
    assert prediction["market_probabilities"]["over_2_5"] == prediction["over_25_prob"]


def test_unknown_team_uses_fitted_league_baseline_without_fake_rating():
    fitted = fit_dixon_coles(_results())
    result = predict_score_distribution(fitted, "Promoted FC", "A")

    assert 0.0 < result["home_prob"] < 1.0
    assert 0.0 < result["away_prob"] < 1.0


def test_closing_odds_do_not_change_fit_or_prediction():
    rows = _results()
    changed_odds = [
        {**row, "closing_odds_home": 1.01, "closing_odds_draw": 250.0, "closing_odds_away": 125.0}
        for row in rows
    ]
    original_fit = fit_dixon_coles(rows)
    changed_fit = fit_dixon_coles(changed_odds)

    assert original_fit.dataset_version == changed_fit.dataset_version
    assert predict_score_distribution(original_fit, "A", "B") == predict_score_distribution(
        changed_fit, "A", "B"
    )


def test_walk_forward_is_chronological_and_reports_market_benchmark_separately():
    provider_rows = []
    for row in _results():
        normalized = dict(row)
        normalized["kickoff_time"] = normalized.pop("date")
        normalized["closing_odds"] = {
            side: normalized.pop(f"closing_odds_{side}")
            for side in ("home", "draw", "away")
        }
        provider_rows.append(normalized)
    report = walk_forward_evaluate(
        provider_rows,
        min_train_matches=20,
        fold_period_months=3,
        min_calibration_samples=20,
    )

    assert report["out_of_sample"]["sample_size"] > 0
    assert report["out_of_sample"]["log_loss"] is not None
    assert report["out_of_sample"]["brier_score"] is not None
    assert report["out_of_sample"]["rps"] is not None
    assert report["out_of_sample"]["reliability"]
    assert report["closing_odds_benchmark"]["sample_size"] > 0
    assert report["paired_log_loss_difference"] is not None
    assert report["calibrated_out_of_sample"]["sample_size"] > 0
    artifact = report["calibration_artifact"]
    assert artifact["training_samples"] > 0
    assert len(artifact["calibration_version"]) == 64
    assert artifact["calibration_method"] == "platt"
    maps = load_platt_calibrators(artifact)
    calibrated = predict_score_distribution(fit_dixon_coles(_results()), "A", "B", maps)
    assert calibrated["calibration_applied"] is True
    assert np.isclose(sum(calibrated["scoreline_probabilities"].values()), 1.0)
    for fold in report["folds"]:
        assert datetime.fromisoformat(fold["training_end"]) < datetime.fromisoformat(fold["test_start"])