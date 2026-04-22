from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import os

from app.db.database import get_db, AsyncSessionLocal
from app.db.models import Match, Prediction
from app.modules.wallet.models import PlatformConfig

router = APIRouter(prefix="/matches", tags=["matches"])
logger = logging.getLogger(__name__)

LEAGUE_DISPLAY_NAMES = {
    "premier_league": "Premier League",
    "la_liga": "La Liga",
    "bundesliga": "Bundesliga",
    "serie_a": "Serie A",
    "ligue_1": "Ligue 1",
    "eredivisie": "Eredivisie",
    "primeira_liga": "Primeira Liga",
    "championship": "Championship",
    "scottish_premiership": "Scottish Premiership",
    "belgian_pro_league": "Belgian Pro League",
    "ucl": "Champions League",
    "uel": "Europa League",
}

COMPETITIONS = {
    "premier_league": "PL",
    "la_liga": "PD",
    "bundesliga": "BL1",
    "serie_a": "SA",
    "ligue_1": "FL1",
    "eredivisie": "DED",
    "championship": "ELC",
    "primeira_liga": "PPL",
}

DEFAULT_MARKETS = [
    {"id": "1x2",              "name": "1X2 (Home/Draw/Away)",    "status": "active", "min_stake": 5, "max_stake": 1000, "edge_threshold": 2.0, "commission_rate": 5.0,  "available_tiers": ["viewer","analyst","pro","elite"], "category": "match_result"},
    {"id": "over_under_25",    "name": "Over/Under 2.5 Goals",    "status": "active", "min_stake": 5, "max_stake": 1000, "edge_threshold": 2.0, "commission_rate": 5.0,  "available_tiers": ["viewer","analyst","pro","elite"], "category": "goals"},
    {"id": "btts",             "name": "Both Teams To Score",     "status": "active", "min_stake": 5, "max_stake": 1000, "edge_threshold": 2.0, "commission_rate": 5.0,  "available_tiers": ["viewer","analyst","pro","elite"], "category": "goals"},
    {"id": "double_chance",    "name": "Double Chance",           "status": "active", "min_stake": 5, "max_stake": 750,  "edge_threshold": 2.5, "commission_rate": 5.0,  "available_tiers": ["analyst","pro","elite"],           "category": "match_result"},
    {"id": "over_under_15",    "name": "Over/Under 1.5 Goals",   "status": "active", "min_stake": 5, "max_stake": 750,  "edge_threshold": 2.5, "commission_rate": 5.5,  "available_tiers": ["analyst","pro","elite"],           "category": "goals"},
    {"id": "over_under_35",    "name": "Over/Under 3.5 Goals",   "status": "active", "min_stake": 5, "max_stake": 750,  "edge_threshold": 2.5, "commission_rate": 5.5,  "available_tiers": ["analyst","pro","elite"],           "category": "goals"},
    {"id": "draw_no_bet",      "name": "Draw No Bet (DNB)",       "status": "active", "min_stake": 5, "max_stake": 500,  "edge_threshold": 2.5, "commission_rate": 5.0,  "available_tiers": ["pro","elite"],                    "category": "match_result"},
    {"id": "asian_handicap",   "name": "Asian Handicap",          "status": "active", "min_stake": 5, "max_stake": 500,  "edge_threshold": 3.0, "commission_rate": 6.0,  "available_tiers": ["pro","elite"],                    "category": "handicap"},
    {"id": "btts_ht",          "name": "BTTS — Half Time",        "status": "active", "min_stake": 5, "max_stake": 500,  "edge_threshold": 3.0, "commission_rate": 6.0,  "available_tiers": ["pro","elite"],                    "category": "goals"},
    {"id": "clean_sheet_home", "name": "Home Clean Sheet",        "status": "active", "min_stake": 5, "max_stake": 400,  "edge_threshold": 3.0, "commission_rate": 6.0,  "available_tiers": ["pro","elite"],                    "category": "goals"},
    {"id": "clean_sheet_away", "name": "Away Clean Sheet",        "status": "active", "min_stake": 5, "max_stake": 400,  "edge_threshold": 3.0, "commission_rate": 6.0,  "available_tiers": ["pro","elite"],                    "category": "goals"},
    {"id": "win_to_nil",       "name": "Win To Nil",              "status": "active", "min_stake": 5, "max_stake": 400,  "edge_threshold": 3.0, "commission_rate": 6.5,  "available_tiers": ["pro","elite"],                    "category": "goals"},
    {"id": "correct_score",    "name": "Correct Score (CS)",      "status": "active", "min_stake": 2, "max_stake": 100,  "edge_threshold": 5.0, "commission_rate": 8.0,  "available_tiers": ["elite"],                          "category": "correct_score"},
    {"id": "htft",             "name": "Half Time / Full Time",   "status": "active", "min_stake": 2, "max_stake": 200,  "edge_threshold": 4.0, "commission_rate": 7.0,  "available_tiers": ["elite"],                          "category": "match_result"},
    {"id": "match_winner_ht",  "name": "Half Time Result",        "status": "active", "min_stake": 5, "max_stake": 300,  "edge_threshold": 3.5, "commission_rate": 6.5,  "available_tiers": ["elite"],                          "category": "match_result"},
    {"id": "first_goal",       "name": "First Goal Scorer",       "status": "paused", "min_stake": 1, "max_stake": 50,   "edge_threshold": 5.0, "commission_rate": 10.0, "available_tiers": ["elite"],                          "category": "player"},
    {"id": "anytime_scorer",   "name": "Anytime Goal Scorer",     "status": "paused", "min_stake": 1, "max_stake": 50,   "edge_threshold": 5.0, "commission_rate": 10.0, "available_tiers": ["elite"],                          "category": "player"},
    {"id": "over_under",       "name": "Over/Under 2.5 (alias)",  "status": "active", "min_stake": 5, "max_stake": 1000, "edge_threshold": 2.0, "commission_rate": 5.0,  "available_tiers": ["viewer","analyst","pro","elite"], "category": "goals"},
]


def _fmt_league(league: str) -> str:
    return LEAGUE_DISPLAY_NAMES.get(league, league.replace("_", " ").title() if league else "Unknown")


async def _load_markets(db: AsyncSession) -> list:
    row = (await db.execute(select(PlatformConfig).where(PlatformConfig.key == "markets_config"))).scalar_one_or_none()
    return row.value if row and isinstance(row.value, list) else DEFAULT_MARKETS


def _active_market_ids(markets: Optional[list]) -> set:
    source = markets if markets else DEFAULT_MARKETS
    return {str(m.get("id")) for m in source if m.get("status") == "active"}


def _vig_free_probs(home_odds, draw_odds, away_odds) -> Optional[dict]:
    try:
        h = float(home_odds)
        d = float(draw_odds)
        a = float(away_odds)
        if min(h, d, a) <= 1.0:
            return None
        inv_h, inv_d, inv_a = 1 / h, 1 / d, 1 / a
        total = inv_h + inv_d + inv_a
        if total <= 0:
            return None
        return {"home": inv_h / total, "draw": inv_d / total, "away": inv_a / total}
    except (TypeError, ValueError):
        return None


def _secondary_market_probs(home_prob: Optional[float], draw_prob: Optional[float], away_prob: Optional[float], draw_odds) -> dict:
    import math as _math
    if home_prob is None or draw_prob is None or away_prob is None:
        return {"over_25": None, "under_25": None, "btts": None, "no_btts": None,
                "over_15": None, "under_15": None, "over_35": None, "under_35": None,
                "dnb_home": None, "dnb_away": None}
    try:
        draw_price = float(draw_odds) if draw_odds else 3.3
    except (TypeError, ValueError):
        draw_price = 3.3

    balance = 1.0 - abs(home_prob - away_prob)
    over_25 = max(0.32, min(0.72, 0.45 + (draw_price - 3.2) * 0.055 + max(home_prob, away_prob) * 0.12))
    btts = max(0.28, min(0.68, 0.42 + balance * 0.20 + (draw_price - 3.2) * 0.025))

    # Poisson-derived lambdas from implied goal expectation
    # A rough estimate: lam ≈ f(over_25) via Poisson CDF inversion
    # P(goals >= 3) = over_25 → solve for lam empirically
    # Using approximation: lam_total ≈ -ln(1 - over_25) * 2.1
    lam_total = max(1.0, -_math.log(max(0.01, 1.0 - over_25)) * 2.1)
    lam_h = lam_total * (0.55 + (home_prob - away_prob) * 0.4)
    lam_a = lam_total - lam_h

    def _poisson_p_under(lam: float, k: int) -> float:
        """P(X <= k) for Poisson(lam)."""
        return sum(_math.exp(-lam) * (lam ** i) / _math.factorial(i) for i in range(k + 1))

    p_under_total_1 = _poisson_p_under(lam_total, 1)  # P(total goals <= 1)
    p_under_total_3 = _poisson_p_under(lam_total, 3)  # P(total goals <= 3)

    over_15 = max(0.4, min(0.92, 1.0 - p_under_total_1))
    over_35 = max(0.10, min(0.55, 1.0 - p_under_total_3))

    # DNB = Draw No Bet — remove draw from market, renormalize home/away
    dnb_total = home_prob + away_prob
    dnb_home = round(home_prob / dnb_total, 4) if dnb_total > 0 else 0.5
    dnb_away = round(away_prob / dnb_total, 4) if dnb_total > 0 else 0.5

    return {
        "over_25": round(over_25, 4),
        "under_25": round(1 - over_25, 4),
        "btts": round(btts, 4),
        "no_btts": round(1 - btts, 4),
        "over_15": round(over_15, 4),
        "under_15": round(1 - over_15, 4),
        "over_35": round(over_35, 4),
        "under_35": round(1 - over_35, 4),
        "dnb_home": dnb_home,
        "dnb_away": dnb_away,
    }


def _fmt_match(m: Match, pred: Optional[Prediction] = None, markets: Optional[list] = None) -> dict:
    odds_home = m.opening_odds_home or m.closing_odds_home
    odds_draw = m.opening_odds_draw or m.closing_odds_draw
    odds_away = m.opening_odds_away or m.closing_odds_away
    active_markets = _active_market_ids(markets)
    market_probs = _vig_free_probs(odds_home, odds_draw, odds_away)

    edge = None
    if pred and pred.vig_free_edge is not None:
        edge = pred.vig_free_edge
    elif odds_home and pred and pred.home_prob:
        market_prob = 1.0 / odds_home
        edge = round(float(pred.home_prob) - market_prob, 4)

    home_prob = float(pred.home_prob) if pred and pred.home_prob is not None else (market_probs or {}).get("home")
    draw_prob = float(pred.draw_prob) if pred and pred.draw_prob is not None else (market_probs or {}).get("draw")
    away_prob = float(pred.away_prob) if pred and pred.away_prob is not None else (market_probs or {}).get("away")
    secondary = _secondary_market_probs(home_prob, draw_prob, away_prob, odds_draw)
    over_25_prob = float(pred.over_25_prob) if pred and pred.over_25_prob is not None else secondary["over_25"]
    under_25_prob = float(pred.under_25_prob) if pred and pred.under_25_prob is not None else secondary["under_25"]
    btts_prob = float(pred.btts_prob) if pred and pred.btts_prob is not None else secondary["btts"]
    no_btts_prob = float(pred.no_btts_prob) if pred and pred.no_btts_prob is not None else secondary["no_btts"]
    over_15_prob = secondary.get("over_15")
    under_15_prob = secondary.get("under_15")
    over_35_prob = secondary.get("over_35")
    under_35_prob = secondary.get("under_35")
    dnb_home_prob = secondary.get("dnb_home")
    dnb_away_prob = secondary.get("dnb_away")
    confidence = float(pred.confidence) if pred and pred.confidence is not None else (0.55 if market_probs else None)

    return {
        "match_id": m.id,
        "external_id": m.external_id,
        "home_team": m.home_team,
        "away_team": m.away_team,
        "league": _fmt_league(m.league) if m.league else "Unknown",
        "league_key": m.league or "unknown",
        "kickoff_time": m.kickoff_time.isoformat() if m.kickoff_time else None,
        "status": m.status or "upcoming",
        "odds": {
            "home": float(odds_home) if odds_home else None,
            "draw": float(odds_draw) if odds_draw else None,
            "away": float(odds_away) if odds_away else None,
        },
        "home_goals": m.home_goals,
        "away_goals": m.away_goals,
        "actual_outcome": m.actual_outcome,
        "home_prob": home_prob if "1x2" in active_markets else None,
        "draw_prob": draw_prob if "1x2" in active_markets else None,
        "away_prob": away_prob if "1x2" in active_markets else None,
        "over_25_prob": over_25_prob if "over_under_25" in active_markets or "over_under" in active_markets else None,
        "under_25_prob": under_25_prob if "over_under_25" in active_markets or "over_under" in active_markets else None,
        "over_15_prob": over_15_prob if "over_under_15" in active_markets or "over_under_25" in active_markets or "over_under" in active_markets else None,
        "under_15_prob": under_15_prob if "over_under_15" in active_markets or "over_under_25" in active_markets or "over_under" in active_markets else None,
        "over_35_prob": over_35_prob if "over_under_35" in active_markets or "over_under_25" in active_markets or "over_under" in active_markets else None,
        "under_35_prob": under_35_prob if "over_under_35" in active_markets or "over_under_25" in active_markets or "over_under" in active_markets else None,
        "btts_prob": btts_prob if "btts" in active_markets else None,
        "no_btts_prob": no_btts_prob if "btts" in active_markets else None,
        "dnb_home_prob": dnb_home_prob if "dnb" in active_markets or "1x2" in active_markets else None,
        "dnb_away_prob": dnb_away_prob if "dnb" in active_markets or "1x2" in active_markets else None,
        "confidence": confidence,
        "bet_side": pred.bet_side if pred else None,
        "edge": edge,
        "entry_odds": float(pred.entry_odds) if pred and pred.entry_odds else None,
        "recommended_stake": float(pred.recommended_stake) if pred and pred.recommended_stake is not None else 0.0,
        "market_prob_source": "ensemble" if pred else "market_odds",
        "enabled_markets": markets if markets is not None else DEFAULT_MARKETS,
    }


@router.get("/upcoming")
async def get_upcoming_matches(
    league: Optional[str] = Query(None),
    days: int = Query(14, ge=1, le=60),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    future = now + timedelta(days=days)
    # Include matches that started up to 3 hours ago but aren't settled yet
    recent_cutoff = now - timedelta(hours=3)

    q = select(Match).where(
        and_(
            Match.kickoff_time >= recent_cutoff,
            Match.kickoff_time <= future,
            Match.actual_outcome.is_(None),
        )
    )
    if league:
        q = q.where(Match.league.ilike(f"%{league}%"))
    q = q.order_by(Match.kickoff_time).limit(limit)

    result = await db.execute(q)
    matches = result.scalars().all()
    markets = await _load_markets(db)

    match_ids = [m.id for m in matches]
    preds_map: dict = {}
    if match_ids:
        pred_q = await db.execute(
            select(Prediction)
            .where(Prediction.match_id.in_(match_ids))
            .order_by(Prediction.timestamp.desc())
        )
        for p in pred_q.scalars().all():
            if p.match_id not in preds_map:
                preds_map[p.match_id] = p

    return {
        "count": len(matches),
        "enabled_markets": markets,
        "matches": [_fmt_match(m, preds_map.get(m.id), markets) for m in matches],
    }


@router.get("/explore")
async def explore_matches(
    league: Optional[str] = Query(None),
    min_edge: float = Query(0.0, ge=0),
    min_confidence: float = Query(0.0, ge=0, le=1),
    days: int = Query(14, ge=1, le=60),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    future = now + timedelta(days=days)
    recent_cutoff = now - timedelta(hours=3)

    q = (
        select(Match, Prediction)
        .outerjoin(Prediction, Match.id == Prediction.match_id)
        .where(Match.kickoff_time >= recent_cutoff)
        .where(Match.kickoff_time <= future)
        .where(Match.actual_outcome.is_(None))
    )
    if league:
        q = q.where(Match.league.ilike(f"%{league}%"))
    q = q.order_by(Match.kickoff_time, Prediction.timestamp.desc())

    result = await db.execute(q)
    rows = result.all()
    markets = await _load_markets(db)

    seen: set = set()
    formatted = []
    for row in rows:
        m, pred = row.Match, row.Prediction
        if m.id in seen:
            continue
        seen.add(m.id)

        conf = float(pred.confidence or 0) if pred else 0.0
        edge_val = 0.0
        if pred and pred.vig_free_edge is not None:
            edge_val = float(pred.vig_free_edge)

        if conf < min_confidence or edge_val < min_edge:
            continue

        formatted.append(_fmt_match(m, pred, markets))

    return {"count": len(formatted), "enabled_markets": markets, "matches": formatted[:limit]}


@router.get("/live")
async def get_live_matches(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    q = select(Match).where(
        and_(
            Match.kickoff_time <= now,
            Match.kickoff_time >= now - timedelta(hours=3),
            Match.actual_outcome.is_(None),
            or_(Match.status == "live", Match.status == "IN_PLAY", Match.status == "LIVE"),
        )
    ).order_by(Match.kickoff_time.desc()).limit(20)

    result = await db.execute(q)
    matches = result.scalars().all()
    markets = await _load_markets(db)

    return {
        "count": len(matches),
        "enabled_markets": markets,
        "matches": [_fmt_match(m, None, markets) for m in matches],
    }


@router.get("/recent")
async def get_recent_matches(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Show: unsettled matches (kicked off up to 3h ago → future), ordered soonest first
    recent_cutoff = now - timedelta(hours=3)

    q = (
        select(Match, Prediction)
        .outerjoin(Prediction, Match.id == Prediction.match_id)
        .where(Match.actual_outcome.is_(None))
        .where(Match.kickoff_time >= recent_cutoff)
        .order_by(Match.kickoff_time.asc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()
    markets = await _load_markets(db)

    # Fallback: show all unsettled matches regardless of date
    if not rows:
        q2 = (
            select(Match, Prediction)
            .outerjoin(Prediction, Match.id == Prediction.match_id)
            .where(Match.actual_outcome.is_(None))
            .order_by(Match.kickoff_time.asc())
            .limit(limit)
        )
        result = await db.execute(q2)
        rows = result.all()

    seen: set = set()
    formatted = []
    for row in rows:
        m, pred = row.Match, row.Prediction
        if m.id in seen:
            continue
        seen.add(m.id)
        formatted.append(_fmt_match(m, pred, markets))

    return {"count": len(formatted), "enabled_markets": markets, "matches": formatted}


@router.get("/completed")
async def get_completed_matches(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Show: completed matches (with actual outcomes), ordered most recent first
    q = (
        select(Match, Prediction)
        .outerjoin(Prediction, Match.id == Prediction.match_id)
        .where(Match.actual_outcome.isnot(None))
        .order_by(Match.kickoff_time.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()
    markets = await _load_markets(db)

    seen: set = set()
    formatted = []
    for row in rows:
        m, pred = row.Match, row.Prediction
        if m.id in seen:
            continue
        seen.add(m.id)
        formatted.append(_fmt_match(m, pred, markets))

    return {"count": len(formatted), "enabled_markets": markets, "matches": formatted}


@router.get("/leagues/list")
async def list_leagues(db: AsyncSession = Depends(get_db)):
    """Return all distinct leagues with display names."""
    result = await db.execute(
        select(Match.league).distinct().where(Match.league.isnot(None))
    )
    keys = [row[0] for row in result.all()]
    return {
        "leagues": [
            {"key": k, "display": _fmt_league(k)}
            for k in sorted(keys)
        ]
    }


@router.get("/sync/status")
async def sync_status(db: AsyncSession = Depends(get_db)):
    """Return count of matches in DB and last stored kickoff time."""
    from sqlalchemy import func as _func
    count_result = await db.execute(select(_func.count(Match.id)))
    count = count_result.scalar() or 0
    last_result = await db.execute(
        select(Match.kickoff_time).order_by(Match.kickoff_time.desc()).limit(1)
    )
    last_kickoff = last_result.scalar_one_or_none()
    return {
        "total_matches": count,
        "last_kickoff": last_kickoff.isoformat() if last_kickoff else None,
    }


@router.get("/markets/enabled")
async def enabled_markets(db: AsyncSession = Depends(get_db)):
    markets = await _load_markets(db)
    return {"markets": [m for m in markets if m.get("status") == "active"], "all_markets": markets}


async def _recent_form(db: AsyncSession, team: str, before: datetime) -> dict:
    q = (
        select(Match)
        .where(or_(Match.home_team == team, Match.away_team == team))
        .where(Match.actual_outcome.isnot(None))
        .where(Match.kickoff_time < before)
        .order_by(Match.kickoff_time.desc())
        .limit(5)
    )
    rows = (await db.execute(q)).scalars().all()
    form = []
    for row in rows:
        is_home = row.home_team == team
        if row.actual_outcome == "draw":
            form.append("D")
        elif (row.actual_outcome == "home" and is_home) or (row.actual_outcome == "away" and not is_home):
            form.append("W")
        else:
            form.append("L")
    return {"team": team, "form": "".join(form) if form else "N/A", "matches": len(rows)}


async def _head_to_head(db: AsyncSession, match: Match) -> dict:
    q = (
        select(Match)
        .where(
            or_(
                and_(Match.home_team == match.home_team, Match.away_team == match.away_team),
                and_(Match.home_team == match.away_team, Match.away_team == match.home_team),
            )
        )
        .where(Match.actual_outcome.isnot(None))
        .where(Match.id != match.id)
        .order_by(Match.kickoff_time.desc())
        .limit(5)
    )
    rows = (await db.execute(q)).scalars().all()
    items = [
        {
            "home_team": r.home_team,
            "away_team": r.away_team,
            "score": f"{r.home_goals}-{r.away_goals}" if r.home_goals is not None and r.away_goals is not None else None,
            "outcome": r.actual_outcome,
            "kickoff_time": r.kickoff_time.isoformat() if r.kickoff_time else None,
        }
        for r in rows
    ]
    return {"count": len(items), "matches": items}


@router.get("/{match_id}")
async def get_match_detail(match_id: int, db: AsyncSession = Depends(get_db)):
    match_q = await db.execute(select(Match).where(Match.id == match_id))
    match = match_q.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    pred_q = await db.execute(
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(Prediction.timestamp.desc())
    )
    preds = pred_q.scalars().all()
    latest_pred = preds[0] if preds else None
    markets = await _load_markets(db)
    model_insights = latest_pred.model_insights if latest_pred and isinstance(latest_pred.model_insights, list) else []
    model_weights = latest_pred.model_weights if latest_pred and isinstance(latest_pred.model_weights, dict) else {}
    latest = _fmt_match(match, latest_pred, markets)
    h = latest.get("home_prob") or 0
    d = latest.get("draw_prob") or 0
    a = latest.get("away_prob") or 0

    return {
        "match": latest,
        "predictions_count": len(preds),
        "predictions": [
            {
                "home_prob": float(p.home_prob or 0),
                "draw_prob": float(p.draw_prob or 0),
                "away_prob": float(p.away_prob or 0),
                "over_25_prob": float(p.over_25_prob or 0) if p.over_25_prob is not None else None,
                "under_25_prob": float(p.under_25_prob or 0) if p.under_25_prob is not None else None,
                "btts_prob": float(p.btts_prob or 0) if p.btts_prob is not None else None,
                "no_btts_prob": float(p.no_btts_prob or 0) if p.no_btts_prob is not None else None,
                "bet_side": p.bet_side,
                "confidence": float(p.confidence or 0),
                "edge": float(p.vig_free_edge or 0),
                "entry_odds": float(p.entry_odds or 0),
                "recommended_stake": float(p.recommended_stake or 0),
                "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            }
            for p in preds[:10]
        ],
        "enabled_markets": markets,
        "model_contributions": model_insights,
        "model_summary": {
            "models_used": len(model_insights),
            "weights": model_weights,
            "source": latest.get("market_prob_source"),
        },
        "consensus_breakdown": {
            "home": h,
            "draw": d,
            "away": a,
            "leader": max({"home": h, "draw": d, "away": a}, key={"home": h, "draw": d, "away": a}.get),
            "probability_sum": round(h + d + a, 6),
        },
        "recent_form": {
            "home": await _recent_form(db, match.home_team, match.kickoff_time),
            "away": await _recent_form(db, match.away_team, match.kickoff_time),
        },
        "head_to_head": await _head_to_head(db, match),
    }


@router.post("/sync")
async def sync_fixtures(
    days: int = Query(default=14, ge=1, le=30),
):
    """
    Fetch and store upcoming fixtures from Football-Data API.

    Behaviour:
    - If FOOTBALL_DATA_API_KEY is set, fetch from the API.
    - Each fixture is deduplicated by stable fingerprint
      (date::home::away::league) AND by external_id, so manually-uploaded
      or seeded matches are never overwritten by the API.
    - Synthetic fallback fixtures are NEVER generated unless
      ENABLE_SYNTHETIC_FIXTURES=true is set explicitly.
    - On rate-limit (429) or no API key, the route returns a clean
      response so the operator can act, instead of fabricating data.
    """
    import httpx
    from app.data.match_dedup import compute_fingerprint, find_existing_match

    football_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
    allow_synthetic = os.getenv("ENABLE_SYNTHETIC_FIXTURES", "false").lower() == "true"
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    date_from = tomorrow.strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=days)).strftime("%Y-%m-%d")

    stored = 0
    skipped_existing = 0
    skipped_dedup = 0
    rate_limited_leagues: list[str] = []

    if not football_key:
        return {
            "stored": 0,
            "skipped_existing": 0,
            "source": "none",
            "message": "FOOTBALL_DATA_API_KEY not configured. "
                       "No synthetic fallback (ENABLE_SYNTHETIC_FIXTURES is off).",
            "synthetic_fallback_enabled": allow_synthetic,
        }

    async with httpx.AsyncClient(timeout=20) as client:
        async with AsyncSessionLocal() as db:
            for league, code in COMPETITIONS.items():
                try:
                    r = await client.get(
                        f"https://api.football-data.org/v4/competitions/{code}/matches",
                        headers={"X-Auth-Token": football_key},
                        params={"status": "SCHEDULED", "dateFrom": date_from, "dateTo": date_to},
                    )
                    if r.status_code == 200:
                        for m in r.json().get("matches", []):
                            ext_id = str(m.get("id", ""))
                            kickoff_str = m.get("utcDate", "")
                            try:
                                kickoff = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00")).replace(tzinfo=None)
                            except Exception:
                                continue
                            home_team = m["homeTeam"]["name"]
                            away_team = m["awayTeam"]["name"]

                            # Dedup by external_id first
                            existing = (await db.execute(
                                select(Match).where(Match.external_id == ext_id)
                            )).scalar_one_or_none()
                            if existing:
                                skipped_existing += 1
                                continue
                            # Dedup by cross-source fingerprint (don't overwrite
                            # manually-uploaded or seeded fixtures)
                            existing_fp = await find_existing_match(
                                db, home_team, away_team, kickoff, league
                            )
                            if existing_fp:
                                # Backfill external_id only — keep original source
                                if not existing_fp.external_id:
                                    existing_fp.external_id = ext_id
                                skipped_dedup += 1
                                continue
                            odds_data = m.get("odds", {})
                            db.add(Match(
                                external_id=ext_id,
                                home_team=home_team,
                                away_team=away_team,
                                league=league,
                                kickoff_time=kickoff,
                                status="upcoming",
                                source="footballdata",
                                fingerprint=compute_fingerprint(home_team, away_team, kickoff, league),
                                opening_odds_home=odds_data.get("homeWin"),
                                opening_odds_draw=odds_data.get("draw"),
                                opening_odds_away=odds_data.get("awayWin"),
                            ))
                            stored += 1
                    elif r.status_code == 429:
                        logger.warning(f"Rate limit hit for {league}")
                        rate_limited_leagues.append(league)
                except Exception as e:
                    logger.error(f"Sync failed for {league}: {e}")
                    # Continue with other leagues rather than aborting the whole sync
            try:
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"DB commit failed during sync: {e}")
                raise HTTPException(status_code=500, detail=f"DB commit failed: {e}")

    from sqlalchemy import func as _func
    async with AsyncSessionLocal() as _db:
        _existing_count = (await _db.execute(select(_func.count(Match.id)))).scalar_one()

    if stored == 0:
        msg = (f"No new fixtures in window {date_from} → {date_to}. "
               f"{_existing_count} fixtures already in database. "
               f"{skipped_existing} duplicates by external_id, "
               f"{skipped_dedup} duplicates by fingerprint.")
        source_label = "existing"
    else:
        msg = f"Synced {stored} new fixtures from Football-Data API"
        source_label = "footballdata"

    return {
        "stored": stored,
        "skipped_existing": skipped_existing,
        "skipped_dedup": skipped_dedup,
        "rate_limited_leagues": rate_limited_leagues,
        "source": source_label,
        "existing_total": _existing_count,
        "window": f"{date_from} → {date_to}",
        "message": msg,
    }
