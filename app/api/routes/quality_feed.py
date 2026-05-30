"""app/api/routes/quality_feed.py — Quality Bet Feed + Value Intelligence Feed.

Derives curated high-edge bets and VIT-scored predictions from the DB.
No global auth dependency — all endpoints are public (no API key required).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Match, Prediction

router = APIRouter(prefix="/quality-feed", tags=["quality-feed"])

RISK_MIN_EDGE = {
    "conservative": 0.06,
    "balanced":     0.03,
    "aggressive":   0.01,
}

RISK_MIN_CONFIDENCE = {
    "conservative": 0.60,
    "balanced":     0.45,
    "aggressive":   0.30,
}


def _kelly(prob: float, odds: float) -> float:
    if odds <= 1 or prob <= 0:
        return 0.0
    b = odds - 1.0
    q = 1 - prob
    k = (b * prob - q) / b
    return max(0.0, round(k * 100, 2))


def _ev(prob: float, odds: float) -> float:
    return round((prob * (odds - 1) - (1 - prob)) * 100, 2)


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/curated")
async def curated_bets(
    risk_profile: str = Query("balanced"),
    min_edge: float = Query(0.02),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Return top +EV predictions — includes both upcoming and recently settled matches."""
    rp = risk_profile.lower() if risk_profile.lower() in RISK_MIN_EDGE else "balanced"
    edge_floor  = max(min_edge, RISK_MIN_EDGE[rp])
    conf_floor  = RISK_MIN_CONFIDENCE[rp]

    now = _now_naive()
    # Include matches from 7 days ago (to show recent results) to 14 days ahead
    window_start = now - timedelta(days=7)
    window_end   = now + timedelta(days=14)

    rows = (await db.execute(
        select(Match, Prediction)
        .join(Prediction, Match.id == Prediction.match_id)
        .where(
            Match.kickoff_time >= window_start,
            Match.kickoff_time <= window_end,
        )
        .order_by(desc(Prediction.timestamp))
        .limit(500)
    )).all()

    seen: set = set()
    items = []
    for match, pred in rows:
        if match.id in seen:
            continue
        seen.add(match.id)

        conf = float(pred.confidence or 0)
        if conf > 1:
            conf /= 100
        if conf < conf_floor:
            continue

        # Use vig-free edge when available; raw_edge can be negative (model underperformed)
        vig_edge = pred.vig_free_edge
        raw_edge = pred.raw_edge
        if vig_edge is not None:
            edge = float(vig_edge)
        elif raw_edge is not None and float(raw_edge) > 0:
            edge = float(raw_edge)
        else:
            edge = 0.0

        best_side = pred.bet_side or "home"
        home_p = float(pred.home_prob or 0.33)
        draw_p = float(pred.draw_prob or 0.25)
        away_p = float(pred.away_prob or 0.33)
        total  = home_p + draw_p + away_p or 1.0
        home_p /= total; draw_p /= total; away_p /= total
        prob_map = {"home": home_p, "draw": draw_p, "away": away_p}
        best_prob = prob_map.get(best_side, home_p)

        # Pass if edge > floor OR high model confidence
        if edge < edge_floor and best_prob < 0.52:
            continue

        raw_odds = pred.entry_odds
        if not raw_odds or raw_odds <= 1.0:
            raw_odds = round(1 / max(best_prob, 0.05), 2)

        kelly_pct = _kelly(best_prob, raw_odds)
        ev = _ev(best_prob, raw_odds)

        side_label = {
            "home": match.home_team,
            "away": match.away_team,
            "draw": "Draw",
        }.get(best_side, best_side.upper())

        rationale_parts = []
        if edge > 0.03:
            rationale_parts.append(f"{edge * 100:.1f}% vig-free edge")
        if conf > 0.60:
            rationale_parts.append(f"{conf * 100:.0f}% ensemble confidence")
        if best_prob > 0.55:
            rationale_parts.append(f"{best_prob * 100:.0f}% model probability")
        rationale = " · ".join(rationale_parts) if rationale_parts else "Model consensus positive"

        items.append({
            "id": pred.id,
            "match_id": match.id,
            "match": f"{match.home_team} vs {match.away_team}",
            "league": (match.league or "").replace("_", " ").title(),
            "side": side_label,
            "bet_side": best_side,
            "odds": round(raw_odds, 2),
            "edge": round(edge * 100, 2),
            "confidence": round(conf * 100, 1),
            "expected_value": ev,
            "kelly_pct": kelly_pct,
            "suggested_stake_pct": min(kelly_pct * 0.25, 5.0),
            "rationale": rationale,
            "home_prob": round(home_p * 100, 1),
            "draw_prob": round(draw_p * 100, 1),
            "away_prob": round(away_p * 100, 1),
            "kickoff": match.kickoff_time.isoformat() if match.kickoff_time else None,
            "settled": match.actual_outcome is not None,
            "actual_outcome": match.actual_outcome,
        })

        if len(items) >= limit:
            break

    items.sort(key=lambda x: (x["edge"] + x["confidence"] * 0.3), reverse=True)

    return {
        "risk_profile": rp,
        "total": len(items),
        "items": items,
    }


@router.get("/value-intelligence")
async def value_intelligence(
    min_vit: float = Query(0, ge=0),
    tier: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    VIT Value Intelligence Feed.

    Scores every prediction:
      VIT = 0.35*(edge_score) + 0.30*(consensus_score) + 0.25*(confidence) + 0.10*(recency_score)
    Tier: platinum>=70 | gold>=50 | silver>=35 | bronze>=20 | standard<20
    Includes matches from the last 7 days and upcoming 14 days.
    """
    now = _now_naive()
    window_start = now - timedelta(days=7)
    window_end   = now + timedelta(days=14)

    rows = (await db.execute(
        select(Match, Prediction)
        .join(Prediction, Match.id == Prediction.match_id)
        .where(
            Match.kickoff_time >= window_start,
            Match.kickoff_time <= window_end,
        )
        .order_by(desc(Prediction.timestamp))
        .limit(500)
    )).all()

    seen: set = set()
    scored = []

    for match, pred in rows:
        if match.id in seen:
            continue
        seen.add(match.id)

        conf = float(pred.confidence or 0)
        if conf > 1:
            conf /= 100

        edge = pred.vig_free_edge or pred.raw_edge or 0
        edge = float(edge)

        edge_score = min(edge / 0.15, 1.0) * 100

        home_p = float(pred.home_prob or 0.33)
        draw_p = float(pred.draw_prob or 0.25)
        away_p = float(pred.away_prob or 0.33)
        total  = home_p + draw_p + away_p or 1.0
        home_p /= total; draw_p /= total; away_p /= total
        best_p = max(home_p, draw_p, away_p)
        consensus_score = min(max((best_p - 0.33) / 0.67, 0.0), 1.0) * 100

        ts = pred.timestamp.replace(tzinfo=None) if pred.timestamp and pred.timestamp.tzinfo else pred.timestamp
        age_h = (now - ts).total_seconds() / 3600 if ts else 48
        recency_score = max(0.0, 100 - age_h * 2)

        vit_score = round(
            0.35 * edge_score
            + 0.30 * consensus_score
            + 0.25 * conf * 100
            + 0.10 * recency_score,
            1,
        )

        if vit_score >= 70:
            pred_tier = "platinum"
        elif vit_score >= 50:
            pred_tier = "gold"
        elif vit_score >= 35:
            pred_tier = "silver"
        elif vit_score >= 20:
            pred_tier = "bronze"
        else:
            pred_tier = "standard"

        if vit_score < min_vit:
            continue
        if tier and tier != "all" and pred_tier != tier:
            continue

        best_side = pred.bet_side or "home"
        side_label = {
            "home": match.home_team,
            "away": match.away_team,
            "draw": "Draw",
        }.get(best_side, best_side.upper())

        raw_odds = pred.entry_odds
        if not raw_odds or raw_odds <= 1.0:
            raw_odds = round(1 / max(best_p, 0.05), 2)

        scored.append({
            "id": pred.id,
            "match_id": match.id,
            "match": f"{match.home_team} vs {match.away_team}",
            "league": (match.league or "").replace("_", " ").title(),
            "side": side_label,
            "bet_side": best_side,
            "odds": round(raw_odds, 2),
            "vit_score": vit_score,
            "tier": pred_tier,
            "edge": round(edge * 100, 2),
            "confidence": round(conf * 100, 1),
            "consensus": round(consensus_score, 1),
            "home_prob": round(home_p * 100, 1),
            "draw_prob": round(draw_p * 100, 1),
            "away_prob": round(away_p * 100, 1),
            "kickoff": match.kickoff_time.isoformat() if match.kickoff_time else None,
            "settled": match.actual_outcome is not None,
        })

        if len(scored) >= limit * 3:
            break

    scored.sort(key=lambda x: x["vit_score"], reverse=True)
    scored = scored[:limit]

    tier_counts: dict = {}
    for s in scored:
        tier_counts[s["tier"]] = tier_counts.get(s["tier"], 0) + 1

    return {
        "total": len(scored),
        "tier_counts": tier_counts,
        "predictions": scored,
    }
