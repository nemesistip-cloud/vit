# app/modules/inplay/routes.py
"""
Live In-Play Prediction Markets — Phase VIII

Real-time prediction markets backed exclusively by verified external providers (Football-Data.org,
iSports) and persistent database matches.

STRICT GUARANTEES:
1. Zero synthetic, fake, simulated, or demo live matches are ever created or served.
2. If zero matches are live, returns an empty list for live matches and provides verified upcoming fixtures.
3. In-play markets (1X2, Next Goal, Total Goals, BTTS) are strictly derived from real match state
   and verified provider odds, or marked as unavailable/suspended.
4. Full provenance tracking (provider name, provider match ID, ingestion timestamp, odds timestamp).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.db.models import User
from app.services.live_match_ingestion import (
    live_ingestion_service,
    CanonicalLiveMatch,
    LiveMarket,
    LiveSelection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inplay", tags=["In-Play"])

# user bets: user_id → [ bet ]
_BETS: Dict[int, List[dict]] = {}


# ── Market derivation from verified match state ───────────────────────────────

def _derive_live_markets(match: CanonicalLiveMatch) -> List[dict]:
    """
    Derive 1X2, Next Goal, Total Goals, and BTTS markets from real match state and odds.
    If market odds cannot be reliably derived from provider data or match state, mark as unavailable.
    """
    now = time.time()
    markets: List[dict] = []

    is_open = match.status == "LIVE" and match.markets_available and match.minute < 88

    # 1. Match Result (1X2)
    # Check if raw provider odds exist
    raw_odds = match.raw_odds or {}
    h_odds = raw_odds.get("home") or raw_odds.get("1")
    d_odds = raw_odds.get("draw") or raw_odds.get("X")
    a_odds = raw_odds.get("away") or raw_odds.get("2")

    # If match is live and no raw odds are provided, mark market status accordingly
    mk_1x2_status = "open" if (is_open and h_odds and d_odds and a_odds) else ("suspended" if is_open else "closed")

    selections_1x2 = []
    if h_odds and d_odds and a_odds:
        selections_1x2 = [
            {"id": "home", "label": match.home, "odds": round(float(h_odds), 2), "source": match.provider},
            {"id": "draw", "label": "Draw", "odds": round(float(d_odds), 2), "source": match.provider},
            {"id": "away", "label": match.away, "odds": round(float(a_odds), 2), "source": match.provider},
        ]
    else:
        # Mark selections as unavailable if no provider odds
        selections_1x2 = [
            {"id": "home", "label": match.home, "odds": 0.0, "source": "unavailable"},
            {"id": "draw", "label": "Draw", "odds": 0.0, "source": "unavailable"},
            {"id": "away", "label": match.away, "odds": 0.0, "source": "unavailable"},
        ]
        if is_open:
            mk_1x2_status = "unavailable"

    markets.append({
        "id": f"{match.id}-match_result",
        "match_id": match.id,
        "type": "match_result",
        "status": mk_1x2_status,
        "home": match.home,
        "away": match.away,
        "selections": selections_1x2,
        "updated_at": now,
        "odds_source": match.provider if (h_odds and d_odds and a_odds) else "none",
        "odds_timestamp": match.source_timestamp,
    })

    # 2. Next Goal Market
    ng_status = "open" if (is_open and match.minute < 85) else ("suspended" if is_open else "closed")
    ng_odds = raw_odds.get("next_goal", {})
    markets.append({
        "id": f"{match.id}-next_goal",
        "match_id": match.id,
        "type": "next_goal",
        "status": ng_status if ng_odds else "unavailable",
        "home": match.home,
        "away": match.away,
        "selections": [
            {"id": "home_next", "label": f"{match.home} next", "odds": round(float(ng_odds.get("home", 0.0)), 2), "source": match.provider if ng_odds else "unavailable"},
            {"id": "away_next", "label": f"{match.away} next", "odds": round(float(ng_odds.get("away", 0.0)), 2), "source": match.provider if ng_odds else "unavailable"},
            {"id": "no_goal", "label": "No more goals", "odds": round(float(ng_odds.get("none", 0.0)), 2), "source": match.provider if ng_odds else "unavailable"},
        ],
        "updated_at": now,
        "odds_source": match.provider if ng_odds else "none",
        "odds_timestamp": match.source_timestamp,
    })

    # 3. Total Goals (Over/Under)
    curr_goals = match.home_score + match.away_score
    line = curr_goals + 0.5
    ou_odds = raw_odds.get("total_goals", {})
    markets.append({
        "id": f"{match.id}-total_goals",
        "match_id": match.id,
        "type": "total_goals",
        "status": "open" if (is_open and ou_odds) else ("unavailable" if is_open else "closed"),
        "home": match.home,
        "away": match.away,
        "selections": [
            {"id": "over", "label": f"Over {line}", "odds": round(float(ou_odds.get("over", 0.0)), 2), "source": match.provider if ou_odds else "unavailable"},
            {"id": "under", "label": f"Under {line}", "odds": round(float(ou_odds.get("under", 0.0)), 2), "source": match.provider if ou_odds else "unavailable"},
        ],
        "updated_at": now,
        "odds_source": match.provider if ou_odds else "none",
        "odds_timestamp": match.source_timestamp,
    })

    # 4. Both Teams to Score (BTTS)
    btts_odds = raw_odds.get("btts", {})
    markets.append({
        "id": f"{match.id}-btts",
        "match_id": match.id,
        "type": "btts",
        "status": "open" if (is_open and btts_odds) else ("unavailable" if is_open else "closed"),
        "home": match.home,
        "away": match.away,
        "selections": [
            {"id": "yes", "label": "Both To Score", "odds": round(float(btts_odds.get("yes", 0.0)), 2), "source": match.provider if btts_odds else "unavailable"},
            {"id": "no", "label": "Not Both To Score", "odds": round(float(btts_odds.get("no", 0.0)), 2), "source": match.provider if btts_odds else "unavailable"},
        ],
        "updated_at": now,
        "odds_source": match.provider if btts_odds else "none",
        "odds_timestamp": match.source_timestamp,
    })

    return markets


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class PlaceBet(BaseModel):
    market_id: str
    selection_id: str
    stake: float = Field(..., gt=0.5, description="Stake in VIT (min 0.5)")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/matches", summary="Verified live matches with open markets")
async def live_matches():
    res = await live_ingestion_service.fetch_and_normalize_all()
    live_list = res.get("live", [])
    upcoming_list = res.get("upcoming", [])

    return {
        "matches": [m.dict() for m in live_list],
        "upcoming": [m.dict() for m in upcoming_list],
        "total_live": len(live_list),
        "total": len(live_list),
        "total_upcoming": len(upcoming_list),
        "is_live_available": len(live_list) > 0,
        "timestamp": time.time(),
    }


@router.get("/matches/{match_id}/markets", summary="All markets for a specific live/upcoming match")
async def get_match_markets(match_id: str):
    res = await live_ingestion_service.fetch_and_normalize_all()
    all_matches = res.get("live", []) + res.get("upcoming", [])

    match = next((m for m in all_matches if m.id == match_id), None)
    if not match:
        raise HTTPException(404, f"Match '{match_id}' not found in live/upcoming feed")

    markets = _derive_live_markets(match)
    return {
        "match_id": match_id,
        "provider": match.provider,
        "provider_match_id": match.provider_match_id,
        "last_updated": match.last_successful_update,
        "markets": markets,
    }


@router.get("/markets/{market_id}", summary="Get a specific market details")
async def get_market(market_id: str):
    res = await live_ingestion_service.fetch_and_normalize_all()
    all_matches = res.get("live", []) + res.get("upcoming", [])

    target_match = None
    for m in all_matches:
        if market_id.startswith(m.id):
            target_match = m
            break

    if not target_match:
        raise HTTPException(404, f"Market '{market_id}' not found")

    markets = _derive_live_markets(target_match)
    mk = next((m for m in markets if m["id"] == market_id), None)
    if not mk:
        raise HTTPException(404, f"Market '{market_id}' not found")

    return mk


@router.post("/bet", summary="Place an in-play bet on verified live markets")
async def place_bet(body: PlaceBet, me: User = Depends(get_current_user)):
    res = await live_ingestion_service.fetch_and_normalize_all()
    all_matches = res.get("live", [])

    target_match = None
    target_market = None
    for m in all_matches:
        if body.market_id.startswith(m.id):
            target_match = m
            mk_list = _derive_live_markets(m)
            target_market = next((mk for mk in mk_list if mk["id"] == body.market_id), None)
            break

    if not target_match or not target_market:
        raise HTTPException(404, "Live market not found or match is no longer live")

    if target_market["status"] != "open":
        raise HTTPException(400, f"Market is currently {target_market['status']}")

    sel = next((s for s in target_market["selections"] if s["id"] == body.selection_id), None)
    if not sel or sel.get("odds", 0) <= 1.0:
        raise HTTPException(400, "Selection unavailable or has invalid odds")

    bet = {
        "id": str(uuid.uuid4()),
        "user_id": me.id,
        "match_id": target_match.id,
        "market_id": body.market_id,
        "selection_id": body.selection_id,
        "selection": sel["label"],
        "odds": sel["odds"],
        "stake": body.stake,
        "potential_win": round(body.stake * sel["odds"], 4),
        "placed_at": time.time(),
        "status": "pending",
        "provider": target_match.provider,
        "provider_match_id": target_match.provider_match_id,
    }

    _BETS.setdefault(me.id, []).append(bet)
    logger.info("inplay:bet user=%s market=%s stake=%.2f provider=%s", me.id, body.market_id, body.stake, target_match.provider)

    return {"ok": True, "bet": bet}


@router.get("/my-bets", summary="My in-play bets")
async def my_bets(
    status: Optional[str] = Query(None, description="pending | settled | void"),
    me: User = Depends(get_current_user),
):
    bets = _BETS.get(me.id, [])
    if status:
        bets = [b for b in bets if b["status"] == status]
    return {"bets": bets, "total": len(bets)}


@router.get("/stats", summary="In-play platform stats")
async def inplay_stats():
    res = await live_ingestion_service.fetch_and_normalize_all()
    live_matches = res.get("live", [])

    total_open_markets = 0
    for m in live_matches:
        mks = _derive_live_markets(m)
        total_open_markets += sum(1 for mk in mks if mk["status"] == "open")

    total_bets = sum(len(v) for v in _BETS.values())
    total_stake = sum(b["stake"] for bets in _BETS.values() for b in bets)

    return {
        "live_matches": len(live_matches),
        "open_markets": total_open_markets,
        "total_bets": total_bets,
        "total_staked": round(total_stake, 2),
        "last_sync": time.time(),
    }
