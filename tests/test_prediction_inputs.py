from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from app.services.evidence_engine import EvidenceEngine, PredictionClassification
from app.services.live_match_ingestion import _database_utc_now
from app.services.odds_api import OddsAPIClient
from app.services.odds_provider import NormalizedOdds, OddsIntelligence
from app.services import predict_features
from app.api.routes import matches as matches_route


def test_database_timestamp_is_utc_naive_for_postgres():
    aware = datetime(2026, 9, 15, 21, 40, tzinfo=timezone.utc)

    normalized = _database_utc_now(aware)

    assert normalized.tzinfo is None
    assert normalized == datetime(2026, 9, 15, 21, 40)


def test_static_history_loader_reads_raw_bundesliga_results(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "D1.csv").write_text(
        "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG\n"
        "D1,05/09/2026,Leverkusen,Mainz,2,0\n"
        "D1,12/09/2026,Bayern Munich,Leverkusen,1,1\n"
        "D1,19/09/2026,Leverkusen,Dortmund,3,2\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(predict_features, "_sports_history_dir", lambda: tmp_path / "sports")
    monkeypatch.setattr(predict_features, "_raw_history_dir", lambda: raw_dir)
    predict_features._static_history_rows.cache_clear()

    try:
        rows = predict_features._static_history_for_team(
            "Bayer 04 Leverkusen",
            limit=5,
            before=datetime(2026, 10, 1, tzinfo=timezone.utc),
            sport="football",
        )
    finally:
        predict_features._static_history_rows.cache_clear()

    assert len(rows) == 3
    assert all(row.league == "bundesliga" for row in rows)
    assert all(row.sport == "football" for row in rows)
    assert not predict_features._match_team_name("Bayer 04 Leverkusen", "Bayern Munich")
    assert not predict_features._match_team_name("West Ham United FC", "Birmingham City FC")
    assert "Bayer" not in predict_features._team_search_terms("Bayer 04 Leverkusen")
    assert "Ham" not in predict_features._team_search_terms("West Ham United FC")


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


@pytest.mark.asyncio
async def test_odds_api_uses_recent_cache_on_rate_limit_but_rejects_older_cache():
    client = OddsAPIClient("test-key", cache_ttl=90, enable_cache=True)
    now = datetime.now()
    quote_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    kickoff_time = datetime.now(timezone.utc) + timedelta(hours=2)
    cached_events = [{
        "id": "event",
        "home_team": "Toronto Raptors",
        "away_team": "Miami Heat",
        "last_update": quote_time.isoformat(),
        "commence_time": kickoff_time.isoformat(),
        "bookmakers": [{
            "key": "test_book",
            "markets": [{
                "key": "h2h",
                "outcomes": [
                    {"name": "Toronto Raptors", "price": 1.9},
                    {"name": "Miami Heat", "price": 2.0},
                ],
            }],
        }],
    }]

    async def rate_limited(*args, **kwargs):
        request = httpx.Request("GET", "https://example.test/odds")
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    client._request = rate_limited
    cache_key = client._get_cache_key("basketball_nba", "eu,uk", client.FETCH_MARKETS)
    try:
        client._cache[cache_key] = (cached_events, now - timedelta(seconds=120))
        result = await client.get_bookmaker_odds_for_competition("nba")
        assert len(result) == 1
        assert result[0].stale_cache is True
        assert result[0].timestamp == quote_time
        assert result[0].event_time == kickoff_time

        client._cache[cache_key] = (cached_events, now - timedelta(seconds=301))
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_odds("basketball_nba")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_prediction_odds_refresh_accepts_cached_two_way_basketball(monkeypatch):
    now = datetime.now(timezone.utc)

    class FakeOddsClient:
        async def get_bookmaker_odds_for_competition(self, league, **kwargs):
            assert league == "nba"
            return [SimpleNamespace(
                match_id="provider-event",
                home_team="Toronto Raptors",
                away_team="Miami Heat",
                home_odds=1.9,
                draw_odds=0.0,
                away_odds=2.0,
                bookmaker="test_book",
                timestamp=now - timedelta(seconds=120),
                stale_cache=True,
            )]

    monkeypatch.setattr(
        matches_route,
        "get_data_loader",
        lambda: SimpleNamespace(odds_client=FakeOddsClient()),
    )
    match = SimpleNamespace(
        id=1,
        external_id="sportsdb-event",
        home_team="Toronto Raptors",
        away_team="Miami Heat",
        kickoff_time=now + timedelta(hours=2),
        league="nba",
        sport="basketball",
        status="upcoming",
    )

    odds = await matches_route._refresh_prediction_odds(match, now)

    assert {item.selection for item in odds} == {"home", "away"}
    assert all(item.provider == "the_odds_api_stale_cache" for item in odds)


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