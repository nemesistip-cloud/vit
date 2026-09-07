from app.api.routes.odds_compare import _extract_h2h_odds, _prediction_ev


def test_ev_uses_model_probability_not_confidence():
    assert _prediction_ev("home", 0.38, {"home": 2.55}) == -0.03
    assert _prediction_ev("home", 0.65, {"home": 2.55}) == 0.66


def test_missing_probability_or_odds_produces_null_ev():
    assert _prediction_ev("home", None, {"home": 2.55}) is None
    assert _prediction_ev("home", 0.38, {"home": None}) is None


def test_extract_does_not_invent_pick_or_confidence():
    event = {
        "id": "fixture-1",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "commence_time": "2026-09-07T12:00:00Z",
        "bookmakers": [{
            "title": "Bookmaker",
            "markets": [{
                "key": "h2h",
                "outcomes": [
                    {"name": "Home FC", "price": 2.55},
                    {"name": "Draw", "price": 3.4},
                    {"name": "Away FC", "price": 2.8},
                ],
            }],
        }],
    }
    result = _extract_h2h_odds(event)
    assert result["ai_pick"] is None
    assert result["ai_confidence"] is None
    assert result["best_ev"] is None