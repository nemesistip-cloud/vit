from app.services.live_match_ingestion import (
    CanonicalLiveMatch,
    extract_live_score,
    reconcile_live_candidates,
)


def _live(home_score: int, away_score: int, provider: str = "isports") -> CanonicalLiveMatch:
    return CanonicalLiveMatch(
        id=f"live-{provider}",
        provider=provider,
        provider_match_id=f"{provider}-123",
        home="AC Milan",
        away="US Lecce",
        league="Serie A",
        status="LIVE",
        home_score=home_score,
        away_score=away_score,
        source_timestamp=1.0,
        ingestion_timestamp=1.0,
        last_successful_update=1.0,
    )


def test_current_score_is_preferred_over_half_time_score():
    assert extract_live_score({"currentScore": {"home": 2, "away": 0}, "halfTime": {"home": 1, "away": 0}}) == (2, 0)


def test_live_score_transition_does_not_regress():
    states = [
        reconcile_live_candidates([_live(0, 0)]),
        reconcile_live_candidates([_live(1, 0), _live(0, 0, "footballdata")]),
        reconcile_live_candidates([_live(1, 0, "isports"), _live(2, 0, "footballdata")]),
    ]

    assert [(state.home_score, state.away_score) for state in states] == [(0, 0), (1, 0), (2, 0)]


def test_provider_conflict_selects_latest_monotonic_score():
    selected = reconcile_live_candidates([_live(1, 0, "isports"), _live(2, 0, "footballdata")])

    assert selected.provider == "footballdata"
    assert (selected.home_score, selected.away_score) == (2, 0)