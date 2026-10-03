"""
Predict-time feature builder.

Given the participants in an upcoming match, query the DB for recent results
and produce the per-team rolling features the sklearn model heads expect.

Replaces the hardcoded global averages that previously lived inline in
`services/ml_service/models/model_orchestrator._sklearn_predict`.

Returns a dict that mirrors the feature_map in `_sklearn_predict` so it can
be merged in directly:

    home_form_pts_5/10, away_form_pts_5/10,
    home_gf_pg_5/10,    away_gf_pg_5/10,
    home_ga_pg_5/10,    away_ga_pg_5/10,
    h2h_home_win_pct, h2h_draw_pct, h2h_away_win_pct,
    h2h_home_goals_pg, h2h_away_goals_pg,
    home_adv_league,
    elo_diff,
    feature_completeness  ← 0..1, 1 = full real data, 0 = pure fallback

Designed to be cheap (≤4 small queries) so it can run on every /predict call.
"""

from __future__ import annotations

import csv
import logging
import math
import re
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

from sqlalchemy import select, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match

logger = logging.getLogger(__name__)

FEATURE_VERSION = "3.0.0"

# League-level home advantage estimates (goals). Empty = neutral default.
_LEAGUE_HOME_ADV: Dict[str, float] = {
    "premier_league":       0.42,
    "la_liga":              0.45,
    "bundesliga":           0.38,
    "serie_a":              0.40,
    "ligue_1":              0.35,
    "champions_league":     0.20,
    "europa_league":        0.18,
    "conference_league":    0.16,
    "eredivisie":           0.44,
    "primeira_liga":        0.48,
    "championship":         0.41,
    "scottish_premiership": 0.43,
    "belgian_pro_league":   0.42,
    "super_lig":            0.50,
    "ekstraklasa":          0.46,
    "mls":                  0.38,
    "liga_mx":              0.47,
    "brasileirao":          0.46,
    "argentine_primera":    0.49,
    "brazil_serie_a":       0.46,
    "argentina_liga_profesional": 0.49,
}
_DEFAULT_HOME_ADV = 0.40
_TEAM_NAME_IGNORED_TOKENS = {"fc", "afc", "cf", "club", "the", "sc", "ac", "as", "fsv"}

# Neutral fallbacks used only when there's no historical data at all.
_FALLBACK_FEATURES: Dict[str, float] = {
    "home_form_pts_5":   1.30, "away_form_pts_5":   1.20,
    "home_form_pts_10":  1.30, "away_form_pts_10":  1.20,
    "home_gf_pg_5":      1.45, "away_gf_pg_5":      1.20,
    "home_ga_pg_5":      1.20, "away_ga_pg_5":      1.45,
    "home_gf_pg_10":     1.45, "away_gf_pg_10":     1.20,
    "home_ga_pg_10":     1.20, "away_ga_pg_10":     1.45,
    "h2h_home_win_pct":  0.45, "h2h_draw_pct":      0.27,
    "h2h_away_win_pct":  0.28,
    "h2h_home_goals_pg": 1.45, "h2h_away_goals_pg": 1.20,
    "home_adv_league":   _DEFAULT_HOME_ADV,
    "elo_diff":          0.0,
    "feature_completeness": 0.0,
}


def _normalise_team_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _normalise_league_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _match_team_name(team: str, candidate: str) -> bool:
    if not team or not candidate:
        return False
    other = _normalise_team_name(candidate)
    if not other:
        return False
    for term in _team_search_terms(team):
        normalized_term = _normalise_team_name(term)
        if not normalized_term:
            continue
        if normalized_term == other:
            return True
        term_tokens = {
            token for token in re.findall(r"[a-z0-9]+", term.lower())
            if token not in _TEAM_NAME_IGNORED_TOKENS and not token.isdigit()
        }
        other_tokens = {
            token for token in re.findall(r"[a-z0-9]+", candidate.lower())
            if token not in _TEAM_NAME_IGNORED_TOKENS and not token.isdigit()
        }
        if len(term_tokens) >= 2 and term_tokens.issubset(other_tokens):
            return True
        if len(other_tokens) >= 2 and other_tokens.issubset(term_tokens):
            return True
    return False


def _sports_history_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "sports"


def _raw_history_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "raw"


_RAW_LEAGUES = {
    "E0": "premier_league",
    "E1": "championship",
    "D1": "bundesliga",
    "SP1": "la_liga",
    "I1": "serie_a",
    "F1": "ligue_1",
    "N1": "eredivisie",
    "P1": "primeira_liga",
}


def _parse_date(value: Optional[str], day_first: bool = False) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        day_first_formats = ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y")
        month_first_formats = ("%m/%d/%Y", "%d/%m/%Y", "%d/%m/%y")
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", *(day_first_formats if day_first else month_first_formats)):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
    return None


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _latest_match_date(matches: List[Any]) -> Optional[str]:
    dates = [
        date
        for date in (_as_utc(getattr(match, "kickoff_time", None)) for match in matches)
        if date is not None
    ]
    return max(dates).isoformat() if dates else None


def _merge_match_history(primary: List[Any], supplement: List[Any], limit: int) -> List[Any]:
    """Merge provider history without double-counting the same dated result."""
    merged: List[Any] = []
    seen = set()

    for match in primary + supplement:
        kickoff = _as_utc(getattr(match, "kickoff_time", None))
        if kickoff is None:
            key = None
        else:
            def canonical_team_name(value: Any) -> str:
                tokens = re.findall(r"[a-z0-9]+", str(value or "").lower())
                return "".join(token for token in tokens if token not in _TEAM_NAME_IGNORED_TOKENS)

            teams = sorted((
                canonical_team_name(getattr(match, "home_team", "")),
                canonical_team_name(getattr(match, "away_team", "")),
            ))
            key = (
                kickoff.isoformat(),
                teams[0],
                teams[1],
                getattr(match, "home_goals", None),
                getattr(match, "away_goals", None),
            )
        if key is not None and key in seen:
            continue
        if key is not None:
            seen.add(key)
        merged.append(match)

    merged.sort(
        key=lambda match: _as_utc(getattr(match, "kickoff_time", None))
        or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return merged[:limit]


def get_fresh_football_form(match_features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate recent trusted football form and derive bounded model inputs."""
    trusted_sources = {
        "footballdata", "football-data.org", "football-data-uk",
        "github-premier-league-data", "sportsdb", "isports",
        "sportmonks", "api_football", "provider", "user_csv",
        "odds_api", "the_odds_api",
    }
    providers = set(match_features.get("evidence_providers") or [])
    if not providers or not providers <= trusted_sources:
        return None

    try:
        completeness = float(match_features.get("feature_completeness", 0.0))
        home_count = int(match_features.get("home_history_sample_size", 0))
        away_count = int(match_features.get("away_history_sample_size", 0))
        dates = [
            datetime.fromisoformat(str(match_features[key]).replace("Z", "+00:00"))
            for key in ("home_history_latest", "away_history_latest")
        ]
        values = {
            key: float(match_features[key])
            for key in (
                "home_form_pts_10", "away_form_pts_10",
                "home_gf_pg_10", "away_gf_pg_10",
                "home_ga_pg_10", "away_ga_pg_10",
            )
        }
        home_advantage = float(match_features.get("home_adv_league", 0.0) or 0.0)
    except (KeyError, TypeError, ValueError):
        return None

    if dates[0].tzinfo is None:
        dates[0] = dates[0].replace(tzinfo=timezone.utc)
    if dates[1].tzinfo is None:
        dates[1] = dates[1].replace(tzinfo=timezone.utc)
    ages = [
        (datetime.now(timezone.utc) - date.astimezone(timezone.utc)).total_seconds() / 86400
        for date in dates
    ]
    if (
        not math.isfinite(completeness)
        or completeness < 0.55
        or home_count < 3
        or away_count < 3
        or any(age < 0 or age > 540 for age in ages)
        or any(not math.isfinite(value) for value in values.values())
        or not 0.0 <= values["home_form_pts_10"] <= 3.0
        or not 0.0 <= values["away_form_pts_10"] <= 3.0
        or any(not 0.0 <= values[key] <= 10.0 for key in (
            "home_gf_pg_10", "away_gf_pg_10", "home_ga_pg_10", "away_ga_pg_10"
        ))
        or not math.isfinite(home_advantage)
    ):
        return None

    goal_difference_edge = (
        values["home_gf_pg_10"] - values["home_ga_pg_10"]
        - values["away_gf_pg_10"] + values["away_ga_pg_10"]
    )
    form_shift = max(
        -0.25,
        min(
            0.25,
            0.16 * ((values["home_form_pts_10"] - values["away_form_pts_10"]) / 3.0)
            + 0.035 * goal_difference_edge,
        ),
    )
    lambda_home = max(
        0.2,
        min(4.5, (values["home_gf_pg_10"] + values["away_ga_pg_10"]) / 2.0 + home_advantage / 2.0),
    )
    lambda_away = max(
        0.2,
        min(4.5, (values["away_gf_pg_10"] + values["home_ga_pg_10"]) / 2.0 - home_advantage / 2.0),
    )
    return {
        "form_shift": form_shift,
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "providers": sorted(providers),
    }


@lru_cache(maxsize=1)
def _static_history_rows() -> List[SimpleNamespace]:
    rows: List[SimpleNamespace] = []
    history_dir = _sports_history_dir()
    raw_dir = _raw_history_dir()
    csv_paths = list(history_dir.glob("**/*_matches.csv")) if history_dir.exists() else []
    if raw_dir.exists():
        csv_paths.extend(
            path for path in raw_dir.glob("*.csv")
            if path.stem.split("_")[0].upper() in _RAW_LEAGUES
        )

    for csv_path in sorted(csv_paths):
        raw_league_code = csv_path.stem.split("_")[0].upper()
        is_raw_football = raw_league_code in _RAW_LEAGUES
        try:
            with csv_path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    home = (row.get("home_team") or row.get("home") or row.get("HomeTeam") or "").strip()
                    away = (row.get("away_team") or row.get("away") or row.get("AwayTeam") or "").strip()
                    if not home or not away:
                        continue

                    home_score = row.get("home_score") or row.get("home_goals") or row.get("home_points") or row.get("FTHG")
                    away_score = row.get("away_score") or row.get("away_goals") or row.get("away_points") or row.get("FTAG")
                    try:
                        home_goals = int(float(str(home_score).strip())) if home_score not in (None, "") else None
                        away_goals = int(float(str(away_score).strip())) if away_score not in (None, "") else None
                    except (TypeError, ValueError):
                        home_goals = None
                        away_goals = None

                    try:
                        home_xg = float(row.get("home_xg") or row.get("HxG"))
                        if not math.isfinite(home_xg):
                            home_xg = None
                    except (TypeError, ValueError):
                        home_xg = None
                    try:
                        away_xg = float(row.get("away_xg") or row.get("AxG"))
                        if not math.isfinite(away_xg):
                            away_xg = None
                    except (TypeError, ValueError):
                        away_xg = None

                    if home_goals is None or away_goals is None:
                        continue

                    date_raw = row.get("date") or row.get("kickoff_time") or row.get("match_date") or row.get("datetime") or row.get("Date")
                    match_date = _as_utc(_parse_date(date_raw, day_first=is_raw_football))
                    if match_date is not None and match_date > datetime.now(timezone.utc):
                        continue
                    rows.append(SimpleNamespace(
                        home_team=home,
                        away_team=away,
                        home_goals=home_goals,
                        away_goals=away_goals,
                        home_xg=home_xg,
                        away_xg=away_xg,
                        kickoff_time=match_date or datetime.min.replace(tzinfo=timezone.utc),
                        league=(row.get("league") or (_RAW_LEAGUES.get(raw_league_code) if is_raw_football else csv_path.parent.name) or "").strip() or "unknown",
                        sport="football" if is_raw_football else csv_path.parent.name,
                        source=(row.get("source") or ("football-data-uk" if is_raw_football else "static_csv")).strip(),
                        source_file=str(csv_path),
                    ))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("STATIC_EVIDENCE failed to read %s: %s", csv_path, exc)

    rows.sort(key=lambda match: getattr(match, "kickoff_time", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return rows


def _is_before_cutoff(match: Any, before: Optional[datetime]) -> bool:
    if before is None:
        return True
    match_date = _as_utc(getattr(match, "kickoff_time", None))
    cutoff = _as_utc(before)
    return match_date is not None and cutoff is not None and match_date < cutoff


def _static_history_for_team(
    team: str,
    limit: int = 10,
    league: Optional[str] = None,
    before: Optional[datetime] = None,
    sport: Optional[str] = None,
) -> List[SimpleNamespace]:
    team_matches: List[SimpleNamespace] = []
    for match in _static_history_rows():
        if (
            league
            and match.league.lower() not in {"unknown", ""}
            and _normalise_league_name(match.league) != _normalise_league_name(league)
        ):
            continue
        if not _is_before_cutoff(match, before):
            continue
        if sport and match.sport not in {sport.lower(), "sports"}:
            continue
        if _match_team_name(team, match.home_team) or _match_team_name(team, match.away_team):
            team_matches.append(match)
        if len(team_matches) >= limit:
            break
    return team_matches


def _static_history_for_pair(
    home: str,
    away: str,
    limit: int = 10,
    league: Optional[str] = None,
    before: Optional[datetime] = None,
    sport: Optional[str] = None,
) -> List[SimpleNamespace]:
    pair_matches: List[SimpleNamespace] = []
    for match in _static_history_rows():
        if (
            league
            and match.league.lower() not in {"unknown", ""}
            and _normalise_league_name(match.league) != _normalise_league_name(league)
        ):
            continue
        if not _is_before_cutoff(match, before):
            continue
        if sport and match.sport not in {sport.lower(), "sports"}:
            continue
        if (
            (_match_team_name(home, match.home_team) and _match_team_name(away, match.away_team)) or
            (_match_team_name(home, match.away_team) and _match_team_name(away, match.home_team))
        ):
            pair_matches.append(match)
        if len(pair_matches) >= limit:
            break
    return pair_matches



def _team_search_terms(team: str) -> list[str]:
    import re
    if not team:
        return []
    lowered = team.lower().strip()
    custom_map = {
        'olympique lyonnais': ['lyon', 'olympique lyonnais', 'ol lyon'],
        'lyon': ['lyon', 'olympique lyonnais'],
        'aj auxerre': ['auxerre', 'aj auxerre'],
        'auxerre': ['auxerre', 'aj auxerre'],
        'paris saint germain': ['psg', 'paris sg', 'paris saint-germain'],
        'paris sg': ['psg', 'paris sg', 'paris saint germain'],
        'psg': ['psg', 'paris sg', 'paris saint germain'],
        'fc internazionale milano': [
            'fc internazionale milano', 'internazionale milano',
            'inter milan', 'inter milano', 'inter',
        ],
        'inter milan': [
            'inter milan', 'fc internazionale milano',
            'internazionale milano', 'inter milano', 'inter',
        ],
        'udinese calcio': ['udinese calcio', 'udinese'],
        'udinese': ['udinese calcio', 'udinese'],
        'queens park rangers': ['queens park rangers', 'qpr'],
        'qpr': ['qpr', 'queens park rangers'],
        'west ham united fc': ['west ham united fc', 'west ham united', 'west ham'],
        'west ham united': ['west ham united fc', 'west ham united', 'west ham'],
        'west ham': ['west ham united fc', 'west ham united', 'west ham'],
        'bayer 04 leverkusen': ['bayer 04 leverkusen', 'bayer leverkusen', 'leverkusen'],
        'bayer leverkusen': ['bayer 04 leverkusen', 'bayer leverkusen', 'leverkusen'],
        'leverkusen': ['bayer 04 leverkusen', 'bayer leverkusen', 'leverkusen'],
        'ararat-armenia-2': [
            'ararat-armenia-2', 'ararat armenia 2', 'ararat-armenia',
        ],
        'bentonit ijevan': ['bentonit ijevan', 'bentonit'],
    }
    if lowered in custom_map:
        return custom_map[lowered]
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', team).strip()
    words = cleaned.split()
    non_generic = [w for w in words if w.lower() not in {'fc', 'cf', 'afc', 'aj', 'as', 'us', 'sc', 'ogc', 'rc', 'the', 'club', 'sporting', 'olympique'}]
    terms = [team, cleaned]
    if non_generic:
        terms.append(' '.join(non_generic))
        for w in non_generic:
            if len(w) >= 3:
                terms.append(w)
    seen = set()
    res = []
    for t in terms:
        t_strip = t.strip()
        if t_strip and t_strip.lower() not in seen:
            seen.add(t_strip.lower())
            res.append(t_strip)
    return res


async def _recent_matches_for(
    db: AsyncSession,
    team: str,
    limit: int = 10,
    before: Optional[datetime] = None,
    sport: Optional[str] = None,
) -> List[Match]:
    """Most-recent settled matches for a team (home or away), newest first."""
    terms = _team_search_terms(team)
    conditions = []
    for term in terms:
        conditions.append(Match.home_team.ilike(f'%{term}%'))
        conditions.append(Match.away_team.ilike(f'%{term}%'))
    filters = [
        or_(*conditions),
        Match.home_goals.isnot(None),
        Match.away_goals.isnot(None),
    ]
    if before is not None:
        filters.append(Match.kickoff_time < before)
    if sport:
        filters.append(Match.sport == sport.lower())
    stmt = (
        select(Match)
        .where(*filters)
        .order_by(desc(Match.kickoff_time))
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def _h2h_matches(
    db: AsyncSession,
    home: str,
    away: str,
    limit: int = 10,
    before: Optional[datetime] = None,
    sport: Optional[str] = None,
) -> List[Match]:
    home_terms = _team_search_terms(home)
    away_terms = _team_search_terms(away)
    home_conds = [or_(Match.home_team.ilike(f'%{t}%'), Match.away_team.ilike(f'%{t}%')) for t in home_terms]
    away_conds = [or_(Match.home_team.ilike(f'%{t}%'), Match.away_team.ilike(f'%{t}%')) for t in away_terms]
    filters = [
        and_(
                or_(*home_conds),
                or_(*away_conds),
                Match.home_goals.isnot(None),
                Match.away_goals.isnot(None),
        )
    ]
    if before is not None:
        filters.append(Match.kickoff_time < before)
    if sport:
        filters.append(Match.sport == sport.lower())
    stmt = (
        select(Match)
        .where(*filters)
        .order_by(desc(Match.kickoff_time))
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


def _form_block(team: str, matches: List[Match], window: int) -> Dict[str, float]:
    """Compute (points/game, goals_for/game, goals_against/game) over window."""
    sliced = matches[:window]
    if not sliced:
        return {"pts_pg": 1.25, "gf_pg": 1.30, "ga_pg": 1.30, "n": 0}

    team_terms = [term.lower() for term in _team_search_terms(team)]

    def is_team_name(value: str) -> bool:
        lowered = value.lower()
        return any(term in lowered or lowered in term for term in team_terms)

    pts = gf = ga = 0
    for m in sliced:
        if is_team_name(m.home_team):
            tg, og = int(m.home_goals or 0), int(m.away_goals or 0)
        else:
            tg, og = int(m.away_goals or 0), int(m.home_goals or 0)
        gf += tg
        ga += og
        if tg > og:
            pts += 3
        elif tg == og:
            pts += 1
    n = len(sliced)
    return {
        "pts_pg": round(pts / n, 4),
        "gf_pg":  round(gf / n, 4),
        "ga_pg":  round(ga / n, 4),
        "n":      n,
    }


def _h2h_block(home: str, away: str, matches: List[Match]) -> Dict[str, float]:
    """Win-rate split + goals-per-game from the home team's perspective."""
    if not matches:
        return {
            "home_wr": 0.45, "draw_wr": 0.27, "away_wr": 0.28,
            "home_gpg": 1.45, "away_gpg": 1.20, "n": 0,
        }
    h_wins = draws = a_wins = 0
    h_goals = a_goals = 0
    for m in matches:
        # Normalise to "home-team" perspective regardless of which side they were on
        if m.home_team == home:
            hg, ag = int(m.home_goals or 0), int(m.away_goals or 0)
        else:
            hg, ag = int(m.away_goals or 0), int(m.home_goals or 0)
        h_goals += hg
        a_goals += ag
        if hg > ag:
            h_wins += 1
        elif hg == ag:
            draws += 1
        else:
            a_wins += 1
    n = len(matches)
    return {
        "home_wr":  round(h_wins / n, 4),
        "draw_wr":  round(draws / n, 4),
        "away_wr":  round(a_wins / n, 4),
        "home_gpg": round(h_goals / n, 4),
        "away_gpg": round(a_goals / n, 4),
        "n":        n,
    }


def _elo_proxy(home_form: Dict[str, float], away_form: Dict[str, float]) -> float:
    """
    Cheap ELO-delta proxy from form differential.

    +400 ≈ heavy home favourite, -400 ≈ heavy away favourite, 0 = balanced.
    Real ELO is computed elsewhere; this is a strong-enough signal for the
    sklearn heads when ELO state isn't available.
    """
    h_strength = home_form["pts_pg"] + 0.6 * home_form["gf_pg"] - 0.5 * home_form["ga_pg"]
    a_strength = away_form["pts_pg"] + 0.6 * away_form["gf_pg"] - 0.5 * away_form["ga_pg"]
    return round((h_strength - a_strength) * 90.0, 2)


async def build_predict_features(
    db: Optional[AsyncSession],
    home_team: str,
    away_team: str,
    league: Optional[str] = None,
    before: Optional[datetime] = None,
    sport: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns a feature dict ready to merge into the orchestrator `features` arg.

    Resilient by design: every block has its own try/except. If the DB is
    unavailable or there is no history at all, the function returns the
    fallback feature set with `feature_completeness=0.0` so downstream
    diagnostics can detect this.
    """
    home_recent: List[Any] = []
    away_recent: List[Any] = []
    h2h: List[Any] = []
    evidence_source = "db"

    if db is None:
        static_home = _static_history_for_team(home_team, limit=10, league=league, before=before, sport=sport)
        static_away = _static_history_for_team(away_team, limit=10, league=league, before=before, sport=sport)
        static_h2h = _static_history_for_pair(home_team, away_team, limit=10, league=league, before=before, sport=sport)
        if not static_home and not static_away and not static_h2h:
            logger.warning(
                "FEATURE_FALLBACK db=None for %s vs %s — no static historical evidence found; "
                "returning neutral fallback feature set",
                home_team, away_team,
            )
            return dict(_FALLBACK_FEATURES)
        home_recent = static_home
        away_recent = static_away
        h2h = static_h2h
        providers = {
            getattr(match, "source", "static_csv")
            for match in home_recent + away_recent + h2h
        }
        evidence_source = next(iter(providers)) if len(providers) == 1 else "mixed"
        logger.info(
            "FEATURE_EVIDENCE db=None for %s vs %s — using real static CSV history (%d rows)",
            home_team, away_team, len(home_recent) + len(away_recent) + len(h2h),
        )

    else:
        try:
            home_recent_db = await _recent_matches_for(db, home_team, limit=10, before=before, sport=sport)
            static_home = _static_history_for_team(
                home_team, limit=10, league=league, before=before, sport=sport,
            ) if len(home_recent_db) < 10 else []
            home_recent = _merge_match_history(home_recent_db, static_home, limit=10)
            if static_home:
                evidence_source = "mixed"
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"home recent fetch failed for {home_team}: {exc}")
            home_recent = []

        try:
            away_recent_db = await _recent_matches_for(db, away_team, limit=10, before=before, sport=sport)
            static_away = _static_history_for_team(
                away_team, limit=10, league=league, before=before, sport=sport,
            ) if len(away_recent_db) < 10 else []
            away_recent = _merge_match_history(away_recent_db, static_away, limit=10)
            if static_away:
                evidence_source = "mixed"
        except Exception as exc:  # pragma: no cover
            logger.warning(f"away recent fetch failed for {away_team}: {exc}")
            away_recent = []

        try:
            h2h_db = await _h2h_matches(db, home_team, away_team, limit=10, before=before, sport=sport)
            static_h2h = _static_history_for_pair(
                home_team, away_team, limit=10, league=league, before=before, sport=sport,
            ) if len(h2h_db) < 10 else []
            h2h = _merge_match_history(h2h_db, static_h2h, limit=10)
            if static_h2h:
                evidence_source = "mixed"
        except Exception as exc:  # pragma: no cover
            logger.warning(f"h2h fetch failed for {home_team} vs {away_team}: {exc}")
            h2h = []

        if not home_recent and not away_recent and not h2h:
            static_home = _static_history_for_team(home_team, limit=10, league=league, before=before, sport=sport)
            static_away = _static_history_for_team(away_team, limit=10, league=league, before=before, sport=sport)
            static_h2h = _static_history_for_pair(home_team, away_team, limit=10, league=league, before=before, sport=sport)
            if static_home or static_away or static_h2h:
                home_recent = static_home
                away_recent = static_away
                h2h = static_h2h
                evidence_source = "static_csv"

    out: Dict[str, Any] = {}
    completeness_signals: List[float] = []

    # Explicit fallback warnings — operators must see when the feature
    # builder is running on cold-start defaults instead of real history.
    if not home_recent:
        logger.warning(
            "FEATURE_FALLBACK home=%s — no historical matches found, using neutral form/GF/GA defaults",
            home_team,
        )
    if not away_recent:
        logger.warning(
            "FEATURE_FALLBACK away=%s — no historical matches found, using neutral form/GF/GA defaults",
            away_team,
        )
    if not h2h:
        logger.info(
            "FEATURE_FALLBACK h2h=%s vs %s — no head-to-head history, using neutral H2H split",
            home_team, away_team,
        )

    home_5  = _form_block(home_team, home_recent, window=5)
    home_10 = _form_block(home_team, home_recent, window=10)
    away_5  = _form_block(away_team, away_recent, window=5)
    away_10 = _form_block(away_team, away_recent, window=10)
    h2h_b   = _h2h_block(home_team, away_team, h2h)

    out.update({
        "home_form_pts_5":   home_5["pts_pg"],
        "away_form_pts_5":   away_5["pts_pg"],
        "home_form_pts_10":  home_10["pts_pg"],
        "away_form_pts_10":  away_10["pts_pg"],
        "home_gf_pg_5":      home_5["gf_pg"],
        "away_gf_pg_5":      away_5["gf_pg"],
        "home_ga_pg_5":      home_5["ga_pg"],
        "away_ga_pg_5":      away_5["ga_pg"],
        "home_gf_pg_10":     home_10["gf_pg"],
        "away_gf_pg_10":     away_10["gf_pg"],
        "home_ga_pg_10":     home_10["ga_pg"],
        "away_ga_pg_10":     away_10["ga_pg"],
        "h2h_home_win_pct":  h2h_b["home_wr"],
        "h2h_draw_pct":      h2h_b["draw_wr"],
        "h2h_away_win_pct":  h2h_b["away_wr"],
        "h2h_home_goals_pg": h2h_b["home_gpg"],
        "h2h_away_goals_pg": h2h_b["away_gpg"],
        "home_adv_league":   _LEAGUE_HOME_ADV.get((league or "").lower(), _DEFAULT_HOME_ADV),
        "elo_diff":          _elo_proxy(
            {"pts_pg": home_10["pts_pg"], "gf_pg": home_10["gf_pg"], "ga_pg": home_10["ga_pg"]},
            {"pts_pg": away_10["pts_pg"], "gf_pg": away_10["gf_pg"], "ga_pg": away_10["ga_pg"]},
        ),
    })

    # Keep the underlying sample size explicit so readiness can distinguish
    # real history from neutral fallback values.
    completeness_signals.append(min(1.0, home_10["n"] / 5.0))
    completeness_signals.append(min(1.0, away_10["n"] / 5.0))
    completeness_signals.append(min(1.0, h2h_b["n"] / 3.0))
    out["feature_completeness"] = round(sum(completeness_signals) / 3.0, 3)
    out["history_sample_size"] = min(home_10["n"], away_10["n"])
    out["home_history_sample_size"] = home_10["n"]
    out["away_history_sample_size"] = away_10["n"]
    out["h2h_sample_size"] = h2h_b["n"]
    out["home_history_latest"] = _latest_match_date(home_recent)
    out["away_history_latest"] = _latest_match_date(away_recent)
    out["h2h_history_latest"] = _latest_match_date(h2h)
    evidence_providers = sorted({
        getattr(match, "source", None) or "db"
        for match in home_recent + away_recent + h2h
    })
    if evidence_providers:
        evidence_source = evidence_providers[0] if len(evidence_providers) == 1 else "mixed"
    out["evidence_providers"] = evidence_providers
    out["feature_version"] = FEATURE_VERSION
    out["evidence_source"] = evidence_source

    return out
