# app/api/routes/odds_compare.py
# VIT Sports Intelligence Network — v3.0.0
# Multi-bookmaker odds comparison, arbitrage scanner, audit log

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import APP_VERSION

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/odds", tags=["odds"])

VERSION = APP_VERSION

# ── Bookmaker configuration ───────────────────────────────────────────
BOOKMAKERS = {
    "pinnacle":    "pinnacle",
    "bet365":      "bet365",
    "betfair_ex":  "betfair_ex_eu",
    "betway":      "betway",
    "unibet":      "unibet_eu",
    "williamhill": "williamhill",
    "bwin":        "bwin",
}

SPORT_MAP = {
    "premier_league": "soccer_epl",
    "la_liga":        "soccer_spain_la_liga",
    "bundesliga":     "soccer_germany_bundesliga",
    "serie_a":        "soccer_italy_serie_a",
    "ligue_1":        "soccer_france_ligue_one",
    "championship":   "soccer_england_championship",
    "eredivisie":     "soccer_netherlands_eredivisie",
    "primeira_liga":  "soccer_portugal_primeira_liga",
    "scottish_premiership": "soccer_scotland_premiership",
    "belgian_pro_league": "soccer_belgium_jupiler_pro_league",
}

# ── Audit log (in-memory, append-only) ───────────────────────────────
_audit_log: List[dict] = []

def _audit(action: str, details: dict):
    _audit_log.append({
        "id":        str(uuid.uuid4())[:8],
        "action":    action,
        "details":   details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(_audit_log) > 1000:
        _audit_log.pop(0)


def _verify_key(api_key: Optional[str] = None):
    auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    if not auth_enabled:
        return
    if api_key is None:
        return
    from app.config import get_env
    if api_key != get_env("API_KEY", ""):
        raise HTTPException(status_code=403, detail="Invalid admin key")


# ── Odds API helper ───────────────────────────────────────────────────
async def _fetch_multi_bookmaker_odds(sport: str, odds_key: str) -> tuple[List[dict], str]:
    """Fetch odds from multiple bookmakers via The Odds API.

    Returns (events, status) where status is one of:
    "ok" | "api_error" | "invalid_key" | "rate_limited" | "timeout" | "no_key"
    """
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(
                f"https://api.the-odds-api.com/v4/sports/{sport}/odds/",
                params={
                    "apiKey":     odds_key,
                    "regions":    "eu,uk",
                    "markets":    "h2h",
                    "oddsFormat": "decimal",
                }
            )
            if r.status_code == 200:
                return r.json(), "ok"
            elif r.status_code in (401, 403):
                logger.warning(f"Odds API auth error {r.status_code} for {sport}")
                raise HTTPException(status_code=503, detail="Odds API: invalid or expired API key")
            elif r.status_code == 422:
                return [], "invalid_sport"
            elif r.status_code == 429:
                logger.warning("Odds API rate limit hit")
                return [], "rate_limited"
            else:
                logger.warning(f"Odds API {r.status_code} for {sport}")
                return [], f"api_error_{r.status_code}"
    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.warning("Odds API request timed out")
        return [], "timeout"
    except Exception as e:
        logger.warning(f"Odds API fetch failed: {e}")
        return [], "fetch_error"


def _extract_h2h_odds(event: dict) -> dict:
    """Extract best + all bookmaker odds for a single event."""
    home = str(event.get("home_team", "")).strip()
    away = str(event.get("away_team", "")).strip()
    home_key = home.lower()
    away_key = away.lower()
    bk_odds = {}

    for bk in event.get("bookmakers", []):
        bk_name = bk.get("key", "unknown")
        for mkt in bk.get("markets", []):
            if mkt.get("key") == "h2h":
                home_price = 0
                draw_price = 0
                away_price = 0
                for outcome in mkt.get("outcomes", []):
                    name = str(outcome.get("name", "")).strip().lower()
                    price = outcome.get("price", 0)
                    if name in (home_key, "home"):
                        home_price = price
                    elif name == "draw":
                        draw_price = price
                    elif name in (away_key, "away"):
                        away_price = price

                if home_price > 1.01 and draw_price > 1.01 and away_price > 1.01:
                    bk_odds[bk_name] = {"home": home_price, "draw": draw_price, "away": away_price}

    if not bk_odds:
        return {}

    best_home = max((v["home"] for v in bk_odds.values()), default=0)
    best_draw = max((v["draw"] for v in bk_odds.values()), default=0)
    best_away = max((v["away"] for v in bk_odds.values()), default=0)

    return {
        "home_team":   home,
        "away_team":   away,
        "kickoff":     event.get("commence_time", ""),
        "bookmakers":  bk_odds,
        "best_odds":   {"home": best_home, "draw": best_draw, "away": best_away},
        "n_bookmakers": len(bk_odds),
    }


def _detect_arbitrage(event_odds: dict, min_profit_pct: float = 0.5) -> Optional[dict]:
    """
    Detect arbitrage opportunity across bookmakers for a single event.

    Arbitrage exists when sum(1/best_odds) < 1.0.
    Profit = (1 - sum(1/best_odds)) / sum(1/best_odds)
    """
    bk_odds = event_odds.get("bookmakers", {})
    if len(bk_odds) < 2:
        return None

    # Find best odds for each outcome across all bookmakers
    all_home = [(bk, v["home"]) for bk, v in bk_odds.items() if v.get("home", 0) > 1.01]
    all_draw = [(bk, v["draw"]) for bk, v in bk_odds.items() if v.get("draw", 0) > 1.01]
    all_away = [(bk, v["away"]) for bk, v in bk_odds.items() if v.get("away", 0) > 1.01]

    if not all_home or not all_draw or not all_away:
        return None

    best_home_bk, best_home = max(all_home, key=lambda x: x[1])
    best_draw_bk, best_draw = max(all_draw, key=lambda x: x[1])
    best_away_bk, best_away = max(all_away, key=lambda x: x[1])

    arb_sum = (1 / best_home) + (1 / best_draw) + (1 / best_away)
    if arb_sum >= 1.0:
        return None

    profit_pct = round((1 - arb_sum) / arb_sum * 100, 3)
    if profit_pct < min_profit_pct:
        return None

    # Calculate stakes for £100 total
    total_stake = 100
    home_stake = round(total_stake / (best_home * arb_sum), 2)
    draw_stake = round(total_stake / (best_draw * arb_sum), 2)
    away_stake = round(total_stake / (best_away * arb_sum), 2)

    return {
        "home_team":    event_odds["home_team"],
        "away_team":    event_odds["away_team"],
        "kickoff":      event_odds.get("kickoff", ""),
        "profit_pct":   profit_pct,
        "arb_sum":      round(arb_sum, 6),
        "legs": {
            "home": {"bookmaker": best_home_bk, "odds": best_home, "stake": home_stake},
            "draw": {"bookmaker": best_draw_bk, "odds": best_draw, "stake": draw_stake},
            "away": {"bookmaker": best_away_bk, "odds": best_away, "stake": away_stake},
        },
        "guaranteed_profit": round(total_stake * profit_pct / 100, 2),
    }


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/compare")
async def compare_odds(
    league:    str   = Query(default="premier_league"),
    api_key: Optional[str] = Query(default=None),
):
    """
    Return multi-bookmaker odds comparison for upcoming fixtures in a league.
    Shows best available price for each outcome and which book offers it.
    """
    _verify_key(api_key)
    odds_key = os.getenv("ODDS_API_KEY", "") or os.getenv("THE_ODDS_API_KEY", "")

    if not odds_key:
        raise HTTPException(status_code=503, detail="ODDS_API_KEY not configured")

    sport  = SPORT_MAP.get(league, "soccer_epl")
    events, data_status = await _fetch_multi_bookmaker_odds(sport, odds_key)

    comparison = []
    for ev in events[:20]:
        parsed = _extract_h2h_odds(ev)
        if parsed:
            comparison.append(parsed)

    _audit("odds_compare", {"league": league, "events_found": len(comparison), "status": data_status})

    return {
        "league":      league,
        "events":      comparison,
        "total":       len(comparison),
        "data_status": data_status,
        "fetched_at":  datetime.now(timezone.utc).isoformat(),
    }


@router.get("/arbitrage")
async def scan_arbitrage(
    league:         str   = Query(default="premier_league"),
    min_profit_pct: float = Query(default=0.5, description="Minimum profit % to report"),
    api_key: Optional[str] = Query(default=None),
):
    """
    Scan for arbitrage opportunities across bookmakers.
    Returns events where betting all outcomes guarantees profit.
    """
    _verify_key(api_key)
    odds_key = os.getenv("ODDS_API_KEY", "") or os.getenv("THE_ODDS_API_KEY", "")

    if not odds_key:
        raise HTTPException(status_code=503, detail="ODDS_API_KEY not configured")

    sport  = SPORT_MAP.get(league, "soccer_epl")
    events, data_status = await _fetch_multi_bookmaker_odds(sport, odds_key)

    opportunities = []
    scanned = 0

    for ev in events:
        parsed = _extract_h2h_odds(ev)
        if not parsed:
            continue
        scanned += 1
        arb = _detect_arbitrage(parsed, min_profit_pct)
        if arb:
            opportunities.append(arb)

    opportunities.sort(key=lambda x: x["profit_pct"], reverse=True)
    _audit("arbitrage_scan", {"league": league, "scanned": scanned, "found": len(opportunities), "status": data_status})

    return {
        "league":         league,
        "scanned":        scanned,
        "opportunities":  opportunities,
        "total_found":    len(opportunities),
        "min_profit_pct": min_profit_pct,
        "data_status":    data_status,
        "fetched_at":     datetime.now(timezone.utc).isoformat(),
    }


class InjuryNote(BaseModel):
    team:    str
    player:  str
    status:  str  # "out" | "doubtful" | "returning"
    note:    str = ""


# ── Injury / context adjustments ─────────────────────────────────────
_injury_store: List[dict] = []

@router.post("/injuries")
async def add_injury(note: InjuryNote, api_key: Optional[str] = Query(default=None)):
    """Add a manual injury/team news note that affects confidence."""
    _verify_key(api_key)
    entry = {**note.dict(), "id": str(uuid.uuid4())[:8], "added_at": datetime.now(timezone.utc).isoformat()}
    _injury_store.append(entry)
    _audit("injury_added", {"team": note.team, "player": note.player, "status": note.status})
    return {"added": entry}


@router.get("/injuries")
async def get_injuries(team: Optional[str] = Query(None), api_key: Optional[str] = Query(default=None)):
    """Return all injury notes, optionally filtered by team."""
    _verify_key(api_key)
    results = _injury_store if not team else [i for i in _injury_store if team.lower() in i["team"].lower()]
    return {"injuries": results, "total": len(results)}


@router.delete("/injuries/{injury_id}")
async def delete_injury(injury_id: str, api_key: Optional[str] = Query(default=None)):
    """Remove an injury note."""
    _verify_key(api_key)
    global _injury_store
    before = len(_injury_store)
    _injury_store = [i for i in _injury_store if i["id"] != injury_id]
    if len(_injury_store) == before:
        raise HTTPException(status_code=404, detail="Injury note not found")
    _audit("injury_deleted", {"id": injury_id})
    return {"deleted": injury_id}


# ── Audit Log ─────────────────────────────────────────────────────────
@router.get("/audit-log")
async def get_audit_log(
    limit:   int = Query(default=50, le=200),
    api_key: Optional[str] = Query(default=None),
):
    """Return the system audit log (all admin actions)."""
    _verify_key(api_key)
    return {
        "log":   list(reversed(_audit_log))[:limit],
        "total": len(_audit_log),
    }
