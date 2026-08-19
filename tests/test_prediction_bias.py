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