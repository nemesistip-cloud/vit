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

router = APIRouter(prefix="/history", tags=["history"], dependencies=[Depends(verify_api_key)])

CERTIFIED_EDGE_THRESHOLD = 0.05
HIGH_CONFIDENCE_EDGE_THRESHOLD = 0.02


def _format_prediction_row(row):
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
        "bet_side": row.Prediction.bet_side,
        "entry_odds": row.Prediction.entry_odds,
        "actual_outcome": row.Match.actual_outcome,
        "clv": row.CLVEntry.clv if row.CLVEntry else None,
        "profit": row.CLVEntry.profit if row.CLVEntry else None,
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
    current_user=Depends(verify_api_key),
    optional_user=Depends(get_optional_user),
):
    uid: int | None = getattr(optional_user, "id", None)
    apply_user_filter = (uid is not None) and (not all_users)

    base_q = (
        select(Match, Prediction, CLVEntry)
        .join(Prediction, Match.id == Prediction.match_id)
        .outerjoin(CLVEntry, Prediction.id == CLVEntry.prediction_id)
    )
    if apply_user_filter:
        base_q = base_q.where(Prediction.user_id == uid)

    count_q = select(func.count()).select_from(Prediction)
    if apply_user_filter:
        count_q = count_q.where(Prediction.user_id == uid)
    count_result = await db.execute(count_q)
    total = count_result.scalar()

    result = await db.execute(
        base_q
        .order_by(Prediction.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = result.all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "scope": "community" if all_users else ("user" if uid is not None else "anonymous"),
        "predictions": [_format_prediction_row(r) for r in rows]
    }


# ======================================================================
# v4.12.0 — USER-FACING TICKET BUILDER
# Reuses the orchestrator-free DB path: works off Prediction rows that
# already exist, so any authenticated user can build tickets without
# triggering expensive re-predictions.
# ======================================================================

# Markets the builder understands. Each entry maps a market key to the
# probability column on Prediction and (optionally) an odds source
# (`opening_odds_*` on Match for 1x2; otherwise model-derived fair odds).
_TICKET_MARKETS = {
    "home":      {"label": "Home Win",     "prob_attr": "home_prob",     "odds_attr": "opening_odds_home", "category": "1x2"},
    "draw":      {"label": "Draw",         "prob_attr": "draw_prob",     "odds_attr": "opening_odds_draw", "category": "1x2"},
    "away":      {"label": "Away Win",     "prob_attr": "away_prob",     "odds_attr": "opening_odds_away", "category": "1x2"},
    "over_2_5":  {"label": "Over 2.5",     "prob_attr": "over_25_prob",  "odds_attr": None,                "category": "goals"},
    "under_2_5": {"label": "Under 2.5",    "prob_attr": "under_25_prob", "odds_attr": None,                "category": "goals"},
    "btts":      {"label": "BTTS",         "prob_attr": "btts_prob",     "odds_attr": None,                "category": "btts"},
    "no_btts":   {"label": "No BTTS",      "prob_attr": "no_btts_prob",  "odds_attr": None,                "category": "btts"},
}

def _synth_odds_from_prob(p: float) -> float:
    """
    Fair odds derived directly from the model probability (1/p).
    Used for markets where we don't yet capture live bookmaker prices
    (Over/Under, BTTS). The reported edge for such legs is therefore 0
    by construction — the user is expected to enter the real price they
    find at their book, or to read the leg as a 'model-fair' line.
    """
    if not p or p <= 0:
        return 0.0
    return round(1.0 / p, 2)


@router.get("/ticket/markets")
async def list_ticket_markets():
    """Enumerate the markets the ticket builder supports."""
    return {
        "markets": [
            {"key": k, "label": v["label"], "category": v["category"],
             "uses_real_odds": v["odds_attr"] is not None}
            for k, v in _TICKET_MARKETS.items()
        ],
        "unsupported": [
            {"key": "correct_score", "reason": "Correct-score probabilities are not stored on Prediction yet."},
        ],
    }


@router.get("/ticket/candidates")
async def get_ticket_candidates(
    market: str = Query(..., description="One of: " + ", ".join(_TICKET_MARKETS.keys())),
    min_confidence: float = Query(0.60, ge=0.0, le=1.0),
    min_edge: float = Query(0.02, ge=0.0, le=1.0),
    limit: int = Query(20, ge=1, le=50),
    only_upcoming: bool = Query(True, description="Restrict to unsettled, future-kickoff matches"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return high-confidence selections for a given market, drawn from the
    most recent Prediction per match in the database. Each candidate
    carries enough info for the build endpoint to combine it into a ticket.
    """
    if market not in _TICKET_MARKETS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported market '{market}'. Choose from: {sorted(_TICKET_MARKETS.keys())}"
        )

    spec = _TICKET_MARKETS[market]
    prob_attr = spec["prob_attr"]
    odds_attr = spec["odds_attr"]

    # Pull the most recent prediction per match (latest timestamp wins) so
    # we don't duplicate the same fixture across users / re-runs.
    latest_pred_subq = (
        select(Prediction.match_id, func.max(Prediction.timestamp).label("max_ts"))
        .group_by(Prediction.match_id)
        .subquery()
    )

    q = (
        select(Match, Prediction)
        .join(Prediction, Match.id == Prediction.match_id)
        .join(
            latest_pred_subq,
            (Prediction.match_id == latest_pred_subq.c.match_id)
            & (Prediction.timestamp == latest_pred_subq.c.max_ts),
        )
    )

    if only_upcoming:
        now = datetime.now(timezone.utc)
        q = q.where(Match.kickoff_time > now, Match.actual_outcome.is_(None))

    result = await db.execute(q.order_by(Prediction.timestamp.desc()).limit(500))
    rows = result.all()

    candidates = []
    for r in rows:
        m, p = r.Match, r.Prediction
        prob = getattr(p, prob_attr, None)
        if prob is None or prob < min_confidence:
            continue

        # Resolve odds + edge
        if odds_attr is not None:
            odds = getattr(m, odds_attr, None)
            if not odds or odds <= 1.0:
                continue
            implied = 1.0 / odds
            edge = float(prob) - implied
            odds_source = "bookmaker_opening"
            # Edge filter only meaningful when we have real bookmaker odds.
            if edge < min_edge:
                continue
        else:
            odds = _synth_odds_from_prob(float(prob))
            if odds <= 1.0:
                continue
            edge = 0.0  # fair-odds line — edge is undefined without a real price
            odds_source = "model_fair"

        candidates.append({
            "match_id": m.id,
            "home_team": m.home_team,
            "away_team": m.away_team,
            "league": m.league,
            "kickoff_time": m.kickoff_time.isoformat() if m.kickoff_time else None,
            "market": market,
            "market_label": spec["label"],
            "selection": spec["label"],
            "probability": round(float(prob), 4),
            "odds": round(float(odds), 2),
            "odds_source": odds_source,
            "edge": round(float(edge), 4),
            "confidence": round(float(p.confidence or prob), 3),
            "ev_score": round(float(prob) * float(edge), 5),
        })

    candidates.sort(key=lambda c: c["ev_score"], reverse=True)

    return {
        "market": market,
        "market_label": spec["label"],
        "filters": {"min_confidence": min_confidence, "min_edge": min_edge,
                    "only_upcoming": only_upcoming},
        "total_found": len(candidates),
        "candidates": candidates[:limit],
    }


class TicketLeg(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    league: Optional[str] = None
    kickoff_time: Optional[str] = None
    market: str
    market_label: Optional[str] = None
    selection: Optional[str] = None
    probability: float
    odds: float
    edge: Optional[float] = None
    confidence: Optional[float] = None
    odds_source: Optional[str] = None


class TicketBuildRequest(BaseModel):
    candidates: List[TicketLeg] = Field(..., min_length=2)
    legs: int = Field(3, ge=2, le=10, description="Number of legs in the ticket")
    top_n: int = Field(5, ge=1, le=20)
    min_combined_edge: float = Field(0.0, ge=-1.0, le=10.0)
    same_match_allowed: bool = Field(False, description="Allow multiple legs on the same fixture")


def _correlation_penalty(legs: List[TicketLeg]) -> float:
    """1.5% per same-league pair (matches the admin accumulator behaviour)."""
    leagues = [leg.league or "" for leg in legs]
    same_pairs = sum(
        1 for a, b in combinations(range(len(leagues)), 2)
        if leagues[a] and leagues[a] == leagues[b]
    )
    return same_pairs * 0.015


@router.post("/ticket/build")
async def build_ticket(body: TicketBuildRequest):
    """
    Combine candidate legs into N-leg tickets and return the top-N by
    correlation-adjusted combined edge.

    For each combination:
      combined_prob   = ∏ leg.probability
      combined_odds   = ∏ leg.odds
      combined_edge   = combined_prob − 1/combined_odds
      adjusted_edge   = combined_edge − correlation_penalty
      kelly_stake     = capped Kelly on combined_odds & combined_prob
    """
    candidates = body.candidates
    if len(candidates) < body.legs:
        raise HTTPException(
            status_code=422,
            detail=f"Need at least {body.legs} candidates to build a {body.legs}-leg ticket. "
                   f"Got {len(candidates)}."
        )

    tickets = []
    for combo in combinations(candidates, body.legs):
        legs = list(combo)

        if not body.same_match_allowed:
            match_ids = [leg.match_id for leg in legs]
            if len(set(match_ids)) != len(match_ids):
                continue

        combined_prob = 1.0
        combined_odds = 1.0
        for leg in legs:
            if leg.probability <= 0 or leg.odds <= 1.0:
                combined_prob = 0.0
                break
            combined_prob *= leg.probability
            combined_odds *= leg.odds

        if combined_prob <= 0:
            continue

        fair_odds = 1.0 / combined_prob
        combined_edge = combined_prob - (1.0 / combined_odds)
        penalty = _correlation_penalty(legs)
        adjusted_edge = combined_edge - penalty

        b = combined_odds - 1.0
        p = combined_prob
        q = 1.0 - p
        kelly = max(0.0, (b * p - q) / b) if b > 0 else 0.0
        kelly = min(kelly, 0.03)  # cap accumulator stakes at 3% of bankroll

        avg_confidence = sum((leg.confidence or leg.probability) for leg in legs) / len(legs)

        if adjusted_edge < body.min_combined_edge:
            continue

        tickets.append({
            "n_legs": len(legs),
            "legs": [leg.dict() for leg in legs],
            "combined_prob": round(combined_prob, 5),
            "combined_odds": round(combined_odds, 2),
            "fair_odds": round(fair_odds, 2),
            "combined_edge": round(combined_edge, 4),
            "correlation_penalty": round(penalty, 4),
            "adjusted_edge": round(adjusted_edge, 4),
            "avg_confidence": round(avg_confidence, 3),
            "kelly_stake": round(kelly, 4),
            "potential_return_per_unit": round(combined_odds, 2),
        })

    tickets.sort(key=lambda t: t["adjusted_edge"], reverse=True)

    return {
        "requested_legs": body.legs,
        "candidates_supplied": len(candidates),
        "total_generated": len(tickets),
        "tickets": tickets[:body.top_n],
    }


@router.delete("/clear")
@router.delete("/clear-all")
async def clear_history(db: AsyncSession = Depends(get_db)):
    """
    Delete all prediction history, including match and CLV records tied to historical predictions.
    """
    await db.execute(delete(CLVEntry))
    await db.execute(delete(Prediction))
    await db.execute(delete(Match))
    await db.commit()
    return {"message": "Prediction history cleared"}


@router.get("/picks")
async def get_picks(db: AsyncSession = Depends(get_db)):
    """
    Return certified picks (edge > 5%) and high-confidence picks (edge > 2%).
    Backed by child model ratings stored in model_insights.
    """
    result = await db.execute(
        select(Match, Prediction, CLVEntry)
        .join(Prediction, Match.id == Prediction.match_id)
        .outerjoin(CLVEntry, Prediction.id == CLVEntry.prediction_id)
        .where(Prediction.vig_free_edge.isnot(None))
        .order_by(Prediction.vig_free_edge.desc())
        .limit(100)
    )
    rows = result.all()

    certified = []
    high_confidence = []

    for row in rows:
        edge = row.Prediction.vig_free_edge or 0
        insights = row.Prediction.model_insights or []

        active_models = [m for m in insights if not m.get("failed")]
        num_models = len(active_models)

        if num_models == 0:
            continue

        # Calculate per-market model agreement (consensus)
        bet_side = row.Prediction.bet_side
        side_probs = []
        if bet_side == "home":
            side_probs = [m.get("home_prob", 0) for m in active_models if m.get("home_prob") is not None]
        elif bet_side == "draw":
            side_probs = [m.get("draw_prob", 0) for m in active_models if m.get("draw_prob") is not None]
        elif bet_side == "away":
            side_probs = [m.get("away_prob", 0) for m in active_models if m.get("away_prob") is not None]

        avg_model_prob = sum(side_probs) / len(side_probs) if side_probs else 0
        model_agreement = sum(
            1 for m in active_models
            if (bet_side == "home" and (m.get("home_prob") or 0) > 0.4)
            or (bet_side == "draw" and (m.get("draw_prob") or 0) > 0.3)
            or (bet_side == "away" and (m.get("away_prob") or 0) > 0.4)
        )
        agreement_pct = round(model_agreement / num_models * 100, 1) if num_models > 0 else 0

        # Model confidence ratings per market
        avg_1x2_confidence = (
            sum(m.get("confidence", {}).get("1x2", 0.5) for m in active_models) / num_models
        ) if num_models > 0 else 0.5
        avg_ou_confidence = (
            sum(m.get("confidence", {}).get("over_under", 0.5) for m in active_models if "over_under" in m.get("supported_markets", [])) /
            max(1, sum(1 for m in active_models if "over_under" in m.get("supported_markets", [])))
        )
        avg_btts_confidence = (
            sum(m.get("confidence", {}).get("btts", 0.5) for m in active_models if "btts" in m.get("supported_markets", [])) /
            max(1, sum(1 for m in active_models if "btts" in m.get("supported_markets", [])))
        )

        pick = {
            **_format_prediction_row(row),
            "model_insights": insights,
            "num_models": num_models,
            "model_agreement_pct": agreement_pct,
            "avg_model_prob": round(avg_model_prob, 3),
            "avg_1x2_confidence": round(avg_1x2_confidence, 3),
            "avg_ou_confidence": round(avg_ou_confidence, 3),
            "avg_btts_confidence": round(avg_btts_confidence, 3),
            "pick_type": "certified" if edge >= CERTIFIED_EDGE_THRESHOLD else "high_confidence"
        }

        if edge >= CERTIFIED_EDGE_THRESHOLD:
            certified.append(pick)
        elif edge >= HIGH_CONFIDENCE_EDGE_THRESHOLD:
            high_confidence.append(pick)

    return {
        "certified_picks": certified[:20],
        "high_confidence_picks": high_confidence[:20],
        "certified_count": len(certified),
        "high_confidence_count": len(high_confidence),
        "edge_thresholds": {
            "certified": CERTIFIED_EDGE_THRESHOLD,
            "high_confidence": HIGH_CONFIDENCE_EDGE_THRESHOLD
        }
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
