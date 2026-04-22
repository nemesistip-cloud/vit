# app/services/results_settler.py
"""
Auto-settlement service — v2.0

Polls Football-Data.org for FINISHED matches and settles predictions.

Key improvements over v1:
- Fuzzy name matching via SequenceMatcher (handles "Manchester United FC" ↔ "Man. United")
- Checks ALL finished API matches, not just those already in the DB
- Creates new Match records for finished games that were never predicted, so the
  full results history is always available in analytics
- Bankroll is updated after every settled prediction
- Thread-safe asyncio DB session usage
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, AsyncSessionLocal
from app.db.models import Match, Prediction, CLVEntry
from app.services.clv_tracker import CLVTracker

logger = logging.getLogger(__name__)

COMPETITIONS = {
    "premier_league": "PL",
    "serie_a":        "SA",
    "la_liga":        "PD",
    "bundesliga":     "BL1",
    "ligue_1":        "FL1",
    "championship":   "ELC",
    "eredivisie":     "DED",
    "primeira_liga":  "PPL",
    "scottish_premiership": "SPL",
    "belgian_pro_league":   "BJL",
}

_FORBIDDEN_LEAGUES: set = set()
_KEY_PERMANENTLY_INVALID: bool = False

# Similarity threshold for fuzzy name matching (0-1).
# 0.72 allows "Man. United" ↔ "Manchester United FC" but rejects "Man City" ↔ "Man United"
_NAME_SIM_THRESHOLD = 0.72


def _strip_suffixes(name: str) -> str:
    """Remove only generic club-type suffixes, NOT meaningful words like United/City."""
    for suffix in [" FC", " AFC", " CF", " SC", " FK", " SK", " AC", " IF", " BK",
                   " SV", " VV", " FV", " BSC", " TSV", " RB", " 1. "]:
        name = name.replace(suffix, "")
    return name.strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _names_match(api_name: str, db_name: str) -> bool:
    """
    Return True when two team names refer to the same club.

    Strategy (in order):
    1. Exact case-insensitive match
    2. After stripping generic suffixes (FC, AFC …)
    3. Fuzzy similarity ≥ 0.72 on raw names
    4. Fuzzy similarity ≥ 0.72 on stripped names
    """
    if api_name.lower() == db_name.lower():
        return True

    stripped_api = _strip_suffixes(api_name)
    stripped_db  = _strip_suffixes(db_name)

    if stripped_api.lower() == stripped_db.lower():
        return True

    if _similarity(api_name, db_name) >= _NAME_SIM_THRESHOLD:
        return True

    if _similarity(stripped_api, stripped_db) >= _NAME_SIM_THRESHOLD:
        return True

    return False


async def fetch_finished_matches(days_back: int = 2) -> list:
    """
    Pull FINISHED matches from Football-Data.org for the last `days_back` days.
    Returns a list of dicts: home_team, away_team, league, kickoff, home_goals, away_goals.
    """
    global _KEY_PERMANENTLY_INVALID
    key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    if not key:
        logger.warning("FOOTBALL_DATA_API_KEY not set — cannot fetch finished matches")
        return []

    if _KEY_PERMANENTLY_INVALID:
        logger.debug("Skipping finished-match fetch — API key permanently invalid")
        return []

    now       = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
    date_to   = now.strftime("%Y-%m-%d")
    finished  = []
    new_forbidden = 0

    async with httpx.AsyncClient(timeout=30) as client:
        for league, code in COMPETITIONS.items():
            if league in _FORBIDDEN_LEAGUES:
                continue
            try:
                r = await client.get(
                    f"https://api.football-data.org/v4/competitions/{code}/matches",
                    headers={"X-Auth-Token": key},
                    params={"status": "FINISHED", "dateFrom": date_from, "dateTo": date_to},
                )
                if r.status_code == 200:
                    for m in r.json().get("matches", []):
                        score = m.get("score", {}).get("fullTime", {})
                        home_g = score.get("home")
                        away_g = score.get("away")
                        if home_g is None or away_g is None:
                            continue
                        finished.append({
                            "home_team":  m["homeTeam"]["name"],
                            "away_team":  m["awayTeam"]["name"],
                            "league":     league,
                            "kickoff":    m.get("utcDate", ""),
                            "home_goals": int(home_g),
                            "away_goals": int(away_g),
                        })
                elif r.status_code == 401:
                    logger.warning("FOOTBALL_DATA_API_KEY is invalid or expired — suspending all settlement fetch")
                    _KEY_PERMANENTLY_INVALID = True
                    break
                elif r.status_code == 429:
                    logger.warning(f"Rate limit hit for {league}")
                elif r.status_code == 403:
                    _FORBIDDEN_LEAGUES.add(league)
                    new_forbidden += 1
                    logger.debug(f"API key tier does not cover {league} — blacklisted for this session")
            except Exception as e:
                logger.warning(f"Finished-match fetch failed for {league}: {e}")

    if new_forbidden:
        logger.warning(
            f"FOOTBALL_DATA_API_KEY tier excludes {new_forbidden} league(s) — "
            f"upgrade key or remove them from COMPETITIONS. Blacklisted: {sorted(_FORBIDDEN_LEAGUES)}"
        )
    logger.info(f"Fetched {len(finished)} finished match(es) from Football-Data API")
    return finished


async def fetch_live_matches() -> list:
    """
    Pull IN_PLAY matches from Football-Data.org right now.
    """
    key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    if not key:
        return []

    if _KEY_PERMANENTLY_INVALID:
        return []

    live = []
    async with httpx.AsyncClient(timeout=15) as client:
        for league, code in COMPETITIONS.items():
            if league in _FORBIDDEN_LEAGUES:
                continue
            try:
                r = await client.get(
                    f"https://api.football-data.org/v4/competitions/{code}/matches",
                    headers={"X-Auth-Token": key},
                    params={"status": "IN_PLAY"},
                )
                if r.status_code == 200:
                    for m in r.json().get("matches", []):
                        score = (m.get("score", {}).get("currentScore") or
                                 m.get("score", {}).get("halfTime", {}))
                        live.append({
                            "home_team":    m["homeTeam"]["name"],
                            "away_team":    m["awayTeam"]["name"],
                            "league":       league,
                            "kickoff_time": m.get("utcDate", ""),
                            "status":       "live",
                            "home_score":   score.get("home") if score else None,
                            "away_score":   score.get("away") if score else None,
                            "minute":       m.get("minute"),
                            "market_odds":  {},
                        })
                elif r.status_code in (401, 403):
                    _FORBIDDEN_LEAGUES.add(league)
            except Exception as e:
                logger.warning(f"Live-match fetch failed for {league}: {e}")

    return live


def _parse_kickoff(utc_str: str) -> datetime:
    """Parse an ISO datetime string to a naive-UTC datetime."""
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


def _determine_outcome(home_g: int, away_g: int) -> str:
    if home_g > away_g:
        return "home"
    if home_g == away_g:
        return "draw"
    return "away"


async def settle_results(days_back: int = 2) -> dict:
    """
    Full settlement pass:

    For every FINISHED match returned by the API:
      a) If a matching unsettled Match row exists in DB → settle it (update score, CLV, P&L)
      b) If an already-settled Match row exists        → count as already_settled
      c) If no Match row exists at all               → create one (status=completed)
         so analytics always has complete result history

    Bankroll is updated after every settled prediction.
    """
    finished = await fetch_finished_matches(days_back)
    if not finished:
        return {
            "settled": 0, "already_settled": 0,
            "no_prediction": 0, "not_found": 0, "no_db_match": 0,
            "errors": 0, "details": [],
            "message": "No finished matches returned from API — check FOOTBALL_DATA_API_KEY",
        }

    settled         = 0
    already_settled = 0
    no_prediction   = 0
    created_new     = 0
    errors          = 0
    details         = []

    async with AsyncSessionLocal() as db:
        # Pre-load all matches (any status) to avoid N+1 queries
        all_matches_result = await db.execute(select(Match))
        all_matches: list[Match] = all_matches_result.scalars().all()

        for api_match in finished:
            try:
                home_g  = api_match["home_goals"]
                away_g  = api_match["away_goals"]
                outcome = _determine_outcome(home_g, away_g)
                kickoff = _parse_kickoff(api_match.get("kickoff", ""))

                # ── Find DB match (any status) ────────────────────────
                db_match: Optional[Match] = None
                for m in all_matches:
                    if (_names_match(api_match["home_team"], m.home_team) and
                            _names_match(api_match["away_team"], m.away_team)):
                        db_match = m
                        break

                # ── Already settled → skip ────────────────────────────
                if db_match and db_match.status == "completed":
                    already_settled += 1
                    continue

                # ── No DB record → create a completed match record ────
                if db_match is None:
                    db_match = Match(
                        home_team     = api_match["home_team"],
                        away_team     = api_match["away_team"],
                        league        = api_match["league"],
                        kickoff_time  = kickoff,
                        home_goals    = home_g,
                        away_goals    = away_g,
                        actual_outcome= outcome,
                        status        = "completed",
                    )
                    db.add(db_match)
                    await db.flush()           # get db_match.id
                    all_matches.append(db_match)
                    created_new  += 1
                    no_prediction += 1
                    logger.info(
                        f"[settle] New record created: "
                        f"{api_match['home_team']} {home_g}-{away_g} {api_match['away_team']}"
                    )
                else:
                    # ── Existing unsettled match → update scores ──────
                    db_match.home_goals     = home_g
                    db_match.away_goals     = away_g
                    db_match.actual_outcome = outcome
                    db_match.status         = "completed"

                    # ── Settle linked prediction ───────────────────────
                    pred_res = await db.execute(
                        select(Prediction).where(Prediction.match_id == db_match.id)
                    )
                    prediction = pred_res.scalar_one_or_none()

                    profit = 0.0
                    if prediction and prediction.bet_side:
                        won    = prediction.bet_side == outcome
                        stake  = prediction.recommended_stake or 0.0
                        odds   = prediction.entry_odds or 2.0
                        profit = stake * (odds - 1) if won else -stake

                        # CLV update
                        clv_res = await db.execute(
                            select(CLVEntry).where(CLVEntry.prediction_id == prediction.id)
                        )
                        clv_entry = clv_res.scalar_one_or_none()
                        # Use actual closing odds only; fall back to entry_odds (same side)
                        # rather than hardcoded market averages so CLV is not fabricated.
                        clv_home = db_match.closing_odds_home or None
                        clv_draw = db_match.closing_odds_draw or None
                        clv_away = db_match.closing_odds_away or None
                        closing_available = all(
                            x is not None for x in [clv_home, clv_draw, clv_away]
                        )
                        side_odds = (
                            {"home": clv_home, "draw": clv_draw, "away": clv_away}.get(
                                prediction.bet_side
                            )
                            or odds
                        )

                        if clv_entry:
                            clv_entry.closing_odds = side_odds if closing_available else None
                            clv_entry.clv          = (
                                CLVTracker.calculate_clv(clv_entry.entry_odds or odds, side_odds)
                                if closing_available else None
                            )
                            clv_entry.bet_outcome  = "win" if won else "loss"
                            clv_entry.profit       = profit
                            if not closing_available:
                                logger.warning(
                                    "[settle] Closing odds missing for match=%s — CLV not calculated",
                                    db_match.id,
                                )
                        else:
                            if closing_available:
                                await CLVTracker.update_closing_by_prediction(
                                    db, prediction.id,
                                    clv_home, clv_draw, clv_away,
                                    outcome, profit,
                                )
                            else:
                                logger.warning(
                                    "[settle] Closing odds missing for match=%s — CLV entry skipped",
                                    db_match.id,
                                )

                        # ── Bankroll update ───────────────────────────
                        try:
                            from app.services.bankroll import BankrollManager
                            bm = BankrollManager(db)
                            await bm.load_state()
                            bm.bankroll.update_bet(stake, odds, won)
                            await bm.save_state()
                        except Exception as be:
                            logger.warning(f"Bankroll update failed (non-fatal): {be}")
                    else:
                        no_prediction += 1

                await db.commit()
                settled += 1
                logger.info(
                    f"[settle] Settled: {db_match.home_team} {home_g}-{away_g} "
                    f"{db_match.away_team} ({outcome})"
                )
                details.append({
                    "home_team":  db_match.home_team,
                    "away_team":  db_match.away_team,
                    "home_goals": home_g,
                    "away_goals": away_g,
                    "outcome":    outcome,
                    "bet_side":   (prediction.bet_side
                                   if (db_match and 'prediction' in dir() and prediction) else None),
                    "profit":     (profit
                                   if (db_match and 'prediction' in dir() and prediction) else None),
                    "clv_value":  None,
                })

            except Exception as e:
                errors += 1
                logger.error(f"Settlement error for {api_match}: {e}", exc_info=True)
                try:
                    await db.rollback()
                except Exception:
                    pass

    total_processed = settled + already_settled
    return {
        "settled":         settled,
        "already_settled": already_settled,
        "no_prediction":   no_prediction,
        "not_found":       0,
        "no_db_match":     created_new,
        "created_new":     created_new,
        "errors":          errors,
        "details":         details,
        "message": (
            f"Settlement complete: {settled} settled, "
            f"{already_settled} already done, "
            f"{created_new} new records created"
        ),
    }
