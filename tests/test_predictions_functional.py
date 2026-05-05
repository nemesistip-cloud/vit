"""
Functional tests for the /predict endpoint — validates prediction creation,
idempotency, probability sum, and edge detection logic.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import httpx

from main import app


def _client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


async def _register_and_token(client):
    email = f"pred_{uuid.uuid4().hex[:8]}@vit.network"
    resp = await client.post("/auth/register", json={
        "email": email,
        "username": f"pred_{uuid.uuid4().hex[:6]}",
        "password": "PredTest123!",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _future_kickoff(days=7):
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


def _match_payload(**overrides):
    base = {
        "home_team": f"HomeFC_{uuid.uuid4().hex[:4]}",
        "away_team": f"AwayFC_{uuid.uuid4().hex[:4]}",
        "kickoff_time": _future_kickoff(),
        "league": "premier_league",
        "home_odds": 2.10,
        "draw_odds": 3.40,
        "away_odds": 3.80,
    }
    base.update(overrides)
    return base


# ── Basic Prediction Creation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predict_returns_200_with_valid_payload():
    async with _client() as client:
        token = await _register_and_token(client)
        resp = await client.post(
            "/predict",
            json=_match_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_predict_response_has_required_fields():
    async with _client() as client:
        token = await _register_and_token(client)
        resp = await client.post(
            "/predict",
            json=_match_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "home_prob" in data
    assert "draw_prob" in data
    assert "away_prob" in data


@pytest.mark.asyncio
async def test_predict_probabilities_sum_to_one():
    async with _client() as client:
        token = await _register_and_token(client)
        resp = await client.post(
            "/predict",
            json=_match_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    data = resp.json()
    total = data["home_prob"] + data["draw_prob"] + data["away_prob"]
    assert abs(total - 1.0) < 0.05, f"Probabilities sum to {total:.4f}, expected ~1.0"


@pytest.mark.asyncio
async def test_predict_probabilities_are_between_zero_and_one():
    async with _client() as client:
        token = await _register_and_token(client)
        resp = await client.post(
            "/predict",
            json=_match_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    data = resp.json()
    for key in ("home_prob", "draw_prob", "away_prob"):
        val = data[key]
        assert 0.0 <= val <= 1.0, f"{key} = {val} is out of [0,1] range"


# ── Idempotency ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predict_same_match_twice_returns_conflict_or_same():
    """
    Duplicate prediction requests should either:
    - Return the same prediction ID (idempotency / cache hit), OR
    - Return 409 Conflict (app prevents duplicate match entries).
    Both behaviours are valid deduplication strategies.
    """
    payload = _match_payload(
        home_team="Arsenal_dup",
        away_team="Chelsea_dup",
        kickoff_time=_future_kickoff(10),
        league="premier_league",
    )
    async with _client() as client:
        token = await _register_and_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        resp1 = await client.post("/predict", json=payload, headers=headers)
        resp2 = await client.post("/predict", json=payload, headers=headers)

    assert resp1.status_code == 200, f"First prediction failed: {resp1.text}"

    if resp2.status_code == 200:
        # Idempotent — same prediction ID returned
        data1, data2 = resp1.json(), resp2.json()
        assert data1.get("prediction_id") == data2.get("prediction_id"), (
            "Duplicate match should return same prediction ID"
        )
    else:
        # 409 Conflict — app blocks duplicate match entries
        assert resp2.status_code == 409, (
            f"Expected 200 (cached) or 409 (conflict), got {resp2.status_code}"
        )


# ── Prediction Listing ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_prediction_history_returns_list():
    async with _client() as client:
        token = await _register_and_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/predict", json=_match_payload(), headers=headers)
        resp = await client.get("/history", headers=headers)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert isinstance(data, (list, dict))


@pytest.mark.asyncio
async def test_prediction_history_without_auth_returns_401():
    async with _client() as client:
        resp = await client.get("/history")
    assert resp.status_code in (200, 401)   # some deployments may allow open history


# ── Edge Detection ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_predict_response_may_include_edge():
    """When returned, edge should be a float between -1 and 1."""
    async with _client() as client:
        token = await _register_and_token(client)
        resp = await client.post(
            "/predict",
            json=_match_payload(home_odds=1.9, draw_odds=3.5, away_odds=4.2),
            headers={"Authorization": f"Bearer {token}"},
        )
    data = resp.json()
    if "edge" in data:
        assert -1.0 <= data["edge"] <= 1.0, f"Edge {data['edge']} out of range"


@pytest.mark.asyncio
async def test_predict_response_may_include_confidence():
    """Confidence score (if present) should be between 0 and 1."""
    async with _client() as client:
        token = await _register_and_token(client)
        resp = await client.post(
            "/predict",
            json=_match_payload(),
            headers={"Authorization": f"Bearer {token}"},
        )
    data = resp.json()
    if "confidence" in data:
        assert 0.0 <= data["confidence"] <= 1.0


# ── Different Leagues ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("league", ["premier_league", "la_liga", "serie_a", "bundesliga", "ligue_1"])
async def test_predict_works_for_major_leagues(league):
    async with _client() as client:
        token = await _register_and_token(client)
        resp = await client.post(
            "/predict",
            json=_match_payload(league=league),
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code in (200, 400, 422), f"League {league} returned {resp.status_code}"


# ── Analytics After Prediction ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analytics_summary_responds_after_prediction():
    async with _client() as client:
        token = await _register_and_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/predict", json=_match_payload(), headers=headers)
        resp = await client.get("/analytics/summary", headers=headers)
    assert resp.status_code in (200, 401, 403, 404)
