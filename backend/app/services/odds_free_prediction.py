"""Production data adapter for the odds-independent football model."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match
from app.services.predict_features import _static_history_rows
from services.ml_service.odds_free_model import (
    FEATURE_VERSION,
    MAX_MODEL_SEASONS,
    MODEL_VERSION,
    HistoricalResult,
    fit_dixon_coles,
    load_platt_calibrators,
    predict_score_distribution,
)

MIN_HISTORY_MATCHES = 760
MIN_HISTORY_SEASONS = 2
TRUSTED_RESULT_SOURCES = {
    "football-data-uk",
    "football-data.org",
    "footballdata",
    "github-premier-league-data",
    "sportsdb",
    "sportmonks",
    "api_football",
    "user_csv",
}


def _key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@lru_cache(maxsize=8)
def _fit_cached(results: tuple[HistoricalResult, ...]):
    return fit_dixon_coles(results)


def _load_calibration_for_cutoff(kickoff_time: datetime) -> tuple[dict, dict | None]:
    """Calibration artifacts are intentionally disabled unless the promotion gate is passed.

    This keeps the verified raw Dixon-Coles model as the active production path until a
    candidate artifact demonstrates an actual improvement on the same chronological fixtures.
    """
    return {}, None


async def load_historical_results(
    db: AsyncSession | None,
    league: str,
    before: datetime,
) -> tuple[HistoricalResult, ...]:
    """Combine trusted, settled DB and checked-in CSV results strictly pre-kickoff.

    The database query is intentionally narrowed to the requested league and a recent
    historical window. A full-table scan on production football data causes each
    prediction request to stall long enough for Render health checks and downstream
    502s to trigger.
    """
    cutoff = _utc(before)
    cutoff_naive = cutoff.replace(tzinfo=None)
    history_start = cutoff_naive - timedelta(days=366 * (MAX_MODEL_SEASONS + 2))
    league_key = _key(league)
    deduped: dict[tuple[str, str, str], HistoricalResult] = {}

    if db is not None:
        stmt = select(
            Match.home_team,
            Match.away_team,
            Match.kickoff_time,
            Match.home_goals,
            Match.away_goals,
            Match.league,
            Match.source,
            Match.statistics,
            Match.closing_odds_home,
            Match.closing_odds_draw,
            Match.closing_odds_away,
        ).where(
            Match.sport == "football",
            Match.home_goals.is_not(None),
            Match.away_goals.is_not(None),
            Match.kickoff_time >= history_start,
            Match.kickoff_time < cutoff_naive,
        )
        if league and league.strip():
            stmt = stmt.where(Match.league == league)
        result = await db.execute(stmt)
        for home, away, kickoff, hg, ag, row_league, source, statistics, close_home, close_draw, close_away in result.all():
            if (
                not home or not away or not kickoff or _key(row_league) != league_key
                or str(source or "").casefold() not in TRUSTED_RESULT_SOURCES
            ):
                continue
            date = _utc(kickoff)
            if date >= cutoff:
                continue
            stats = statistics if isinstance(statistics, dict) else {}
            item = HistoricalResult(
                date, home, away, int(hg), int(ag),
                _finite_nonnegative(stats.get("home_xg")),
                _finite_nonnegative(stats.get("away_xg")),
                _finite_nonnegative_price(close_home),
                _finite_nonnegative_price(close_draw),
                _finite_nonnegative_price(close_away),
            )
            deduped[(date.date().isoformat(), _key(home), _key(away))] = item

    for row in _static_history_rows():
        if (
            _key(getattr(row, "league", None)) != league_key
            or str(getattr(row, "source", "")).casefold() not in TRUSTED_RESULT_SOURCES
        ):
            continue
        date = _utc(row.kickoff_time)
        # Public CSV dates have no kickoff time; exclude the whole date to
        # prevent results from later on that date leaking into the feature set.
        if date.date() >= cutoff.date():
            continue
        item = HistoricalResult(
            date, row.home_team, row.away_team, row.home_goals, row.away_goals,
            _finite_nonnegative(getattr(row, "home_xg", None)),
            _finite_nonnegative(getattr(row, "away_xg", None)),
            _finite_nonnegative_price(getattr(row, "closing_odds_home", None)),
            _finite_nonnegative_price(getattr(row, "closing_odds_draw", None)),
            _finite_nonnegative_price(getattr(row, "closing_odds_away", None)),
        )
        deduped.setdefault((date.date().isoformat(), _key(item.home_team), _key(item.away_team)), item)

    return tuple(sorted(deduped.values(), key=lambda row: row.date))


def _season_id(date: datetime) -> int:
    return date.year if date.month >= 7 else date.year - 1


def _finite_nonnegative(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _finite_nonnegative_price(value: Any) -> float | None:
    number = _finite_nonnegative(value)
    return number if number is not None and number > 1.0 else None


def _schedule_features(results: tuple[HistoricalResult, ...], home: str, away: str, kickoff: datetime) -> dict[str, Any]:
    cutoff = _utc(kickoff)
    features = {}
    for side, team in (("home", _key(home)), ("away", _key(away))):
        played = [
            row for row in results
            if team in {_key(row.home_team), _key(row.away_team)}
        ]
        last_played = max((_utc(row.date) for row in played), default=None)
        features[f"{side}_rest_days"] = (cutoff - last_played).total_seconds() / 86400 if last_played else None
        features[f"{side}_matches_previous_14_days"] = sum(
            0 <= (cutoff - _utc(row.date)).total_seconds() < 14 * 86400 for row in played
        )
        xg_for, xg_against = [], []
        for row in played:
            if row.home_xg is None or row.away_xg is None:
                continue
            if team == _key(row.home_team):
                xg_for.append(row.home_xg)
                xg_against.append(row.away_xg)
            else:
                xg_for.append(row.away_xg)
                xg_against.append(row.home_xg)
        features[f"{side}_xg_per_match"] = sum(xg_for) / len(xg_for) if xg_for else None
        features[f"{side}_xga_per_match"] = sum(xg_against) / len(xg_against) if xg_against else None
        features[f"{side}_xg_sample_size"] = len(xg_for)
    return features


async def predict_odds_free(
    db: AsyncSession | None,
    home_team: str,
    away_team: str,
    league: str,
    kickoff_time: datetime,
) -> dict[str, Any]:
    """Fit the statistical baseline and derive markets without accepting odds."""
    results = await load_historical_results(db, league, kickoff_time)
    if results:
        latest_season = max(_season_id(row.date) for row in results)
        first_model_season = latest_season - MAX_MODEL_SEASONS + 1
        results = tuple(row for row in results if _season_id(row.date) >= first_model_season)
    seasons = {_season_id(row.date) for row in results}
    if len(results) < MIN_HISTORY_MATCHES or len(seasons) < MIN_HISTORY_SEASONS:
        return {
            "status": "unavailable",
            "reasons": [
                f"Trusted pre-kickoff {league} results are insufficient: "
                f"{len(results)} matches over {len(seasons)} seasons; "
                f"need at least {MIN_HISTORY_MATCHES} matches across {MIN_HISTORY_SEASONS} seasons."
            ],
            "source": "odds_free_dixon_coles",
        }

    fitted = _fit_cached(results)
    calibrators, calibration_artifact = _load_calibration_for_cutoff(kickoff_time)
    prediction = predict_score_distribution(fitted, home_team, away_team, calibration={})
    outcome_probs = (
        prediction["home_prob"], prediction["draw_prob"], prediction["away_prob"]
    )
    entropy = -sum(prob * math.log(prob) for prob in outcome_probs if prob > 0)
    entropy_confidence = max(0.0, min(1.0, 1.0 - entropy / math.log(3)))
    providers = sorted({
        str(getattr(row, "source", "football-data-uk"))
        for row in _static_history_rows()
        if _key(getattr(row, "league", None)) == _key(league)
        and _utc(row.kickoff_time) < _utc(kickoff_time)
    })
    prediction.update({
        "status": "ready",
        "data_source": "odds_free_dixon_coles",
        "model_version": MODEL_VERSION,
        "dataset_version": fitted.dataset_version,
        "feature_version": FEATURE_VERSION,
        "calibration_version": None,
        "calibration_applied": False,
        "training_matches": fitted.training_matches,
        "training_seasons": len(seasons),
        "training_cutoff": _utc(kickoff_time).isoformat(),
        "rho": fitted.rho,
        "home_advantage_log_rate": fitted.home_advantage,
        "evidence_providers": providers,
        "schedule_features": _schedule_features(results, home_team, away_team, kickoff_time),
        "models_used": 1,
        "models_total": 1,
    })
    prediction["individual_results"] = [{
        "model_name": "Dixon-Coles",
        "model_type": "statistical",
        "model_weight": 1.0,
        "supported_markets": ["1x2", "over_under", "btts", "correct_score"],
        "home_prob": prediction["home_prob"],
        "draw_prob": prediction["draw_prob"],
        "away_prob": prediction["away_prob"],
        "over_2_5_prob": prediction["over_25_prob"],
        "btts_prob": prediction["btts_prob"],
        "home_goals_expectation": prediction["home_goals_expectation"],
        "away_goals_expectation": prediction["away_goals_expectation"],
        "confidence": {"1x2": entropy_confidence},
        "failed": False,
        "source": "fitted_historical_results",
        "calibration": {
            "applied": False,
            "method": None,
            "training_samples": 0,
        },
    }]
    return {"status": "ready", "predictions": prediction, "individual_results": prediction["individual_results"]}