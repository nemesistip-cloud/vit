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


def test_validate_prediction_response_rejects_invalid_three_way_probs():
    payload = {"home_prob": 0.0, "draw_prob": 0.0, "away_prob": 0.0}
    with pytest.raises(ValueError, match="must include valid home, draw, and away probabilities"):
        validate_prediction_response(payload, sport="football")


def test_validate_prediction_response_rejects_invalid_three_way_probs_even_with_market_odds():
    payload = {"home_prob": 0.0, "draw_prob": 0.0, "away_prob": 0.0}
    market_odds = {"home": 2.10, "draw": 3.30, "away": 3.60}
    with pytest.raises(ValueError, match="must include valid home, draw, and away probabilities"):
        validate_prediction_response(payload, market_odds=market_odds, sport="football")


def test_validate_market_odds_rejects_equal_football_odds():
    assert not validate_market_odds({"home": 2.75, "draw": 2.75, "away": 2.75}, sport="football")


def test_validate_market_odds_rejects_invalid_two_way_odds():
    assert not validate_market_odds({"home": 2.0, "away": 2.0}, sport="tennis")


def test_validate_prediction_response_normalizes_negative_probs():
    payload = {"home_prob": -0.1, "draw_prob": 0.4, "away_prob": 0.7}
    normalized = validate_prediction_response(payload, sport="football")
    total = normalized["home_prob"] + normalized["draw_prob"] + normalized["away_prob"]
    assert abs(total - 1.0) < 1e-6
    assert normalized["home_prob"] == 0.0
    assert normalized["draw_prob"] > 0
    assert normalized["away_prob"] > 0


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
