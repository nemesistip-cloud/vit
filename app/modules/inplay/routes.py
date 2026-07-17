# app/modules/inplay/routes.py
"""
Live In-Play Prediction Markets — Phase VIII
Real-time markets for ongoing matches: bet on next scorer, HT/FT,
corners, cards, and more. Markets open/close automatically with
match clock. Odds update on a simulated tick (replace with live
feed adapter in production).
"""

from __future__ import annotations

import logging
import math
import random
import time
import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inplay", tags=["In-Play"])

# ── Synthetic live match store ────────────────────────────────────────────────
_LIVE_MATCHES: List[dict] = [
    {
        "id":        "lm-001",
        "home":      "Manchester City",
        "away":      "Arsenal",
        "league":    "Premier League",
        "minute":    67,
        "home_score": 1,
        "away_score": 1,
        "status":    "in_progress",
        "period":    "second_half",
        "started_at": time.time() - 67 * 60,
    },
    {
        "id":        "lm-002",
        "home":      "Real Madrid",
        "away":      "Barcelona",
        "league":    "La Liga",
        "minute":    38,
        "home_score": 2,
        "away_score": 0,
        "status":    "in_progress",
        "period":    "first_half",
        "started_at": time.time() - 38 * 60,
    },
    {
        "id":        "lm-003",
        "home":      "Bayern Munich",
        "away":      "Borussia Dortmund",
        "league":    "Bundesliga",
        "minute":    82,
        "home_score": 3,
        "away_score": 2,
        "status":    "in_progress",
        "period":    "second_half",
        "started_at": time.time() - 82 * 60,
    },
]

# market_id → market dict
_MARKETS: Dict[str, dict] = {}

# user bets: user_id → [ bet ]
_BETS: Dict[int, List[dict]] = {}


def _init_markets():
    """Seed markets for live matches."""
    for m in _LIVE_MATCHES:
        mins_left = 90 - m["minute"]
        for market_type in ["match_result", "next_goal", "total_goals", "btts"]:
            mk_id = f"{m['id']}-{market_type}"
            if mk_id in _MARKETS:
                continue
            _MARKETS[mk_id] = {
                "id":           mk_id,
                "match_id":     m["id"],
                "type":         market_type,
                "status":       "open" if mins_left > 2 else "suspended",
                "home":         m["home"],
                "away":         m["away"],
                "selections":   _build_selections(m, market_type),
                "updated_at":   time.time(),
            }


def _build_selections(match: dict, market_type: str) -> List[dict]:
    h, a = match["home_score"], match["away_score"]
    mins_left = max(1, 90 - match["minute"])
    # Very rough in-play odds
    if market_type == "match_result":
        base_h = 1.5 + (a - h) * 0.3
        base_d = 3.2
        base_a = 1.5 + (h - a) * 0.3
        return [
            {"label": match["home"], "odds": round(max(1.05, base_h + random.uniform(-0.1, 0.1)), 2), "id": "home"},
            {"label": "Draw",        "odds": round(max(1.05, base_d + random.uniform(-0.2, 0.2)), 2), "id": "draw"},
            {"label": match["away"], "odds": round(max(1.05, base_a + random.uniform(-0.1, 0.1)), 2), "id": "away"},
        ]
    elif market_type == "next_goal":
        return [
            {"label": f"{match['home']} next",  "odds": round(1.8 + random.uniform(-0.2, 0.2), 2), "id": "home_next"},
            {"label": f"{match['away']} next",  "odds": round(2.1 + random.uniform(-0.2, 0.2), 2), "id": "away_next"},
            {"label": "No more goals",          "odds": round(2.9 + random.uniform(-0.3, 0.3), 2), "id": "no_goal"},
        ]
    elif market_type == "total_goals":
        current = h + a
        return [
            {"label": f"Over {current + 0.5}",  "odds": round(1.65 + random.uniform(-0.15, 0.15), 2), "id": "over"},
            {"label": f"Under {current + 0.5}", "odds": round(2.25 + random.uniform(-0.15, 0.15), 2), "id": "under"},
        ]
    else:  # btts
        return [
            {"label": "Both To Score",      "odds": round(1.72 + random.uniform(-0.1, 0.1), 2), "id": "yes"},
            {"label": "Not Both To Score",  "odds": round(2.05 + random.uniform(-0.1, 0.1), 2), "id": "no"},
        ]


_init_markets()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class PlaceBet(BaseModel):
    market_id:    str
    selection_id: str
    stake:        float = Field(..., gt=0.5, description="Stake in VIT (min 0.5)")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/matches", summary="Live matches with open markets")
async def live_matches():
    # Tick match minutes forward (demo)
    for m in _LIVE_MATCHES:
        elapsed = int((time.time() - m["started_at"]) / 60)
        m["minute"] = min(90, elapsed)
        if m["minute"] >= 90:
            m["status"] = "finished"
    active = [m for m in _LIVE_MATCHES if m["status"] == "in_progress"]
    return {"matches": active, "total": len(active)}


@router.get("/matches/{match_id}/markets", summary="All markets for a live match")
async def get_match_markets(match_id: str):
    markets = [m for m in _MARKETS.values() if m["match_id"] == match_id]
    if not markets:
        raise HTTPException(404, f"No markets for match '{match_id}'")
    # Refresh odds on every read
    for mk in markets:
        match = next((m for m in _LIVE_MATCHES if m["id"] == match_id), None)
        if match:
            mk["selections"] = _build_selections(match, mk["type"])
            mk["updated_at"] = time.time()
    return {"match_id": match_id, "markets": markets}


@router.get("/markets/{market_id}", summary="Get a specific market")
async def get_market(market_id: str):
    mk = _MARKETS.get(market_id)
    if not mk:
        raise HTTPException(404, "Market not found")
    match = next((m for m in _LIVE_MATCHES if m["id"] == mk["match_id"]), None)
    if match:
        mk["selections"] = _build_selections(match, mk["type"])
        mk["updated_at"] = time.time()
    return mk


@router.post("/bet", summary="Place an in-play bet")
async def place_bet(body: PlaceBet, me: User = Depends(get_current_user)):
    mk = _MARKETS.get(body.market_id)
    if not mk:
        raise HTTPException(404, "Market not found")
    if mk["status"] != "open":
        raise HTTPException(400, f"Market is {mk['status']}")
    sel = next((s for s in mk["selections"] if s["id"] == body.selection_id), None)
    if not sel:
        raise HTTPException(400, "Selection not found in this market")

    bet = {
        "id":           str(uuid.uuid4()),
        "user_id":      me.id,
        "market_id":    body.market_id,
        "selection_id": body.selection_id,
        "selection":    sel["label"],
        "odds":         sel["odds"],
        "stake":        body.stake,
        "potential_win": round(body.stake * sel["odds"], 4),
        "placed_at":    time.time(),
        "status":       "pending",
    }
    _BETS.setdefault(me.id, []).append(bet)
    logger.info("inplay:bet user=%s market=%s stake=%.2f", me.id, body.market_id, body.stake)
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
    total_bets  = sum(len(v) for v in _BETS.values())
    total_stake = sum(b["stake"] for bets in _BETS.values() for b in bets)
    return {
        "live_matches":  len([m for m in _LIVE_MATCHES if m["status"] == "in_progress"]),
        "open_markets":  len([mk for mk in _MARKETS.values() if mk["status"] == "open"]),
        "total_bets":    total_bets,
        "total_staked":  round(total_stake, 2),
    }
