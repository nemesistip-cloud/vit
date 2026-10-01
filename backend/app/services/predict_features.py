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
import re
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone
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


def _match_team_name(team: str, candidate: str) -> bool:
    if not team or not candidate:
        return False
    target = _normalise_team_name(team)
    other = _normalise_team_name(candidate)
    if not target or not other:
        return False
    if target == other:
        return True
    if target in other or other in target:
        return True
    for term in _team_search_terms(team):
        norm_term = _normalise_team_name(term)
        if norm_term and norm_term in other:
            return True
    return False


def _sports_history_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "sports"


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y"):
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


def _static_history_rows() -> List[SimpleNamespace]:
    rows: List[SimpleNamespace] = []
    history_dir = _sports_history_dir()
    if not history_dir.exists():
        return rows

    for csv_path in sorted(history_dir.glob("**/*_matches.csv")):
        try:
            with csv_path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    home = (row.get("home_team") or row.get("home") or "").strip()
                    away = (row.get("away_team") or row.get("away") or "").strip()
                    if not home or not away:
                        continue

                    home_score = row.get("home_score") or row.get("home_goals") or row.get("home_points")
                    away_score = row.get("away_score") or row.get("away_goals") or row.get("away_points")
                    try:
                        home_goals = int(float(str(home_score).strip())) if home_score not in (None, "") else None
                        away_goals = int(float(str(away_score).strip())) if away_score not in (None, "") else None
                    except (TypeError, ValueError):
                        home_goals = None
                        away_goals = None

                    if home_goals is None or away_goals is None:
                        continue

                    date_raw = row.get("date") or row.get("kickoff_time") or row.get("match_date") or row.get("datetime")
                    match_date = _as_utc(_parse_date(date_raw))
                    if match_date is not None and match_date > datetime.now(timezone.utc):
                        continue
                    rows.append(SimpleNamespace(
                        home_team=home,
                        away_team=away,
                        home_goals=home_goals,
                        away_goals=away_goals,
                        kickoff_time=match_date or datetime.min.replace(tzinfo=timezone.utc),
                        league=(row.get("league") or csv_path.parent.name or "").strip() or "unknown",
                        source_file=str(csv_path),
                    ))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("STATIC_EVIDENCE failed to read %s: %s", csv_path, exc)

    rows.sort(key=lambda match: getattr(match, "kickoff_time", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return rows


def _static_history_for_team(team: str, limit: int = 10, league: Optional[str] = None) -> List[SimpleNamespace]:
    team_matches: List[SimpleNamespace] = []
    for match in _static_history_rows():
        if league and match.league.lower() not in {"unknown", ""} and match.league.lower() != str(league).lower():
            continue
        if _match_team_name(team, match.home_team) or _match_team_name(team, match.away_team):
            team_matches.append(match)
        if len(team_matches) >= limit:
            break
    return team_matches


def _static_history_for_pair(home: str, away: str, limit: int = 10, league: Optional[str] = None) -> List[SimpleNamespace]:
    pair_matches: List[SimpleNamespace] = []
    for match in _static_history_rows():
        if league and match.league.lower() not in {"unknown", ""} and match.league.lower() != str(league).lower():
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
    stmt = (
        select(Match)
        .where(*filters)
        .order_by(desc(Match.kickoff_time))
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def _h2h_matches(
    db: AsyncSession, home: str, away: str, limit: int = 10
) -> List[Match]:
    home_terms = _team_search_terms(home)
    away_terms = _team_search_terms(away)
    home_conds = [or_(Match.home_team.ilike(f'%{t}%'), Match.away_team.ilike(f'%{t}%')) for t in home_terms]
    away_conds = [or_(Match.home_team.ilike(f'%{t}%'), Match.away_team.ilike(f'%{t}%')) for t in away_terms]
    stmt = (
        select(Match)
        .where(
            and_(
                or_(*home_conds),
                or_(*away_conds),
                Match.home_goals.isnot(None),
                Match.away_goals.isnot(None),
            )
        )
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
        static_home = _static_history_for_team(home_team, limit=10, league=league)
        static_away = _static_history_for_team(away_team, limit=10, league=league)
        static_h2h = _static_history_for_pair(home_team, away_team, limit=10, league=league)
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
        evidence_source = "static_csv"
        logger.info(
            "FEATURE_EVIDENCE db=None for %s vs %s — using real static CSV history (%d rows)",
            home_team, away_team, len(home_recent) + len(away_recent) + len(h2h),
        )

    else:
        try:
            home_recent_db = await _recent_matches_for(db, home_team, limit=10, before=before)
            if home_recent_db:
                home_recent = home_recent_db
            else:
                static_home = _static_history_for_team(home_team, limit=10, league=league)
                if static_home:
                    home_recent = static_home
                    evidence_source = "mixed"
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"home recent fetch failed for {home_team}: {exc}")
            home_recent = []

        try:
            away_recent_db = await _recent_matches_for(db, away_team, limit=10, before=before)
            if away_recent_db:
                away_recent = away_recent_db
            else:
                static_away = _static_history_for_team(away_team, limit=10, league=league)
                if static_away:
                    away_recent = static_away
                    if evidence_source != "mixed":
                        evidence_source = "mixed"
        except Exception as exc:  # pragma: no cover
            logger.warning(f"away recent fetch failed for {away_team}: {exc}")
            away_recent = []

        try:
            h2h_db = await _h2h_matches(db, home_team, away_team, limit=10)
            if h2h_db:
                h2h = h2h_db
            else:
                static_h2h = _static_history_for_pair(home_team, away_team, limit=10, league=league)
                if static_h2h:
                    h2h = static_h2h
                    evidence_source = "mixed"
        except Exception as exc:  # pragma: no cover
            logger.warning(f"h2h fetch failed for {home_team} vs {away_team}: {exc}")
            h2h = []

        if not home_recent and not away_recent and not h2h:
            static_home = _static_history_for_team(home_team, limit=10, league=league)
            static_away = _static_history_for_team(away_team, limit=10, league=league)
            static_h2h = _static_history_for_pair(home_team, away_team, limit=10, league=league)
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
    out["feature_version"] = FEATURE_VERSION
    out["evidence_source"] = evidence_source

    return out
