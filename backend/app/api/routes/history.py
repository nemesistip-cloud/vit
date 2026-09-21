# app/api/routes/history.py
from datetime import datetime, timezone
from itertools import combinations
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, delete

from app.db.database import get_db
from app.db.models import Match, Prediction, CLVEntry
from app.api.middleware.auth import verify_api_key
from app.api.deps import get_optional_user

router = APIRouter(prefix="/history", tags=["history"])

CERTIFIED_EDGE_THRESHOLD = 0.05
HIGH_CONFIDENCE_EDGE_THRESHOLD = 0.02


def _format_prediction_row(row):
    actual = row.Match.actual_outcome
    bet = row.Prediction.bet_side

    # Derive was_correct from the prediction row first (populated on settlement),
    # then fall back to comparing bet_side vs actual_outcome directly.
    if row.Prediction.was_correct is not None:
        was_correct = row.Prediction.was_correct
    elif actual and bet:
        was_correct = bet.lower() == actual.lower()
    else:
        was_correct = None  # match not settled yet

    # Prefer settled_profit on the prediction row; fall back to CLVEntry profit
    profit = row.Prediction.settled_profit
    if profit is None and row.CLVEntry:
        profit = row.CLVEntry.profit

    home_g = row.Match.home_goals
    away_g = row.Match.away_goals
    ft_score = f"{home_g}-{away_g}" if (home_g is not None and away_g is not None) else None

    return {
        "match_id": row.Match.id,
        "home_team": row.Match.home_team,
        "away_team": row.Match.away_team,
        "league": row.Match.league,
        "kickoff_time": row.Match.kickoff_time.isoformat(),
        "home_prob": row.Prediction.home_prob,
        "draw_prob": row.Prediction.draw_prob,
        "away_prob": row.Prediction.away_prob,
        "over_25_prob": row.Prediction.over_25_prob,
        "under_25_prob": row.Prediction.under_25_prob,
        "btts_prob": row.Prediction.btts_prob,
        "no_btts_prob": row.Prediction.no_btts_prob,
        "consensus_prob": row.Prediction.consensus_prob,
        "recommended_stake": row.Prediction.recommended_stake,
        "final_ev": row.Prediction.final_ev,
        "edge": row.Prediction.vig_free_edge,
        "confidence": row.Prediction.confidence,
        "bet_side": bet,
        "entry_odds": row.Prediction.entry_odds,
        "actual_outcome": actual,
        "ft_score": ft_score,
        "home_goals": home_g,
        "away_goals": away_g,
        "was_correct": was_correct,
        "clv": row.CLVEntry.clv if row.CLVEntry else None,
        "profit": profit,
        "timestamp": row.Prediction.timestamp.isoformat()
    }


@router.get("")
async def get_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    all_users: bool = Query(
        False,
        description="When true, return predictions from every user (community feed). "
                    "When false (default), restrict to the authenticated user."
    ),
    db: AsyncSession = Depends(get_db),
    optional_user=Depends(get_optional_user),
):
    uid: int | None = getattr(optional_user, "id", None)
    apply_user_filter = (uid is not None) and (not all_users)

    # De-duplicate by (user_id, match_id) to avoid multiple signals from same person on same match
    # showing up in the same ledger view. We take the latest prediction ID.
    if apply_user_filter:
        latest_pred_sq = (
            select(Prediction.match_id, func.max(Prediction.id).label("latest_id"))
            .where(Prediction.user_id == uid)
            .group_by(Prediction.match_id)
        ).subquery()
    else:
        latest_pred_sq = (
            select(Prediction.user_id, Prediction.match_id, func.max(Prediction.id).label("latest_id"))
            .group_by(Prediction.user_id, Prediction.match_id)
        ).subquery()

    base_q = (
        select(Match, Prediction, CLVEntry)
        .join(latest_pred_sq, (Prediction.id == latest_pred_sq.c.latest_id))
        .join(Match, Match.id == Prediction.match_id)
        .outerjoin(CLVEntry, Prediction.id == CLVEntry.prediction_id)
    )

    if not apply_user_filter:
        # Community feed: hide "no-edge" rows
        base_q = base_q.where(Prediction.bet_side.isnot(None))

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(
        base_q.order_by(Match.kickoff_time.desc()).offset(offset).limit(limit)
    )).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "predictions": [_format_prediction_row(r) for r in rows],
        "scope": "user" if apply_user_filter else "community"
    }


@router.get("/results-comparison")
async def get_results_comparison(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    league: Optional[str] = Query(None),
    settled_only: bool = Query(False, description="Only return settled (result-known) predictions"),
    all_users: bool = Query(True, description="When true, show community-wide results. When false, show just mine."),
    db: AsyncSession = Depends(get_db),
    optional_user=Depends(get_optional_user),
):
    """
    Prediction vs Actual Results comparison ledger.
    De-duplicated to show only one row (the latest prediction) per match.
    """
    uid: int | None = getattr(optional_user, "id", None)
    apply_user_filter = (uid is not None) and (not all_users)

    # De-duplicate by match_id to ensure unique fixtures in this view.
    # If filtering by user, we get latest per user-match. If community, latest per match.
    if apply_user_filter:
        latest_pred_sq = (
            select(Prediction.match_id, func.max(Prediction.id).label("latest_id"))
            .where(Prediction.user_id == uid)
            .group_by(Prediction.match_id)
        ).subquery()
    else:
        latest_pred_sq = (
            select(Prediction.match_id, func.max(Prediction.id).label("latest_id"))
            .group_by(Prediction.match_id)
        ).subquery()

    base_q = (
        select(Match, Prediction, CLVEntry)
        .join(latest_pred_sq, (Match.id == latest_pred_sq.c.match_id))
        .join(Prediction, (Prediction.id == latest_pred_sq.c.latest_id))
        .outerjoin(CLVEntry, Prediction.id == CLVEntry.prediction_id)
    )

    if league:
        base_q = base_q.where(Match.league == league)

    if settled_only:
        base_q = base_q.where(Match.actual_outcome.isnot(None))

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(
        base_q.order_by(Match.kickoff_time.desc()).offset(offset).limit(limit)
    )).all()

    settled_count = 0
    correct_count = 0
    total_profit = 0.0
    gap_count = 0
    items = []

    for row in rows:
        actual = row.Match.actual_outcome
        bet = row.Prediction.bet_side

        if actual and bet:
            if row.Prediction.was_correct is not None:
                was_correct = row.Prediction.was_correct
            else:
                was_correct = bet.lower() == actual.lower()
            settled_count += 1
            if was_correct:
                correct_count += 1
            status = "WIN" if was_correct else "LOSS"
        elif actual is None:
            was_correct = None
            status = "PENDING"
            gap_count += 1
        else:
            was_correct = None
            status = "NO_BET"

        profit = row.Prediction.settled_profit
        if profit is None and row.CLVEntry:
            profit = row.CLVEntry.profit
        if profit is not None:
            total_profit += profit

        home_g = row.Match.home_goals
        away_g = row.Match.away_goals

        items.append({
            "match_id": row.Match.id,
            "fixture": f"{row.Match.home_team} vs {row.Match.away_team}",
            "home_team": row.Match.home_team,
            "away_team": row.Match.away_team,
            "league": row.Match.league,
            "kickoff_time": row.Match.kickoff_time.isoformat(),
            "match_status": row.Match.status,
            "predicted_side": bet,
            "model_probability": round(
                (row.Prediction.home_prob if bet == "home" else
                 row.Prediction.draw_prob if bet == "draw" else
                 row.Prediction.away_prob) or 0, 4
            ),
            "entry_odds": row.Prediction.entry_odds,
            "edge": row.Prediction.vig_free_edge,
            "recommended_stake": row.Prediction.recommended_stake,
            "actual_outcome": actual,
            "ft_score": f"{home_g}-{away_g}" if (home_g is not None and away_g is not None) else None,
            "was_correct": was_correct,
            "result_status": status,
            "profit": round(profit, 4) if profit is not None else None,
            "clv": row.CLVEntry.clv if row.CLVEntry else None,
            "timestamp": row.Prediction.timestamp.isoformat(),
            "has_gap": actual is None,
        })

    accuracy = round(correct_count / settled_count * 100, 2) if settled_count else 0.0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "summary": {
            "total_returned": len(items),
            "settled": settled_count,
            "pending": gap_count,
            "correct": correct_count,
            "accuracy_pct": accuracy,
            "total_profit": round(total_profit, 4),
            "gaps": gap_count,
        },
        "predictions": items,
    }



@router.get("/summary")
async def get_history_summary_alias(
    current_user=Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    """Alias for dashboard summary data to satisfy frontend /api/history/summary requests."""
    if not current_user:
        return {"total": 0, "settled": 0, "correct": 0, "accuracy_pct": 0.0, "total_profit": 0.0}

    uid = current_user.id
    from app.db.models import Prediction, Match, CLVEntry
    from sqlalchemy import select, func

    res = await db.execute(
        select(Match, Prediction, CLVEntry)
        .join(Prediction, Match.id == Prediction.match_id)
        .outerjoin(CLVEntry, Prediction.id == CLVEntry.prediction_id)
        .where(Prediction.user_id == uid)
    )
    rows = res.all()

    settled = [r for r in rows if r.Match.actual_outcome]
    wins = [r for r in settled if r.Prediction.bet_side and r.Match.actual_outcome and r.Prediction.bet_side.lower() == r.Match.actual_outcome.lower()]

    total_profit = 0.0
    for r in settled:
        if r.CLVEntry and r.CLVEntry.profit is not None:
            total_profit += float(r.CLVEntry.profit)
        elif r.Prediction.settled_profit is not None:
            total_profit += float(r.Prediction.settled_profit)

    return {
        "total": len(rows),
        "settled": len(settled),
        "correct": len(wins),
        "accuracy_pct": (len(wins) / len(settled) * 100) if settled else 0.0,
        "total_profit": round(total_profit, 2)
    }

@router.get("/{match_id}")
async def get_match_detail(match_id: int, db: AsyncSession = Depends(get_db)):
    """
    Return full match detail: prediction, model insights, market breakdowns, CLV.
    """
    result = await db.execute(
        select(Match, Prediction, CLVEntry)
        .join(Prediction, Match.id == Prediction.match_id)
        .outerjoin(CLVEntry, Prediction.id == CLVEntry.prediction_id)
        .where(Match.id == match_id)
        .order_by(Prediction.timestamp.desc())
        .limit(1)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    insights = row.Prediction.model_insights or []
    if not insights and row.Prediction.model_weights:
        weights = row.Prediction.model_weights or {}
        insights = [
            {
                "model_name": name,
                "model_type": "Unknown",
                "model_weight": float(weight or 0),
                "supported_markets": [],
                "confidence": {"1x2": 0.5, "over_under": 0.5, "btts": 0.5},
                "latency_ms": None,
                "failed": False,
            }
            for name, weight in weights.items()
        ]
    active_models = [m for m in insights if not m.get("failed")]

    def market_breakdown(market_key, prob_fields):
        models_for_market = [m for m in active_models if market_key in m.get("supported_markets", [])]
        if not models_for_market:
            return []
        breakdown = []
        for m in models_for_market:
            probs = {f: round(m.get(f, 0) * 100, 1) for f in prob_fields if m.get(f) is not None}
            conf = m.get("confidence", {}).get(
                market_key if market_key != "1x2" else "1x2", 0.5
            )
            breakdown.append({
                "model_name": m.get("model_name"),
                "model_type": m.get("model_type"),
                "weight": m.get("model_weight", 1.0),
                "probabilities": probs,
                "confidence": round(conf, 3),
                "rating": round(conf * 10, 1),
                "latency_ms": m.get("latency_ms"),
            })
        breakdown.sort(key=lambda x: x["confidence"], reverse=True)
        return breakdown

    neural_info = None
    for m in active_models:
        if m.get("home_goals_expectation") is not None:
            neural_info = {
                "model": m.get("model_name"),
                "home_xG": round(m.get("home_goals_expectation", 0), 3),
                "away_xG": round(m.get("away_goals_expectation", 0), 3),
                "dixon_coles_rho": m.get("dixon_coles_rho"),
            }
            break

    return {
        "match": {
            "id": row.Match.id,
            "home_team": row.Match.home_team,
            "away_team": row.Match.away_team,
            "league": row.Match.league,
            "kickoff_time": row.Match.kickoff_time.isoformat(),
            "status": row.Match.status,
            "actual_outcome": row.Match.actual_outcome,
            "home_goals": row.Match.home_goals,
            "away_goals": row.Match.away_goals,
            "ft_score": (
                f"{row.Match.home_goals}-{row.Match.away_goals}"
                if row.Match.home_goals is not None and row.Match.away_goals is not None
                else None
            ),
            "is_settled": row.Match.actual_outcome is not None,
            "opening_odds": {
                "home": row.Match.opening_odds_home,
                "draw": row.Match.opening_odds_draw,
                "away": row.Match.opening_odds_away,
            }
        },
        "prediction": {
            "home_prob": row.Prediction.home_prob,
            "draw_prob": row.Prediction.draw_prob,
            "away_prob": row.Prediction.away_prob,
            "over_25_prob": row.Prediction.over_25_prob,
            "under_25_prob": row.Prediction.under_25_prob,
            "btts_prob": row.Prediction.btts_prob,
            "no_btts_prob": row.Prediction.no_btts_prob,
            "consensus_prob": row.Prediction.consensus_prob,
            "bet_side": row.Prediction.bet_side,
            "entry_odds": row.Prediction.entry_odds,
            "edge": row.Prediction.vig_free_edge,
            "recommended_stake": row.Prediction.recommended_stake,
            "confidence": row.Prediction.confidence,
            "final_ev": row.Prediction.final_ev,
            "timestamp": row.Prediction.timestamp.isoformat(),
        },
        "markets": {
            "1x2": {
                "home_prob": row.Prediction.home_prob,
                "draw_prob": row.Prediction.draw_prob,
                "away_prob": row.Prediction.away_prob,
                "model_breakdown": market_breakdown("1x2", ["home_prob", "draw_prob", "away_prob"])
            },
            "over_under": {
                "over_25_prob": row.Prediction.over_25_prob,
                "under_25_prob": row.Prediction.under_25_prob,
                "model_breakdown": market_breakdown("over_under", ["over_2_5_prob", "under_2_5_prob"])
            },
            "btts": {
                "btts_prob": row.Prediction.btts_prob,
                "no_btts_prob": row.Prediction.no_btts_prob,
                "model_breakdown": market_breakdown("btts", ["btts_prob", "no_btts_prob"])
            }
        },
        "neural_info": neural_info,
        "clv": {
            "clv": row.CLVEntry.clv if row.CLVEntry else None,
            "profit": row.CLVEntry.profit if row.CLVEntry else None,
            "closing_odds": row.CLVEntry.closing_odds if row.CLVEntry else None,
            "bet_outcome": row.CLVEntry.bet_outcome if row.CLVEntry else None,
        } if row.CLVEntry else None,
        "model_summary": {
            "total_models": len(insights),
            "active_models": len(active_models),
            "failed_models": len(insights) - len(active_models),
            "models": [
                {
                    "name": m.get("model_name"),
                    "type": m.get("model_type"),
                    "weight": m.get("model_weight", 1.0),
                    "markets": m.get("supported_markets", []),
                    "confidence_1x2": round(m.get("confidence", {}).get("1x2", 0.5), 3),
                    "confidence_ou": round(m.get("confidence", {}).get("over_under", 0.5), 3),
                    "confidence_btts": round(m.get("confidence", {}).get("btts", 0.5), 3),
                    "latency_ms": m.get("latency_ms"),
                    "failed": m.get("failed", False),
                }
                for m in insights
            ]
        }
    }
