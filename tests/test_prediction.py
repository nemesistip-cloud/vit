"""
Tests for the /predict endpoint.
With AUTH_ENABLED=false (set in conftest), verify_api_key passes through,
so predictions work without a token by default.
"""
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.api.routes.predict import validate_market_odds, validate_prediction_response
from app.api.routes import predict as predict_route
from app.services.multi_sport_orchestrator import MultiSportOrchestrator
from app.services.odds_free_prediction import load_historical_results
from app.services.predict_features import build_predict_features
from app.services import web_search
from main import app


def _client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def _match_payload(home="Arsenal", away="Chelsea"):
    return {
        "home_team": home,
        "away_team": away,
        "league": "Premier League",
        "kickoff_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "market_odds": {"home": 2.10, "draw": 3.30, "away": 3.60},
    }


@pytest.mark.asyncio
async def test_predict_returns_probabilities():
    async with _client() as client:
        resp = await client.post("/api/predict", json=_match_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert "home_prob" in data
    assert "draw_prob" in data
    assert "away_prob" in data


@pytest.mark.asyncio
async def test_football_prediction_works_without_market_odds():
    payload = _match_payload()
    payload["market_odds"] = {}
    async with _client() as client:
        response = await client.post("/api/predict", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["data_source"] == "odds_free_dixon_coles"
    assert data["entry_odds"] is None
    assert data["bet_side"] is None
    assert data["final_ev"] is None
    assert data["edge"] is None
    assert data["provenance"]["model_version"] == "vit-dixon-coles-1.0.0"
    assert data["provenance"]["training_matches"] >= 760
    assert len(data["provenance"]["dataset_version"]) == 64
    assert abs(sum(data["cs_probs"].values()) - 1.0) < 1e-8


@pytest.mark.asyncio
async def test_predict_probabilities_sum_to_one():
    async with _client() as client:
        resp = await client.post("/api/predict", json=_match_payload())
    assert resp.status_code == 200
    data = resp.json()
    total = data["home_prob"] + data["draw_prob"] + data["away_prob"]
    assert abs(total - 1.0) < 0.05


@pytest.mark.asyncio
async def test_predict_includes_confidence():
    async with _client() as client:
        resp = await client.post("/api/predict", json=_match_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_predict_includes_model_info():
    async with _client() as client:
        resp = await client.post("/api/predict", json=_match_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert "models_used" in data or "model" in data or "recommended_bet" in data


@pytest.mark.asyncio
async def test_predict_missing_required_field_returns_422():
    async with _client() as client:
        resp = await client.post("/api/predict", json={
            "away_team": "Chelsea",
            "league": "Premier League",
            "kickoff_time": datetime.now(timezone.utc).isoformat(),
        })
    assert resp.status_code == 422


def test_validate_prediction_response_rejects_invalid_two_way_probs():
    payload = {"home_prob": 0.0, "away_prob": 0.0}
    with pytest.raises(ValueError, match="must include valid home and away probabilities"):
        validate_prediction_response(payload, sport="basketball")


@pytest.mark.asyncio
async def test_predict_accepts_valid_two_way_market_odds_for_basketball():
    payload = {
        "home_team": "Atlanta Dream",
        "away_team": "Connecticut Sun",
        "league": "WNBA",
        "kickoff_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "sport": "basketball",
        "market_odds": {"home": 1.87, "away": 1.96},
    }
    async with _client() as client:
        resp = await client.post("/api/predict", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["draw_prob"] == 0.0
    assert data["bet_side"] in {"home", "away"}


@pytest.mark.asyncio
async def test_predict_accepts_valid_two_way_market_odds_for_rugby():
    payload = {
        "home_team": "Castres Olympique",
        "away_team": "RC Toulonnais",
        "league": "French Top 14",
        "kickoff_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "sport": "rugby",
        "market_odds": {"home": 1.80, "away": 2.05},
    }
    async with _client() as client:
        resp = await client.post("/api/predict", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["draw_prob"] == 0.0
    assert data["bet_side"] in {"home", "away"}


def test_validate_prediction_response_rejects_invalid_three_way_probs():
    payload = {"home_prob": 0.0, "draw_prob": 0.0, "away_prob": 0.0}
    with pytest.raises(ValueError, match="must include valid home, draw, and away probabilities"):
        validate_prediction_response(payload, sport="football")


def test_validate_prediction_response_rejects_invalid_three_way_probs_even_with_market_odds():
    payload = {"home_prob": 0.0, "draw_prob": 0.0, "away_prob": 0.0}
    market_odds = {"home": 2.10, "draw": 3.30, "away": 3.60}
    with pytest.raises(ValueError, match="must include valid home, draw, and away probabilities"):
        validate_prediction_response(payload, market_odds=market_odds, sport="football")


def test_validate_market_odds_allows_no_odds_for_two_way_sports():
    assert validate_market_odds({}, sport="basketball") is True
    assert validate_market_odds({"home": 2.10, "away": 2.20}, sport="basketball") is True


def test_validate_market_odds_rejects_equal_football_odds():
    assert not validate_market_odds({"home": 2.75, "draw": 2.75, "away": 2.75}, sport="football")


def test_validate_market_odds_rejects_invalid_two_way_odds():
    assert not validate_market_odds({"home": 2.0, "away": 2.0}, sport="tennis")


@pytest.mark.asyncio
async def test_load_historical_results_filters_db_query_to_league_and_recent_window():
    class _StubResult:
        def all(self):
            return []

    class _StubDB:
        def __init__(self):
            self.statement = None

        async def execute(self, statement):
            self.statement = statement
            return _StubResult()

    db = _StubDB()
    cutoff = datetime(2026, 10, 10, tzinfo=timezone.utc)

    await load_historical_results(db, "Premier League", cutoff)

    assert db.statement is not None
    sql = str(db.statement.compile(compile_kwargs={"literal_binds": True})).lower()
    assert "league" in sql
    assert "premier league" in sql
    assert "kickoff_time" in sql
    assert "<" in sql or ">=" in sql


@pytest.mark.asyncio
async def test_build_predict_features_uses_static_csv_evidence_when_db_is_empty():
    features = await build_predict_features(None, "Knicks", "Celtics", league="NBA")
    assert features["feature_completeness"] > 0.0
    assert features["home_history_sample_size"] > 0
    assert features["away_history_sample_size"] > 0
    assert features.get("evidence_source") in {"static_csv", "mixed"}


@pytest.mark.asyncio
async def test_latest_espn_nba_history_enables_raptors_heat_prediction():
    features = await build_predict_features(
        None, "Toronto Raptors", "Miami Heat", league="NBA", sport="basketball"
    )
    result = MultiSportOrchestrator()._predict_two_way_statistical(
        {"match_features": features}, "basketball"
    )

    assert "espn_public_api" in features["evidence_providers"]
    assert features["home_history_sample_size"] >= 10
    assert features["away_history_sample_size"] >= 10
    assert features["home_history_latest"].startswith("2026-")
    assert features["away_history_latest"].startswith("2026-")
    assert result["status"] == "ready"
    assert 0.0 < result["predictions"]["home_prob"] < 1.0
    assert 0.0 < result["predictions"]["away_prob"] < 1.0


@pytest.mark.asyncio
async def test_football_prediction_uses_current_public_premier_league_history():
    features = await build_predict_features(
        None, "Arsenal", "Chelsea", league="Premier League", sport="football"
    )
    prediction = MultiSportOrchestrator()._generate_scie_football({
        "market_odds": {"home": 2.11, "draw": 3.3, "away": 3.6},
        "match_features": features,
    })["predictions"]

    assert features["home_history_sample_size"] >= 10
    assert features["away_history_sample_size"] >= 10
    assert features["home_history_latest"].startswith("2026-09")
    assert features["away_history_latest"].startswith("2026-09")
    assert {"football-data-uk", "github-premier-league-data"} & set(features["evidence_providers"])
    assert prediction["data_source"] == "vit_scie_v6_market_plus_real_form"


@pytest.mark.asyncio
async def test_predict_endpoint_uses_public_football_form(monkeypatch):
    captured_features = {}

    async def public_features(db, home_team, away_team, league=None, before=None, sport=None):
        features = await build_predict_features(
            None, home_team, away_team, league, before=before, sport=sport
        )
        captured_features.update(features)
        return features

    async def no_web_context(*args, **kwargs):
        return {}

    monkeypatch.setattr(predict_route, "build_predict_features", public_features)
    monkeypatch.setattr(web_search, "fetch_match_context", no_web_context)
    monkeypatch.setattr(web_search, "format_context_for_prompt", lambda *args, **kwargs: "")
    payload = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "league": "Premier League",
        "kickoff_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "sport": "football",
        "market_odds": {"home": 2.11, "draw": 3.3, "away": 3.6},
    }

    async with _client() as client:
        response = await client.post("/api/predict", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert "football-data-uk" in captured_features.get("evidence_providers", []), captured_features
    assert captured_features["home_history_sample_size"] >= 10
    assert captured_features["away_history_sample_size"] >= 10
    assert data["data_quality"]["feature_completeness"] >= 0.55


@pytest.mark.asyncio
async def test_trained_football_ensemble_uses_fresh_public_form():
    from services.ml_service.models.model_orchestrator import ModelOrchestrator

    features = await build_predict_features(
        None, "Arsenal", "Chelsea", league="Premier League", sport="football"
    )
    market_odds = {"home": 2.1, "draw": 3.3, "away": 3.6}
    model = ModelOrchestrator()
    base_features = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "league": "premier_league",
        "market_odds": market_odds,
        "match_features": features,
    }
    home_form_result = await model.predict(base_features, "football-form-regression", sport="soccer")

    away_form = dict(features)
    for home_key, away_key in (
        ("home_form_pts_10", "away_form_pts_10"),
        ("home_gf_pg_10", "away_gf_pg_10"),
        ("home_ga_pg_10", "away_ga_pg_10"),
    ):
        away_form[home_key], away_form[away_key] = features[away_key], features[home_key]
    away_form_result = await model.predict(
        {**base_features, "match_features": away_form},
        "football-form-regression",
        sport="soccer",
    )

    predictions = home_form_result["predictions"]
    assert predictions["data_source"] == "differentiated_ensemble_v5_market_plus_real_form"
    assert "football-data-uk" in predictions["evidence_providers"] or "github-premier-league-data" in predictions["evidence_providers"]
    assert predictions["home_prob"] != away_form_result["predictions"]["home_prob"]


@pytest.mark.asyncio
async def test_predict_surfaces_unavailable_evidence_reason(monkeypatch):
    async def stale_features(*args, **kwargs):
        return {
            "feature_completeness": 1.0,
            "home_history_sample_size": 10,
            "away_history_sample_size": 10,
            "history_sample_size": 10,
            "home_history_latest": "2015-04-26T00:00:00",
            "away_history_latest": "2015-04-15T00:00:00",
            "evidence_source": "static_csv",
        }

    async def no_web_context(*args, **kwargs):
        return {}

    monkeypatch.setattr(predict_route, "build_predict_features", stale_features)
    monkeypatch.setattr(web_search, "fetch_match_context", no_web_context)
    monkeypatch.setattr(web_search, "format_context_for_prompt", lambda *args, **kwargs: "")
    payload = {
        "home_team": "Toronto Raptors",
        "away_team": "Miami Heat",
        "league": "NBA",
        "kickoff_time": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "sport": "basketball",
        "market_odds": {},
    }
    async with _client() as client:
        response = await client.post("/api/predict", json=payload)

    assert response.status_code == 422
    body = response.json()
    detail = body.get("detail", body)
    assert "status" in detail, response.text
    assert detail["status"] == "unavailable"
    assert detail["evidence_source"] == "static_csv"
    assert any("stale" in reason.lower() for reason in detail["reasons"])


def test_no_odds_basketball_prediction_uses_real_history_when_available():
    orch = MultiSportOrchestrator()
    result = orch._predict_two_way_statistical({
        "match_features": {
            "feature_completeness": 0.96,
            "home_history_sample_size": 7,
            "away_history_sample_size": 6,
            "history_sample_size": 7,
            "home_form_pts_10": 2.7,
            "away_form_pts_10": 2.2,
            "home_gf_pg_10": 112.0,
            "away_gf_pg_10": 105.0,
            "home_ga_pg_10": 101.0,
            "away_ga_pg_10": 110.0,
        }
    }, "basketball")
    assert result["status"] == "ready"
    home = result["predictions"]["home_prob"]
    away = result["predictions"]["away_prob"]
    assert 0.0 < home < 1.0
    assert 0.15 < home < 0.85
    assert 0.0 < away < 1.0
    assert abs((home + away) - 1.0) < 1e-6


def test_no_odds_basketball_prediction_rejects_stale_history():
    orch = MultiSportOrchestrator()
    result = orch._predict_two_way_statistical({
        "match_features": {
            "feature_completeness": 1.0,
            "home_history_sample_size": 10,
            "away_history_sample_size": 10,
            "history_sample_size": 10,
            "home_history_latest": "2015-04-26T00:00:00",
            "away_history_latest": "2015-04-15T00:00:00",
        }
    }, "basketball")
    assert result["status"] == "unavailable"
    assert any("stale" in reason.lower() for reason in result["reasons"])


def test_no_odds_basketball_prediction_is_unavailable_when_evidence_is_insufficient():
    orch = MultiSportOrchestrator()
    result = orch._predict_two_way_statistical({
        "match_features": {
            "feature_completeness": 0.2,
            "home_history_sample_size": 1,
            "away_history_sample_size": 1,
            "history_sample_size": 1,
        }
    }, "basketball")
    assert result["status"] == "unavailable"
    assert result["reasons"]


def test_validate_prediction_response_normalizes_negative_probs():
    payload = {"home_prob": -0.1, "draw_prob": 0.4, "away_prob": 0.7}
    with pytest.raises(ValueError, match="must be within the range"):
        validate_prediction_response(payload, sport="football")


@pytest.mark.asyncio
async def test_predict_idempotent_on_same_match():
    """First prediction succeeds; posting the same match again is handled gracefully."""
    payload = _match_payload("Liverpool", "ManCity")
    async with _client() as client:
        r1 = await client.post("/api/predict", json=payload)
        r2 = await client.post("/api/predict", json=payload)
    assert r1.status_code == 200
    assert r2.status_code in (200, 409)


@pytest.mark.asyncio
async def test_predict_with_extreme_odds():
    """Should return valid probabilities or a handled error with unusual odds."""
    payload = _match_payload("Barca", "Atletico")
    payload["market_odds"] = {"home": 1.10, "draw": 8.00, "away": 20.0}
    async with _client() as client:
        resp = await client.post("/api/predict", json=payload)
    assert resp.status_code in (200, 429)
    if resp.status_code == 200:
        data = resp.json()
        total = data["home_prob"] + data["draw_prob"] + data["away_prob"]
        assert abs(total - 1.0) < 0.05
