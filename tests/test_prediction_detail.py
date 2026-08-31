"""
tests/test_prediction_detail.py — Unit & Integration tests for canonical prediction detail endpoint (A.4).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from app.db.database import AsyncSessionLocal
from app.db.models import Match, Prediction
from app.modules.evidence.service import create_evidence_snapshot
from app.api.routes.prediction_detail import router as prediction_detail_router
from fastapi import FastAPI


@pytest_asyncio.fixture
async def app_with_route():
    test_app = FastAPI()
    test_app.include_router(prediction_detail_router)
    return test_app


@pytest_asyncio.fixture
async def async_client(app_with_route):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_route),
        base_url="http://testserver"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_prediction_detail_not_initialized_nonexistent_match(async_client: AsyncClient):
    """Test response when match does not exist in database."""
    response = await async_client.get("/api/matches/999999/prediction-detail")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == 999999
    assert data["status"] == "not_initialized"
    assert "not found" in data["unavailable_reason"].lower()
    assert data["evidence"] is None


@pytest.mark.asyncio
async def test_prediction_detail_not_initialized_match_without_prediction(async_client: AsyncClient):
    """Test response when match exists but has no prediction."""
    async with AsyncSessionLocal() as session:
        match = Match(
            home_team="Arsenal",
            away_team="Chelsea",
            league="premier_league",
            kickoff_time=datetime.now(timezone.utc),
            opening_odds_home=2.1,
            opening_odds_draw=3.4,
            opening_odds_away=3.2,
            status="scheduled",
        )
        session.add(match)
        await session.commit()
        await session.refresh(match)
        match_id = match.id

    response = await async_client.get(f"/api/matches/{match_id}/prediction-detail")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == match_id
    assert data["status"] == "not_initialized"
    assert "No prediction exists yet" in data["unavailable_reason"]
    assert data["model"]["reason_if_null"] is not None
    assert data["market_intelligence"]["home_odds"] == 2.1


@pytest.mark.asyncio
async def test_prediction_detail_full_verified(async_client: AsyncClient):
    """Test response when match, prediction, and evidence snapshot exist and all validation rules pass."""
    async with AsyncSessionLocal() as session:
        # Create match
        match = Match(
            home_team="Real Madrid",
            away_team="Barcelona",
            league="la_liga",
            kickoff_time=datetime.now(timezone.utc),
            opening_odds_home=1.95,
            opening_odds_draw=3.6,
            opening_odds_away=3.8,
            status="scheduled",
        )
        session.add(match)
        await session.commit()
        await session.refresh(match)
        match_id = match.id

        # Create prediction
        pred = Prediction(
            match_id=match_id,
            user_id=1,
            bet_side="home",
            home_prob=0.55,
            draw_prob=0.25,
            away_prob=0.20,
            consensus_prob=0.55,
            confidence=0.82,
            final_ev=0.0725,
            entry_odds=1.95,
            recommended_stake=0.05,
            timestamp=datetime.now(timezone.utc),
        )
        session.add(pred)
        await session.commit()

        # Create evidence snapshot with requirements evaluated
        await create_evidence_snapshot(
            db=session,
            match_id=match_id,
            feature_completeness_pct=85,
            provider_data={
                "features": {
                    "home_team": "Real Madrid",
                    "away_team": "Barcelona",
                    "league": "la_liga",
                    "kickoff_time": "2026-09-01T20:00:00Z",
                    "goal_stats": {"home_avg": 2.1, "away_avg": 1.8},
                    "btts_history": {"home_btts_pct": 0.6, "away_btts_pct": 0.7},
                },
                "market_odds": {"home": 1.95, "draw": 3.6, "away": 3.8},
            },
            market_keys_to_evaluate=["1x2", "over_under_2_5", "btts"],
        )

    response = await async_client.get(f"/api/matches/{match_id}/prediction-detail")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == match_id
    assert data["status"] == "verified"
    assert data["unavailable_reason"] is None
    assert data["evidence"]["quality_score"] > 0
    assert data["model"]["home_prob"] == 0.55
    assert data["markets"]["1x2"]["requirements_met"] is True
    assert data["validation"]["all_passed"] is True
    assert data["validation"]["attestation_hash"].startswith("vit:")
