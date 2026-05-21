# app/api/routes/odds_compare.py
# VIT Sports Intelligence Network — v4.7.5
# Multi-bookmaker odds comparison, full-market view, arbitrage scanner, audit log

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import APP_VERSION, AUTH_ENABLED, API_KEY

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
    "premier_league":           "soccer_epl",
    "la_liga":                  "soccer_spain_la_liga",
    "bundesliga":               "soccer_germany_bundesliga",
    "serie_a":                  "soccer_italy_serie_a",
    "ligue_1":                  "soccer_france_ligue_one",
    "championship":             "soccer_efl_champ",
    "eredivisie":               "soccer_eredivisie",
    "primeira_liga":            "soccer_primeira_liga",
    "scottish_premiership":     "soccer_scotland_premiership",
    "belgian_pro_league":       "soccer_belgium_first_div",
    "champions_league":         "soccer_uefa_champs_league",
    "europa_league":            "soccer_uefa_europa_league",
    "league_1":                 "soccer_england_league1",
    "league_2":                 "soccer_england_league2",
    "fa_cup":                   "soccer_fa_cup",
    "germany_bundesliga2":      "soccer_germany_bundesliga2",
    "france_ligue_2":           "soccer_france_ligue_two",
    "spain_segunda":            "soccer_spain_segunda_division",
    "italy_serie_b":            "soccer_italy_serie_b",
    "usa_mls":                  "soccer_usa_mls",
    "mls":                      "soccer_usa_mls",
    "brazil_serie_a":           "soccer_brazil_campeonato",
    "brazil_serie_b":           "soccer_brazil_serie_b",
    "argentina_primera":        "soccer_argentina_primera_division",
    "copa_libertadores":        "soccer_conmebol_copa_libertadores",
    "copa_sudamericana":        "soccer_conmebol_copa_sudamericana",
    "australia_aleague":        "soccer_australia_aleague",
    "china_super_league":       "soccer_china_superleague",
    "denmark_superliga":        "soccer_denmark_superliga",
    "greece_super_league":      "soccer_greece_super_league",
    "austria_bundesliga":       "soccer_austria_bundesliga",
}

# Markets fetched in one API call (btts is NOT available for soccer on standard endpoint)
ALL_MARKETS = "h2h,totals,spreads"

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
    if not AUTH_ENABLED:
        return
    if api_key is None:
        return
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


# ── Core API fetch helper ─────────────────────────────────────────────

async def _fetch_odds(
    sport: str,
    odds_key: str,
    markets: str = ALL_MARKETS,
) -> tuple[List[dict], str, Optional[int]]:
    """
    Fetch event odds from The Odds API.

    Returns (events, status, requests_remaining) where status is one of:
    "ok" | "api_error" | "invalid_key" | "rate_limited" | "timeout" |
    "no_key" | "quota_exceeded"
    """
    try:
        async with httpx.AsyncClient(timeout=14) as client:
            r = await client.get(
                f"https://api.the-odds-api.com/v4/sports/{sport}/odds/",
                params={
                    "apiKey":     odds_key,
                    "regions":    "eu,uk",
                    "markets":    markets,
                    "oddsFormat": "decimal",
                },
            )
            remaining = None
            try:
                remaining = int(
                    r.headers.get(
                        "x-requests-remaining",
                        r.headers.get("X-Requests-Remaining", -1),
                    )
                )
            except (TypeError, ValueError):
                pass

            if r.status_code == 200:
                return r.json(), "ok", remaining
            elif r.status_code in (401, 403):
                raise HTTPException(status_code=503, detail="Odds API: invalid or expired API key")
            elif r.status_code == 402:
                return [], "quota_exceeded", remaining
            elif r.status_code == 422:
                return [], "invalid_sport", remaining
            elif r.status_code == 429:
                return [], "rate_limited", remaining
            else:
                return [], f"api_error_{r.status_code}", remaining

    except HTTPException:
        raise
    except httpx.TimeoutException:
        return [], "timeout", None
    except Exception as e:
        logger.warning(f"Odds API fetch failed: {e}")
        return [], "fetch_error", None


# ── Market extraction helpers ─────────────────────────────────────────

def _extract_h2h_odds(event: dict) -> dict:
    """Extract best + per-bookmaker 1X2 odds for a single event."""
    home     = str(event.get("home_team", "")).strip()
    away     = str(event.get("away_team", "")).strip()
    home_key = home.lower()
    away_key = away.lower()
    bk_odds: Dict[str, dict] = {}

    for bk in event.get("bookmakers", []):
        bk_name = bk.get("key", "unknown")
        for mkt in bk.get("markets", []):
            if mkt.get("key") != "h2h":
                continue
            hp = dp = ap = 0.0
            for o in mkt.get("outcomes", []):
                name  = str(o.get("name", "")).strip().lower()
                price = float(o.get("price", 0) or 0)
                if name in (home_key, "home"):    hp = price
                elif name == "draw":              dp = price
                elif name in (away_key, "away"):  ap = price
            if hp > 1.01 and dp > 1.01 and ap > 1.01:
                bk_odds[bk_name] = {"home": hp, "draw": dp, "away": ap}

    if not bk_odds:
        return {}

    best_home = max((v["home"] for v in bk_odds.values()), default=0)
    best_draw = max((v["draw"] for v in bk_odds.values()), default=0)
    best_away = max((v["away"] for v in bk_odds.values()), default=0)

    return {
        "home_team":    home,
        "away_team":    away,
        "kickoff":      event.get("commence_time", ""),
        "bookmakers":   bk_odds,
        "best_odds":    {"home": best_home, "draw": best_draw, "away": best_away},
        "n_bookmakers": len(bk_odds),
    }


def _extract_all_markets(event: dict) -> dict:
    """
    Extract ALL available markets for a single event across all bookmakers.

    Returns per event:
      h2h      — per-bookmaker + best 1X2 prices
      totals   — per-bookmaker O/U at 1.5, 2.5, 3.5, 4.5 + best prices
      spreads  — per-bookmaker Asian Handicap lines + best prices
      derived  — Double Chance (1X/X2/12) + Draw No Bet + vig-free probs
    """
    home     = str(event.get("home_team", "")).strip()
    away     = str(event.get("away_team", "")).strip()
    home_key = home.lower()
    away_key = away.lower()

    h2h_bk:     Dict[str, Dict]  = {}
    totals_bk:  Dict[str, Dict]  = {}
    spreads_bk: Dict[str, List]  = {}

    for bk in event.get("bookmakers", []):
        bk_name = bk.get("key", "unknown")

        for mkt in bk.get("markets", []):
            mk  = mkt.get("key", "")
            pts = mkt.get("point")
            ocs = mkt.get("outcomes", [])

            # ── 1X2 ─────────────────────────────────────────────────
            if mk == "h2h":
                hp = dp = ap = 0.0
                for o in ocs:
                    name  = str(o.get("name", "")).strip().lower()
                    price = float(o.get("price", 0) or 0)
                    if name in (home_key, "home"):    hp = price
                    elif name == "draw":              dp = price
                    elif name in (away_key, "away"):  ap = price
                if hp > 1.01 and dp > 1.01 and ap > 1.01:
                    h2h_bk[bk_name] = {"home": hp, "draw": dp, "away": ap}

            # ── Over / Under (1.5 / 2.5 / 3.5 / 4.5) ───────────────
            elif mk == "totals":
                entry = totals_bk.setdefault(bk_name, {})
                for o in ocs:
                    name  = str(o.get("name", "")).strip().lower()
                    price = float(o.get("price", 0) or 0)
                    line  = float(o.get("point") or pts or 0)
                    if not price or line not in (1.5, 2.5, 3.5, 4.5):
                        continue
                    suffix = str(line).replace(".", "")[0:2]   # "15","25","35","45"
                    if name == "over":
                        entry[f"over_{suffix}"] = price
                    elif name == "under":
                        entry[f"under_{suffix}"] = price

            # ── Asian Handicap (all lines) ────────────────────────────
            elif mk == "spreads":
                lines_map: Dict[float, Dict] = {}
                for o in ocs:
                    name  = str(o.get("name", "")).strip()
                    price = float(o.get("price", 0) or 0)
                    line  = float(o.get("point") or pts or 0)
                    if not price:
                        continue
                    nl = name.lower()
                    if line not in lines_map:
                        lines_map[line] = {"line": line}
                    if nl in (home_key, "home"):
                        lines_map[line]["home"] = price
                    elif nl in (away_key, "away"):
                        lines_map[line]["away"] = price
                complete = [v for v in lines_map.values() if v.get("home") and v.get("away")]
                if complete:
                    spreads_bk[bk_name] = sorted(complete, key=lambda x: abs(x["line"]))

    if not h2h_bk:
        return {}

    # ── Best prices across all bookmakers ─────────────────────────────
    best_h2h = {
        "home": max((v["home"] for v in h2h_bk.values()), default=0),
        "draw": max((v["draw"] for v in h2h_bk.values()), default=0),
        "away": max((v["away"] for v in h2h_bk.values()), default=0),
    }

    best_totals: Dict[str, float] = {}
    for bk_data in totals_bk.values():
        for k, v in bk_data.items():
            if v and v > best_totals.get(k, 0):
                best_totals[k] = v

    # Best AH: best price at each line across all bookmakers
    all_ah_lines: Dict[float, Dict] = {}
    for bk_lines in spreads_bk.values():
        for entry in bk_lines:
            line = entry["line"]
            if line not in all_ah_lines:
                all_ah_lines[line] = {"line": line}
            if entry.get("home", 0) > all_ah_lines[line].get("home", 0):
                all_ah_lines[line]["home"] = entry["home"]
            if entry.get("away", 0) > all_ah_lines[line].get("away", 0):
                all_ah_lines[line]["away"] = entry["away"]
    best_ah = sorted(
        [v for v in all_ah_lines.values() if v.get("home") and v.get("away")],
        key=lambda x: abs(x["line"]),
    )

    # ── Derived: Double Chance + Draw No Bet ──────────────────────────
    derived: Dict[str, Any] = {}
    bh, bd, ba = best_h2h["home"], best_h2h["draw"], best_h2h["away"]
    if bh > 1 and bd > 1 and ba > 1:
        ph, pd, pa = 1 / bh, 1 / bd, 1 / ba
        tot = ph + pd + pa
        vph, vpd, vpa = ph / tot, pd / tot, pa / tot

        def _dc(p: float) -> Optional[float]:
            return round(1 / p, 3) if 0 < p < 1 else None

        derived["dc_1x"]     = _dc(vph + vpd)
        derived["dc_x2"]     = _dc(vpd + vpa)
        derived["dc_12"]     = _dc(vph + vpa)
        dn_tot = vph + vpa
        if dn_tot > 0:
            derived["dnb_home"] = round(1 / (vph / dn_tot), 3)
            derived["dnb_away"] = round(1 / (vpa / dn_tot), 3)
        derived["vig_free"]  = {
            "home": round(vph, 4),
            "draw": round(vpd, 4),
            "away": round(vpa, 4),
        }
        derived["overround"] = round(tot - 1.0, 5)

    return {
        "event_id":     event.get("id", ""),
        "home_team":    home,
        "away_team":    away,
        "kickoff":      event.get("commence_time", ""),
        "n_bookmakers": len(h2h_bk),
        "h2h": {
            "bookmakers": h2h_bk,
            "best":       best_h2h,
        },
        "totals": {
            "bookmakers": totals_bk,
            "best":       best_totals,
        },
        "spreads": {
            "bookmakers": spreads_bk,
            "best":       best_ah,
        },
        "derived": derived,
    }


# ── Arbitrage detectors ───────────────────────────────────────────────

def _detect_1x2_arbitrage(event_odds: dict, min_profit_pct: float) -> Optional[dict]:
    bk_odds = event_odds.get("bookmakers", {})
    if len(bk_odds) < 2:
        return None

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

    stake = 100
    return {
        "home_team":         event_odds["home_team"],
        "away_team":         event_odds["away_team"],
        "kickoff":           event_odds.get("kickoff", ""),
        "market_type":       "1x2",
        "profit_pct":        profit_pct,
        "arb_sum":           round(arb_sum, 6),
        "legs": {
            "home": {"bookmaker": best_home_bk, "odds": best_home,
                     "stake": round(stake / (best_home * arb_sum), 2)},
            "draw": {"bookmaker": best_draw_bk, "odds": best_draw,
                     "stake": round(stake / (best_draw * arb_sum), 2)},
            "away": {"bookmaker": best_away_bk, "odds": best_away,
                     "stake": round(stake / (best_away * arb_sum), 2)},
        },
        "guaranteed_profit": round(stake * profit_pct / 100, 2),
    }


def _detect_ou_arbitrage(
    full_event: dict,
    line_suffix: str,
    min_profit_pct: float,
) -> Optional[dict]:
    """Detect Over/Under arbitrage at a given line (e.g. '25' for 2.5)."""
    totals_bk = full_event.get("totals", {}).get("bookmakers", {})
    if len(totals_bk) < 2:
        return None

    over_key  = f"over_{line_suffix}"
    under_key = f"under_{line_suffix}"
    line_label = f"{line_suffix[0]}.{line_suffix[1]}"

    overs  = [(bk, v[over_key])  for bk, v in totals_bk.items() if v.get(over_key,  0) > 1.01]
    unders = [(bk, v[under_key]) for bk, v in totals_bk.items() if v.get(under_key, 0) > 1.01]
    if not overs or not unders:
        return None

    best_over_bk, best_over   = max(overs,  key=lambda x: x[1])
    best_under_bk, best_under = max(unders, key=lambda x: x[1])

    arb_sum = (1 / best_over) + (1 / best_under)
    if arb_sum >= 1.0:
        return None
    profit_pct = round((1 - arb_sum) / arb_sum * 100, 3)
    if profit_pct < min_profit_pct:
        return None

    stake = 100
    return {
        "home_team":         full_event["home_team"],
        "away_team":         full_event["away_team"],
        "kickoff":           full_event.get("kickoff", ""),
        "market_type":       f"over_under_{line_suffix}",
        "profit_pct":        profit_pct,
        "arb_sum":           round(arb_sum, 6),
        "legs": {
            f"over_{line_label}":  {"bookmaker": best_over_bk,  "odds": best_over,
                                    "stake": round(stake / (best_over  * arb_sum), 2)},
            f"under_{line_label}": {"bookmaker": best_under_bk, "odds": best_under,
                                    "stake": round(stake / (best_under * arb_sum), 2)},
        },
        "guaranteed_profit": round(stake * profit_pct / 100, 2),
    }


# ══════════════════════════════════════════════════════════════════════
# Endpoints
# ══════════════════════════════════════════════════════════════════════

@router.get("/compare")
async def compare_odds(
    league:  str           = Query(default="premier_league"),
    api_key: Optional[str] = Query(default=None),
):
    """
    Multi-bookmaker 1X2 odds comparison for upcoming fixtures in a league.
    """
    _verify_key(api_key)
    odds_key = os.getenv("ODDS_API_KEY", "") or os.getenv("THE_ODDS_API_KEY", "")
    if not odds_key:
        raise HTTPException(status_code=503, detail="ODDS_API_KEY not configured")

    sport  = SPORT_MAP.get(league, "soccer_epl")
    events, data_status, requests_remaining = await _fetch_odds(sport, odds_key, markets="h2h")

    comparison = []
    for ev in events[:20]:
        parsed = _extract_h2h_odds(ev)
        if parsed:
            comparison.append(parsed)

    _audit("odds_compare", {"league": league, "events_found": len(comparison), "status": data_status})

    return {
        "league":             league,
        "sport_key":          sport,
        "events":             comparison,
        "total":              len(comparison),
        "data_status":        data_status,
        "requests_remaining": requests_remaining,
        "fetched_at":         datetime.now(timezone.utc).isoformat(),
    }


@router.get("/markets")
async def all_markets(
    league:  str           = Query(
        default="premier_league",
        description="League key e.g. premier_league, la_liga, bundesliga",
    ),
    api_key: Optional[str] = Query(default=None),
):
    """
    Full multi-market odds for every upcoming fixture in a league.

    Returns per event:
    - **1X2** (h2h): per-bookmaker odds + best price
    - **Over/Under** at 1.5, 2.5, 3.5, 4.5 goals: per-bookmaker + best
    - **Asian Handicap** (spreads): all available lines + best price
    - **Double Chance** 1X / X2 / 12: derived from vig-free h2h
    - **Draw No Bet** Home / Away: derived from vig-free h2h
    - **Overround**: bookmaker margin %
    - **Vig-free probabilities**: sharp market probabilities
    """
    _verify_key(api_key)
    odds_key = os.getenv("ODDS_API_KEY", "") or os.getenv("THE_ODDS_API_KEY", "")
    if not odds_key:
        raise HTTPException(status_code=503, detail="ODDS_API_KEY not configured")

    sport  = SPORT_MAP.get(league, "soccer_epl")
    events, data_status, requests_remaining = await _fetch_odds(sport, odds_key, markets=ALL_MARKETS)

    market_data = []
    for ev in events[:20]:
        parsed = _extract_all_markets(ev)
        if parsed:
            market_data.append(parsed)

    _audit("all_markets", {"league": league, "events_found": len(market_data), "status": data_status})

    return {
        "league":              league,
        "sport_key":           sport,
        "markets_fetched":     ALL_MARKETS.split(","),
        "markets_derived":     ["double_chance", "draw_no_bet"],
        "events":              market_data,
        "total":               len(market_data),
        "data_status":         data_status,
        "requests_remaining":  requests_remaining,
        "fetched_at":          datetime.now(timezone.utc).isoformat(),
    }


@router.get("/markets/event/{event_id}")
async def event_markets(
    event_id: str,
    sport:    str           = Query(
        default="soccer_epl",
        description="Odds API sport key e.g. soccer_epl",
    ),
    api_key:  Optional[str] = Query(default=None),
):
    """
    All markets for a specific event by its Odds API event_id.
    Returns full bookmaker data plus all derived markets.
    """
    _verify_key(api_key)
    odds_key = os.getenv("ODDS_API_KEY", "") or os.getenv("THE_ODDS_API_KEY", "")
    if not odds_key:
        raise HTTPException(status_code=503, detail="ODDS_API_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=14) as client:
            r = await client.get(
                f"https://api.the-odds-api.com/v4/sports/{sport}/events/{event_id}/odds",
                params={
                    "apiKey":     odds_key,
                    "regions":    "eu,uk",
                    "markets":    ALL_MARKETS,
                    "oddsFormat": "decimal",
                },
            )
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Event not found")
        if r.status_code != 200:
            raise HTTPException(status_code=503, detail=f"Odds API error {r.status_code}")
        event_data = r.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Odds API request failed: {e}")

    parsed = _extract_all_markets(event_data)
    if not parsed:
        raise HTTPException(status_code=422, detail="Could not extract odds from event data")

    _audit("event_markets", {"event_id": event_id, "sport": sport})

    return {
        "event_id":   event_id,
        "sport":      sport,
        "markets":    parsed,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/arbitrage")
async def scan_arbitrage(
    league:         str           = Query(default="premier_league"),
    min_profit_pct: float         = Query(default=0.5,  description="Minimum profit % to report"),
    include_totals: bool          = Query(default=True,  description="Scan O/U 1.5/2.5/3.5 markets too"),
    api_key:        Optional[str] = Query(default=None),
):
    """
    Scan for arbitrage opportunities across bookmakers.
    Covers 1X2 and (optionally) Over/Under markets at 1.5, 2.5, and 3.5 goals.
    """
    _verify_key(api_key)
    odds_key = os.getenv("ODDS_API_KEY", "") or os.getenv("THE_ODDS_API_KEY", "")
    if not odds_key:
        raise HTTPException(status_code=503, detail="ODDS_API_KEY not configured")

    sport   = SPORT_MAP.get(league, "soccer_epl")
    markets = ALL_MARKETS if include_totals else "h2h"
    events, data_status, requests_remaining = await _fetch_odds(sport, odds_key, markets=markets)

    opportunities = []
    scanned = 0

    for ev in events:
        h2h_parsed = _extract_h2h_odds(ev)
        if h2h_parsed:
            scanned += 1
            arb = _detect_1x2_arbitrage(h2h_parsed, min_profit_pct)
            if arb:
                opportunities.append(arb)

        if include_totals:
            full_parsed = _extract_all_markets(ev)
            if full_parsed:
                for line in ("15", "25", "35"):
                    arb_ou = _detect_ou_arbitrage(full_parsed, line, min_profit_pct)
                    if arb_ou:
                        opportunities.append(arb_ou)

    opportunities.sort(key=lambda x: x["profit_pct"], reverse=True)

    _audit("arbitrage_scan", {
        "league":          league,
        "scanned":         scanned,
        "found":           len(opportunities),
        "include_totals":  include_totals,
        "status":          data_status,
    })

    return {
        "league":             league,
        "sport_key":          sport,
        "scanned":            scanned,
        "opportunities":      opportunities,
        "total_found":        len(opportunities),
        "min_profit_pct":     min_profit_pct,
        "markets_scanned":    markets.split(","),
        "data_status":        data_status,
        "requests_remaining": requests_remaining,
        "fetched_at":         datetime.now(timezone.utc).isoformat(),
    }


# ── Injury / context adjustments ─────────────────────────────────────

class InjuryNote(BaseModel):
    team:   str
    player: str
    status: str   # "out" | "doubtful" | "returning"
    note:   str = ""


_injury_store: List[dict] = []


@router.post("/injuries")
async def add_injury(note: InjuryNote, api_key: Optional[str] = Query(default=None)):
    """Add a manual injury / team news note."""
    _verify_key(api_key)
    entry = {
        **note.dict(),
        "id":       str(uuid.uuid4())[:8],
        "added_at": datetime.now(timezone.utc).isoformat(),
    }
    _injury_store.append(entry)
    _audit("injury_added", {"team": note.team, "player": note.player, "status": note.status})
    return {"added": entry}


@router.get("/injuries")
async def get_injuries(
    team:    Optional[str] = Query(None),
    api_key: Optional[str] = Query(default=None),
):
    """Return all injury notes, optionally filtered by team."""
    _verify_key(api_key)
    results = (
        _injury_store
        if not team
        else [i for i in _injury_store if team.lower() in i["team"].lower()]
    )
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
    limit:   int           = Query(default=50, le=200),
    api_key: Optional[str] = Query(default=None),
):
    """Return the system audit log."""
    _verify_key(api_key)
    return {
        "log":   list(reversed(_audit_log))[:limit],
        "total": len(_audit_log),
    }
