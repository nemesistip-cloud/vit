from datetime import datetime, timedelta, timezone

from app.services.multi_sport_orchestrator import MultiSportOrchestrator


def test_missing_market_odds_use_neutral_football_prior():
    result = MultiSportOrchestrator()._generate_scie_football({"market_odds": {}})
    predictions = result["predictions"]

    assert predictions["home_prob"] == predictions["draw_prob"] == predictions["away_prob"]
    assert predictions["confidence"]["1x2"] < 0.5
    assert predictions["data_source"] == "vit_scie_v5_neutral_fallback"


def test_market_odds_can_still_select_away():
    result = MultiSportOrchestrator()._generate_scie_football(
        {"market_odds": {"home": 4.0, "draw": 3.4, "away": 1.8}}
    )
    predictions = result["predictions"]

    assert predictions["away_prob"] > predictions["home_prob"]
    assert predictions["away_prob"] > predictions["draw_prob"]
    assert predictions["data_source"] == "vit_scie_v5_fallback"


def test_fresh_football_form_adjusts_market_prediction():
    orchestrator = MultiSportOrchestrator()
    latest = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    market_odds = {"home": 2.1, "draw": 3.3, "away": 3.6}
    base = {
        "feature_completeness": 1.0,
        "home_history_sample_size": 10,
        "away_history_sample_size": 10,
        "home_history_latest": latest,
        "away_history_latest": latest,
        "evidence_providers": ["football-data-uk"],
    }
    home_form = {
        **base,
        "home_form_pts_10": 2.7,
        "away_form_pts_10": 0.6,
        "home_gf_pg_10": 2.0,
        "home_ga_pg_10": 0.8,
        "away_gf_pg_10": 0.8,
        "away_ga_pg_10": 2.0,
    }
    away_form = {
        **base,
        "home_form_pts_10": 0.6,
        "away_form_pts_10": 2.7,
        "home_gf_pg_10": 0.8,
        "home_ga_pg_10": 2.0,
        "away_gf_pg_10": 2.0,
        "away_ga_pg_10": 0.8,
    }

    home_result = orchestrator._generate_scie_football({
        "market_odds": market_odds, "match_features": home_form
    })["predictions"]
    away_result = orchestrator._generate_scie_football({
        "market_odds": market_odds, "match_features": away_form
    })["predictions"]

    assert home_result["home_prob"] > away_result["home_prob"]
    assert home_result["data_source"] == "vit_scie_v6_market_plus_real_form"


def test_stale_football_form_does_not_adjust_market_prediction():
    orchestrator = MultiSportOrchestrator()
    stale = "2015-04-26T00:00:00+00:00"
    features = {
        "market_odds": {"home": 2.1, "draw": 3.3, "away": 3.6},
        "match_features": {
            "feature_completeness": 1.0,
            "home_history_sample_size": 10,
            "away_history_sample_size": 10,
            "home_history_latest": stale,
            "away_history_latest": stale,
            "evidence_providers": ["football-data-uk"],
            "home_form_pts_10": 2.7,
            "away_form_pts_10": 0.6,
        },
    }

    predictions = orchestrator._generate_scie_football(features)["predictions"]

    assert predictions["data_source"] == "vit_scie_v5_fallback"