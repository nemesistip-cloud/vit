"""
Regression tests for prediction compatibility and match listing behavior.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.core.cache import cache
from app.core.cache_keys import FIXTURE_LIST
from app.db import database as db_module
from app.db.models import Match
import app.services.sportsdb_api as sportsdb_api


def _future_kickoff(days=3):
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")


def _match_payload(**overrides):
    base = {
        "home_team": f"HomeFC_{datetime.now(timezone.utc).timestamp():.0f}",
        "away_team": f"AwayFC_{datetime.now(timezone.utc).timestamp():.0f}",
        "kickoff_time": _future_kickoff(),
        "league": "premier_league",
        "market_odds": {"home": 2.10, "draw": 3.40, "away": 3.80},
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_prediction_history_and_accuracy_endpoints(client, auth_headers):
    headers = auth_headers
    predict_resp = await client.post("/api/predict", json=_match_payload(), headers=headers)
    assert predict_resp.status_code == 200, predict_resp.text

    history_resp = await client.get("/api/history", headers=headers)
    assert history_resp.status_code == 200, history_resp.text
    history_data = history_resp.json()
    assert isinstance(history_data, list)
    assert any(item.get("match_id") == predict_resp.json().get("match_id") for item in history_data)

    accuracy_resp = await client.get("/api/accuracy", headers=headers)
    assert accuracy_resp.status_code == 200, accuracy_resp.text
    accuracy_data = accuracy_resp.json()
    assert accuracy_data["total"] >= 1
    assert accuracy_data["win_rate"] == 0.0
    assert accuracy_data["current_streak"] == 0


@pytest.mark.asyncio
async def test_predictions_match_endpoint_requires_auth(client):
    resp = await client.get("/api/predictions/match/1")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_match_endpoint_returns_prediction(client, auth_headers):
    headers = auth_headers
    predict_resp = await client.post("/api/predict", json=_match_payload(home_team="CompatHome", away_team="CompatAway"), headers=headers)
    assert predict_resp.status_code == 200, predict_resp.text
    match_id = predict_resp.json().get("match_id")
    assert match_id is not None

    resp = await client.get(f"/api/predictions/match/{match_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["match_id"] == match_id
    assert isinstance(data.get("predictions"), list)
    assert "confidence" in data
    assert "consensus" in data


@pytest.mark.asyncio
async def test_matches_auto_sync_fallback(client, monkeypatch):
    # Ensure cache does not return stale fixture list data.
    await cache.delete(f"{FIXTURE_LIST}:None:None")

    async def fake_sync_upcoming_fixtures(db, days_ahead: int = 7):
        match = Match(
            home_team="FallbackFC",
            away_team="SyncFC",
            league="premier_league",
            kickoff_time=datetime.now(timezone.utc) + timedelta(days=1),
            source="test",
        )
        db.add(match)
        await db.commit()
        return {"inserted": 1, "updated": 0, "skipped": 0, "total_fetched": 1}

    monkeypatch.setattr("app.api.routes.matches.AsyncSessionLocal", db_module.AsyncSessionLocal)
    monkeypatch.setattr(sportsdb_api, "sync_upcoming_fixtures", fake_sync_upcoming_fixtures)

    resp = await client.get("/api/matches")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert isinstance(payload, list)
    assert any(item.get("home_team") == "FallbackFC" and item.get("away_team") == "SyncFC" for item in payload)
