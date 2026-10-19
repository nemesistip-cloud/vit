from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest


class FakeResult:
    def __init__(self, rows=None, scalar=None):
        self.rows = rows or []
        self.scalar = scalar

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.scalar


class FakeSession:
    def __init__(self, matches_by_external_id):
        self.matches_by_external_id = matches_by_external_id
        self.added = []
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def execute(self, statement):
        sql = str(statement)
        if "WHERE matches.source =" in sql:
            return FakeResult()
        if "WHERE matches.external_id =" in sql:
            external_id = statement.compile().params["external_id_1"]
            return FakeResult(scalar=self.matches_by_external_id.get(external_id))
        return FakeResult()

    def add(self, match):
        self.added.append(match)

    async def commit(self):
        self.commits += 1

    async def flush(self):
        return None


class FakeSessionFactory:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session


def sportsdb_event(external_id, sport):
    return {
        "external_id": external_id,
        "home_team": f"{sport.title()} Home",
        "away_team": f"{sport.title()} Away",
        "league": f"{sport.title()} League",
        "kickoff_time": datetime.now(timezone.utc) + timedelta(days=1),
        "status": "upcoming",
        "sport": sport,
    }


@pytest.mark.asyncio
async def test_fixture_gap_import_preserves_sport_and_repairs_provider_rows(monkeypatch):
    from app.agents.fixture_gap_agent import FixtureGapAgent
    from app.data import match_dedup
    from app.db import database
    from app.services import sportsdb_api

    existing_provider_match = SimpleNamespace(
        external_id="sportsdb-basketball-existing",
        source="sportsdb",
        sport="football",
        status="upcoming",
    )
    user_match = SimpleNamespace(
        external_id="user-baseball-existing",
        source="user_csv",
        sport="football",
        status="upcoming",
    )
    session = FakeSession({
        existing_provider_match.external_id: existing_provider_match,
        user_match.external_id: user_match,
    })
    events = [
        sportsdb_event("sportsdb-basketball-new", "basketball"),
        sportsdb_event(existing_provider_match.external_id, "basketball"),
        sportsdb_event(user_match.external_id, "baseball"),
    ]

    async def fetch_fixtures():
        return {"past": [], "upcoming": events}

    async def no_fingerprint_match(*_args, **_kwargs):
        return None

    monkeypatch.setattr(sportsdb_api, "fetch_all_real_fixtures", fetch_fixtures)
    monkeypatch.setattr(database, "AsyncSessionLocal", FakeSessionFactory(session))
    monkeypatch.setattr(match_dedup, "find_existing_match", no_fingerprint_match)

    inserted = await FixtureGapAgent()._import_real_fixtures()

    assert inserted == 1
    assert session.added[0].sport == "basketball"
    assert existing_provider_match.sport == "basketball"
    assert user_match.sport == "football"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_fixture_gap_import_commits_sport_correction_without_new_rows(monkeypatch):
    from app.agents.fixture_gap_agent import FixtureGapAgent
    from app.data import match_dedup
    from app.db import database
    from app.services import sportsdb_api

    existing = SimpleNamespace(
        external_id="sportsdb-tennis-existing",
        source="sportsdb",
        sport="football",
        status="upcoming",
    )
    session = FakeSession({existing.external_id: existing})

    async def fetch_fixtures():
        return {"past": [], "upcoming": [sportsdb_event(existing.external_id, "tennis")]}

    async def no_fingerprint_match(*_args, **_kwargs):
        return None

    monkeypatch.setattr(sportsdb_api, "fetch_all_real_fixtures", fetch_fixtures)
    monkeypatch.setattr(database, "AsyncSessionLocal", FakeSessionFactory(session))
    monkeypatch.setattr(match_dedup, "find_existing_match", no_fingerprint_match)

    inserted = await FixtureGapAgent()._import_real_fixtures()

    assert inserted == 0
    assert existing.sport == "tennis"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_manual_sportsdb_sync_commits_existing_sport_correction(monkeypatch):
    from app.services import sportsdb_api

    existing = SimpleNamespace(
        external_id="sportsdb-basketball-manual-sync",
        source="sportsdb",
        sport="football",
        kickoff_time=(datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None),
    )
    session = FakeSession({existing.external_id: existing})
    event = sportsdb_event(existing.external_id, "basketball")

    async def fetch_next_events():
        return [event]

    async def fetch_upcoming_range(**_kwargs):
        return []

    monkeypatch.setattr(sportsdb_api, "fetch_next_events", fetch_next_events)
    monkeypatch.setattr(sportsdb_api, "fetch_upcoming_range", fetch_upcoming_range)

    result = await sportsdb_api.sync_upcoming_fixtures(session, days_ahead=2)

    assert result["updated"] == 1
    assert existing.sport == "basketball"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_manual_sync_persists_odds_api_fixture_with_provider_sport(monkeypatch):
    from app.services import sportsdb_api

    event = sportsdb_event("oddsapi:nba-sync-event", "basketball")
    event["source"] = "the_odds_api"
    session = FakeSession({})

    async def no_sportsdb_events():
        return []

    async def no_date_range_events(**_kwargs):
        return []

    async def odds_api_events(**_kwargs):
        return [event], None

    monkeypatch.setattr(sportsdb_api, "fetch_next_events", no_sportsdb_events)
    monkeypatch.setattr(sportsdb_api, "fetch_upcoming_range", no_date_range_events)
    monkeypatch.setattr(sportsdb_api, "_fetch_odds_api_fixtures", odds_api_events)

    result = await sportsdb_api.sync_upcoming_fixtures(session, days_ahead=7)

    assert result["inserted"] == 1
    assert result["odds_api_fetched"] == 1
    assert session.added[0].sport == "basketball"
    assert session.added[0].source == "the_odds_api"
    assert session.added[0].external_id == "oddsapi:nba-sync-event"


@pytest.mark.asyncio
async def test_scheduled_fixture_sync_agent_runs_provider_sync(monkeypatch):
    from app.agents.coordinator import AgentCoordinator
    from app.agents.fixture_sync_agent import FixtureSyncAgent
    from app.db import database
    from app.services import sportsdb_api

    session = FakeSession({})

    async def sync_fixtures(_db, days_ahead):
        assert days_ahead == 60
        return {"inserted": 12, "updated": 3, "skipped": 0, "total_fetched": 15}

    monkeypatch.setattr(database, "AsyncSessionLocal", FakeSessionFactory(session))
    monkeypatch.setattr(sportsdb_api, "sync_upcoming_fixtures", sync_fixtures)

    result = await FixtureSyncAgent().run_cycle()

    assert result == {"status": "ok", "inserted": 12, "updated": 3, "skipped": 0, "total_fetched": 15}

    monkeypatch.delenv("ENABLED_AGENTS", raising=False)
    coordinator = object.__new__(AgentCoordinator)
    coordinator._agent_classes = {"fixture-sync": FixtureSyncAgent}
    assert "fixture-sync" in coordinator._get_enabled_agent_names()


@pytest.mark.asyncio
async def test_odds_api_fixture_fetch_uses_active_event_schedules_only(monkeypatch):
    from app.services import odds_api, sportsdb_api

    clients = []

    class FakeOddsAPIClient:
        def __init__(self, *_args, **_kwargs):
            self.event_requests = []
            clients.append(self)

        async def get_sports(self):
            return [
                {"key": "basketball_nba", "title": "NBA", "active": True},
                {"key": "soccer_epl", "title": "English Premier League", "active": False},
                {"key": "unknown_sport", "title": "Unknown", "active": True},
            ]

        async def get_events(self, sport_key, **kwargs):
            self.event_requests.append((sport_key, kwargs))
            return [
                {
                    "id": "nba-event-1",
                    "home_team": "Toronto Raptors",
                    "away_team": "Miami Heat",
                    "commence_time": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                },
                {
                    "id": "nba-event-past",
                    "home_team": "Past Home",
                    "away_team": "Past Away",
                    "commence_time": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                },
                {
                    "id": "nba-event-out-of-range",
                    "home_team": "Later Home",
                    "away_team": "Later Away",
                    "commence_time": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(),
                },
            ]

        async def close(self):
            return None

    monkeypatch.setenv("ODDS_API_KEY", "test-key")
    monkeypatch.setattr(odds_api, "OddsAPIClient", FakeOddsAPIClient)

    events, error = await sportsdb_api._fetch_odds_api_fixtures(days_ahead=7)

    assert error is None
    assert len(events) == 1
    assert events[0]["sport"] == "basketball"
    assert events[0]["source"] == "the_odds_api"
    assert events[0]["external_id"] == "oddsapi:nba-event-1"
    assert len(clients[0].event_requests) == 1
    sport_key, params = clients[0].event_requests[0]
    assert sport_key == "basketball_nba"
    assert params == {}


@pytest.mark.parametrize(
    ("sport_key", "expected"),
    [
        ("soccer_epl", "football"),
        ("basketball_nba", "basketball"),
        ("tennis_atp_french_open", "tennis"),
        ("americanfootball_nfl", "american_football"),
        ("baseball_mlb", "baseball"),
        ("icehockey_nhl", "ice_hockey"),
        ("mma_ufc", "mma"),
        ("boxing_super", "boxing"),
        ("rugbyleague_nrl", "rugby"),
    ],
)
def test_odds_api_fixture_sport_mapping_covers_supported_sports(sport_key, expected):
    from app.services.sportsdb_api import _odds_api_sport

    assert _odds_api_sport(sport_key) == expected


@pytest.mark.asyncio
async def test_odds_api_client_uses_event_only_endpoint_without_markets(monkeypatch):
    from app.services.odds_api import OddsAPIClient

    client = OddsAPIClient("test-key", enable_cache=False)
    requested = {}

    async def fake_request(endpoint, params):
        requested["endpoint"] = endpoint
        requested["params"] = params
        return [{"id": "event-1"}]

    monkeypatch.setattr(client, "_request", fake_request)

    events = await client.get_events("basketball_nba")
    await client.close()

    assert events == [{"id": "event-1"}]
    assert requested == {
        "endpoint": "/sports/basketball_nba/events",
        "params": {},
    }