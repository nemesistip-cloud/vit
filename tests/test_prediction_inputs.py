from datetime import datetime, timezone

import pytest

from app.services.evidence_engine import EvidenceEngine, PredictionClassification
from app.services.live_match_ingestion import _database_utc_now
from app.services.odds_api import OddsAPIClient
from app.services.odds_provider import NormalizedOdds, OddsIntelligence


def test_database_timestamp_is_utc_naive_for_postgres():
    aware = datetime(2026, 9, 15, 21, 40, tzinfo=timezone.utc)

    normalized = _database_utc_now(aware)

    assert normalized.tzinfo is None
    assert normalized == datetime(2026, 9, 15, 21, 40)


@pytest.mark.asyncio
async def test_live_odds_feed_does_not_apply_future_only_date_filter():
    client = OddsAPIClient("test-key", enable_cache=False)
    captured = {}

    async def fake_get_odds(**kwargs):
        captured.update(kwargs)
        return []

    client.get_odds = fake_get_odds
    try:
        await client.get_odds_for_competition(
            "la_liga",
            days_ahead=2,
            include_live=True,
        )
    finally:
        await client.close()

    assert captured["date_from"] is None
    assert captured["date_to"] is not None
    assert captured["sport"] == "soccer_spain_la_liga"


def test_partial_real_form_can_produce_limited_evidence_with_live_odds():
    now = datetime.now(timezone.utc)
    odds = [
        NormalizedOdds("fixture", "football", "match_winner", "home", 2.1, "bookmaker", now, "odds_api"),
        NormalizedOdds("fixture", "football", "match_winner", "draw", 3.3, "bookmaker", now, "odds_api"),
        NormalizedOdds("fixture", "football", "match_winner", "away", 3.6, "bookmaker", now, "odds_api"),
    ]
    reconciled = OddsIntelligence.reconcile(odds, sport="football", market="match_winner")

    evidence = EvidenceEngine.evaluate(
        match_source="footballdata",
        match_features={"feature_completeness": 0.511},
        reconciled_odds=reconciled,
        recent_form_data={
            "home": {"matches_played": 1},
            "away": {"matches_played": 2},
        },
        model_agreement_pct=0.0,
        market="match_winner",
    )

    assert evidence.is_sufficient is True
    assert evidence.classification is PredictionClassification.LIMITED
    assert evidence.recent_form == 5.0
    assert "Full recent form history for both teams" in evidence.missing_elements