from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import os
import asyncio

from app.db.database import get_db, AsyncSessionLocal
from app.core.cache_keys import FIXTURE_LIST
from app.db.models import Match, Prediction
from app.services.isports_api import ISportsClient, ISPORTS_LEAGUE_IDS
from app.services.sportsdb_api import sync_upcoming_fixtures
from app.modules.wallet.models import PlatformConfig
from app.core.cache import cache
import random
from app.modules.ai.models import AIPredictionAudit
from app.services.deterministic_insights import generate_match_insights
from app.services.predict_features import build_predict_features

router = APIRouter(prefix="/matches", tags=["matches"])
logger = logging.getLogger(__name__)

LEAGUE_DISPLAY_NAMES = {
    "premier_league":       "Premier League",
    "la_liga":              "La Liga",
    "bundesliga":           "Bundesliga",
    "serie_a":              "Serie A",
    "ligue_1":              "Ligue 1",
    "champions_league":     "Champions League",
    "europa_league":        "Europa League",
    "eredivisie":           "Eredivisie",
    "primeira_liga":        "Primeira Liga",
    "championship":         "Championship",
    "scottish_premiership": "Scottish Premiership",
    "belgian_pro_league":   "Belgian Pro League",
    "super_lig":            "Süper Lig",
    "ekstraklasa":          "Ekstraklasa",
    "mls":                  "MLS",
    "liga_mx":              "Liga MX",
    "brasileirao":          "Brasileirão",
    "argentine_primera":    "Argentine Primera División",
    "nba":                  "NBA",
    "atp":                  "ATP World Tour",
    "wta":                  "WTA Tour",
    # legacy aliases
    "ucl": "Champions League",
    "uel": "Europa League",
}

COMPETITIONS = {
    # Domestic leagues
    "premier_league":   "PL",
    "la_liga":          "PD",
    "bundesliga":       "BL1",
    "serie_a":          "SA",
    "ligue_1":          "FL1",
    "eredivisie":       "DED",
    "championship":     "ELC",
    "primeira_liga":    "PPL",
    # European club competitions
    "champions_league": "CL",
    "europa_league":    "EL",
    # International tournaments — World Cup + Euros available when active
    "fifa_world_cup":   "WC",
    "uefa_euro":        "EC",
}

# DEFAULT_MARKETS list is externalised to app/config/markets.json
try:
    import json, os
    _markets_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'markets.json')
    if os.path.exists(_markets_path):
        with open(_markets_path, 'r') as _mf:
            DEFAULT_MARKETS = json.load(_mf)
    else:
        DEFAULT_MARKETS = []
except Exception:
    DEFAULT_MARKETS = []


def _fmt_league(league: str) -> str:
    return LEAGUE_DISPLAY_NAMES.get(league, league.replace("_", " ").title() if league else "Unknown")


async def _load_markets(db: AsyncSession) -> list:
    row = (await db.execute(select(PlatformConfig).where(PlatformConfig.key == "markets_config"))).scalar_one_or_none()
    return row.value if row and isinstance(row.value, list) else DEFAULT_MARKETS


def _active_market_ids(markets: Optional[list]) -> set:
    source = markets if markets else DEFAULT_MARKETS
    return {str(m.get("id")) for m in source if m.get("status") == "active"}


def _vig_free_probs(home_odds, draw_odds, away_odds) -> Optional[dict]:
    """
    Calculate vig-free probabilities from decimal odds.
    Supports both 3-way (Home/Draw/Away) and 2-way (Home/Away) markets.
    """
    try:
        h = float(home_odds) if home_odds else 0
        a = float(away_odds) if away_odds else 0
        if h <= 1.0 or a <= 1.0:
            return None

        inv_h = 1.0 / h
        inv_a = 1.0 / a
        inv_d = 0.0

        if draw_odds:
            try:
                d = float(draw_odds)
                if d > 1.0:
                    inv_d = 1.0 / d
            except (TypeError, ValueError):
                pass

        total = inv_h + inv_d + inv_a
        if total <= 0:
            return None

        return {
            "home": inv_h / total,
            "draw": inv_d / total if inv_d > 0 else 0.0,
            "away": inv_a / total
        }
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
    elif odds_home and pred and pred.home_prob is not None:
        market_prob = 1.0 / odds_home
        edge = round(float(pred.home_prob) - market_prob, 4)

    # Market-implied probabilities are not model predictions. Keep the
    # prediction fields unavailable until a Prediction row supplies them.
    home_prob = float(pred.home_prob) if pred and pred.home_prob is not None else None
    draw_prob = float(pred.draw_prob) if pred and pred.draw_prob is not None else None
    away_prob = float(pred.away_prob) if pred and pred.away_prob is not None else None

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
    confidence = float(pred.confidence) if pred and pred.confidence is not None else None

    return {
        "match_id": m.id,
        "external_id": m.external_id,
        "home_team": m.home_team,
        "away_team": m.away_team,
        "league": _fmt_league(m.league) if m.league else "Unknown",
        "league_key": m.league or "unknown",
        "kickoff_time": m.kickoff_time.isoformat() if m.kickoff_time else None,
        "status": m.status or "upcoming",
        "source": m.source or "unknown",
        "sport": getattr(m, "sport", None) or "football",
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
        "edge": edge,
    }


@router.get("")
@router.get("/")
async def get_matches(
    league: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    _cache_key = f"{FIXTURE_LIST}:{league}:{status}:{sport}"
    try:
        _cached = await cache.get(_cache_key)
        if _cached:
            return _cached
    except Exception:
        pass
    try:
        # If DB is empty, attempt a quick fixture sync so `/api/matches` can return results
        try:
            existing_count = (await db.execute(select(func.count(Match.id)))).scalar_one()
        except Exception:
            existing_count = 0

        if existing_count == 0:
            try:
                from app.services.sportsdb_api import sync_upcoming_fixtures as _sdb_sync
                async with AsyncSessionLocal() as sdb_db:
                    await _sdb_sync(sdb_db, days_ahead=7)
                # refresh count after sync
                existing_count = (await db.execute(select(func.count(Match.id)))).scalar_one()
            except Exception as _sync_e:
                logger.warning(f"Auto-sync attempt failed: {_sync_e}")

        stmt = select(Match, Prediction).outerjoin(
            Prediction,
            and_(
                Match.id == Prediction.match_id,
                # If multiple predictions exist, we'll take the most recent one
                # using a subquery or by ordering in Python later.
            )
        )
        if league:
            stmt = stmt.where(Match.league == league)
        if status:
            stmt = stmt.where(Match.status == status)
        if sport:
            stmt = stmt.where(Match.sport == sport.lower().replace(" ", "_"))

        stmt = stmt.order_by(Match.kickoff_time.asc())
        result = await db.execute(stmt)
        rows = result.all()

        # Deduplicate matches if multiple predictions exist
        match_map = {}
        markets = await _load_markets(db)

        for m, p in rows:
            if m.id not in match_map:
                match_map[m.id] = (m, p)
            else:
                # Keep the latest prediction
                _, existing_p = match_map[m.id]
                if p and (not existing_p or p.timestamp > existing_p.timestamp):
                    match_map[m.id] = (m, p)

        res = [_fmt_match(m, p, markets) for m, p in match_map.values()]
        try:
            await cache.set(_cache_key, res, ttl=300)
        except Exception:
            pass
        return res
    except Exception as e:
        logger.warning(f"get_matches DB error: {e}")
        return []


@router.get("/upcoming")
async def get_upcoming_matches(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    _cache_key = f"{FIXTURE_LIST}:upcoming:{sport}"
    _cached = await cache.get(_cache_key)
    if _cached: return _cached
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Match.status.in_(["upcoming", "scheduled"])
    # Sort by kickoff time
    stmt = (
        select(Match, Prediction)
        .outerjoin(Prediction, Match.id == Prediction.match_id)
        .where(Match.kickoff_time >= now - timedelta(hours=2))
        .where(Match.actual_outcome.is_(None))
        .order_by(Match.kickoff_time.asc())
    )
    if sport:
        stmt = stmt.where(Match.sport == sport.lower().replace(" ", "_"))
    result = await db.execute(stmt)
    rows = result.all()

    match_map = {}
    markets = await _load_markets(db)
    for m, p in rows:
        if m.id not in match_map:
            match_map[m.id] = (m, p)
        else:
            _, existing_p = match_map[m.id]
            if p and (not existing_p or p.timestamp > existing_p.timestamp):
                match_map[m.id] = (m, p)

    res = [_fmt_match(m, p, markets) for m, p in match_map.values()]
    await cache.set(_cache_key, res, ttl=300)
    return res


async def _recent_form(db: AsyncSession, team: str, before: datetime) -> dict:
    # Last 5 matches for this team
    stmt = (
        select(Match)
        .where(or_(Match.home_team == team, Match.away_team == team))
        .where(Match.kickoff_time < before)
        .where(Match.actual_outcome.isnot(None))
        .order_by(Match.kickoff_time.desc())
        .limit(5)
    )
    res = await db.execute(stmt)
    matches = res.scalars().all()
    form = []
    for m in matches:
        if m.actual_outcome == "draw":
            form.append("D")
        elif (m.home_team == team and m.actual_outcome == "home") or \
             (m.away_team == team and m.actual_outcome == "away"):
            form.append("W")
        else:
            form.append("L")

    return {
        "results": form,
        "form": "".join(form) if form else "N/A",
        "matches": [
            {
                "home": m.home_team,
                "away": m.away_team,
                "score": f"{m.home_goals}-{m.away_goals}" if m.home_goals is not None else None,
                "outcome": m.actual_outcome,
                "date": m.kickoff_time.isoformat()
            }
            for m in matches
        ]
    }


async def _head_to_head(db: AsyncSession, m: Match) -> dict:
    stmt = (
        select(Match)
        .where(or_(
            and_(Match.home_team == m.home_team, Match.away_team == m.away_team),
            and_(Match.home_team == m.away_team, Match.away_team == m.home_team)
        ))
        .where(Match.actual_outcome.isnot(None))
        .where(Match.id != m.id)
        .order_by(Match.kickoff_time.desc())
        .limit(5)
    )
    res = await db.execute(stmt)
    matches = res.scalars().all()

    home_wins = sum(1 for match in matches if (match.home_team == m.home_team and match.actual_outcome == "home") or (match.away_team == m.home_team and match.actual_outcome == "away"))
    away_wins = sum(1 for match in matches if (match.home_team == m.away_team and match.actual_outcome == "home") or (match.away_team == m.away_team and match.actual_outcome == "away"))
    draws = sum(1 for match in matches if match.actual_outcome == "draw")

    return {
        "count": len(matches),
        "home_wins": home_wins,
        "away_wins": away_wins,
        "draws": draws,
        "matches": [
            {
                "home": match.home_team,
                "away": match.away_team,
                "score": f"{match.home_goals}-{match.away_goals}" if match.home_goals is not None else None,
                "outcome": match.actual_outcome,
                "date": match.kickoff_time.isoformat()
            }
            for match in matches
        ]
    }


@router.get("/explore")
async def explore_markets(db: AsyncSession = Depends(get_db)):
    # Group by league
    stmt = select(Match.league, func.count(Match.id)).where(Match.actual_outcome.is_(None)).group_by(Match.league)
    res = await db.execute(stmt)
    leagues = []
    for l, count in res.all():
        leagues.append({
            "id": l,
            "name": _fmt_league(l),
            "count": count
        })
    return leagues


@router.get("/live")
async def get_live_matches(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    _cache_key = f"{FIXTURE_LIST}:live:{sport}"
    _cached = await cache.get(_cache_key)
    if _cached: return _cached
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # A match is "live" if it started less than 2 hours ago and has no outcome yet
    stmt = (
        select(Match, Prediction)
        .outerjoin(Prediction, Match.id == Prediction.match_id)
        .where(Match.kickoff_time <= now)
        .where(Match.kickoff_time >= now - timedelta(hours=2))
        .where(Match.actual_outcome.is_(None))
        .order_by(Match.kickoff_time.desc())
    )
    if sport:
        stmt = stmt.where(Match.sport == sport.lower().replace(" ", "_"))
    result = await db.execute(stmt)
    rows = result.all()
    match_map = {}
    markets = await _load_markets(db)
    for m, p in rows:
        if m.id not in match_map:
            match_map[m.id] = (m, p)
    res = [_fmt_match(m, p, markets) for m, p in match_map.values()]
    await cache.set(_cache_key, res, ttl=300)
    return res


@router.get("/recent")
async def get_recent_matches(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    _cache_key = f"{FIXTURE_LIST}:recent:{sport}"
    _cached = await cache.get(_cache_key)
    if _cached: return _cached
    # Last 20 completed matches
    stmt = (
        select(Match, Prediction)
        .outerjoin(Prediction, Match.id == Prediction.match_id)
        .where(Match.actual_outcome.isnot(None))
        .order_by(Match.kickoff_time.desc())
        .limit(20)
    )
    if sport:
        stmt = stmt.where(Match.sport == sport.lower().replace(" ", "_"))
    result = await db.execute(stmt)
    rows = result.all()
    match_map = {}
    markets = await _load_markets(db)
    for m, p in rows:
        if m.id not in match_map:
            match_map[m.id] = (m, p)
    res = [_fmt_match(m, p, markets) for m, p in match_map.values()]
    await cache.set(_cache_key, res, ttl=300)
    return res


@router.get("/completed")
async def get_completed_matches(
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    _cache_key = f"{FIXTURE_LIST}:completed:{limit}"
    _cached = await cache.get(_cache_key)
    if _cached: return _cached
    stmt = (
        select(Match, Prediction)
        .outerjoin(Prediction, Match.id == Prediction.match_id)
        .where(Match.actual_outcome.isnot(None))
        .order_by(Match.kickoff_time.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    match_map = {}
    markets = await _load_markets(db)
    for m, p in rows:
        if m.id not in match_map:
            match_map[m.id] = (m, p)
    res = [_fmt_match(m, p, markets) for m, p in match_map.values()]
    await cache.set(_cache_key, res, ttl=300)
    return res


@router.get("/leagues/list")
async def list_leagues(db: AsyncSession = Depends(get_db)):
    stmt = select(Match.league).distinct()
    res = await db.execute(stmt)
    leagues = res.scalars().all()
    return [
        {"id": l, "name": _fmt_league(l)}
        for l in leagues if l
    ]


@router.get("/sync/status")
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    count = (await db.execute(select(func.count(Match.id)))).scalar_one()
    last = (await db.execute(select(Match).order_by(Match.created_at.desc()).limit(1))).scalar_one_or_none()
    return {
        "total_fixtures": count,
        "last_sync": last.created_at.isoformat() if last else None,
        "status": "healthy"
    }


@router.get("/markets/enabled")
async def get_enabled_markets(db: AsyncSession = Depends(get_db)):
    return await _load_markets(db)



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

    # Fetch Audit for detailed model breakdown
    audit_q = await db.execute(
        select(AIPredictionAudit)
        .where(AIPredictionAudit.match_id == str(match_id))
        .order_by(AIPredictionAudit.created_at.desc())
    )
    latest_audit = audit_q.scalar_one_or_none()

    markets = await _load_markets(db)
    latest = _fmt_match(match, latest_pred, markets)
    h = latest.get("home_prob")
    d = latest.get("draw_prob")
    a = latest.get("away_prob")

    # Fetch deeper features (Elo, etc)
    features = await build_predict_features(db, match.home_team, match.away_team, match.league)
    elo_diff = features.get("elo_diff", 0.0)

    # Tactical Insights (Native SCIE)
    has_primary_probabilities = h is not None and d is not None and a is not None
    if not has_primary_probabilities:
        tactical_insights = {
            "summary": "Prediction unavailable until model output is generated.",
            "key_factors": [],
            "recommendation": "No recommendation available.",
        }
    else:
        try:
            tactical_insights = await generate_match_insights(
                home_team=match.home_team,
                away_team=match.away_team,
                league=match.league or "unknown",
                home_prob=h,
                draw_prob=d,
                away_prob=a,
                over_25_prob=float(latest.get("over_25_prob") or 0.5),
                btts_prob=float(latest.get("btts_prob") or 0.5),
                bet_side=getattr(latest_pred, 'bet_side', None),
                edge=float(latest.get("edge") or 0.0),
                entry_odds=float(latest.get("odds", {}).get("home") or 2.0),
                confidence=float(getattr(latest_pred, 'confidence', 0.5) or 0.5),
            )
        except Exception as e:
            logger.error(f"Tactical insight generation failed: {e}")
            tactical_insights = {
                "summary": "Intelligence gathering in progress.",
                "key_factors": [],
                "recommendation": "Monitor market movements."
            }

    return {
        **latest,
        "intelligence": {
            "consensus": {
                "home_prob": float(h) if h is not None else None,
                "draw_prob": float(d) if d is not None else None,
                "away_prob": float(a) if a is not None else None,
                "confidence": float(getattr(latest_pred, 'confidence', 0.0)) if latest_pred and getattr(latest_pred, 'confidence', None) is not None else None,
                "risk_score": float(getattr(latest_audit, 'risk_score', 0.0)) if latest_audit and getattr(latest_audit, 'risk_score', None) is not None else None,
                "model_agreement": float(getattr(latest_audit, 'model_agreement', 0.0)) if latest_audit and getattr(latest_audit, 'model_agreement', None) is not None else None,
                "models_active": int(getattr(latest_audit, 'pkl_models_active', 0)) if latest_audit and getattr(latest_audit, 'pkl_models_active', None) is not None else None,
                "elo_diff": float(elo_diff),
                "squad_value_diff": round(float(elo_diff) * 1.2, 2),
                "timestamp": latest_pred.timestamp.isoformat() if (latest_pred and getattr(latest_pred, 'timestamp', None)) else None,
            },
            "attribution": getattr(latest_audit, 'individual_results', None) or getattr(latest_pred, 'model_insights', []) or [],
            "tactical": tactical_insights,
            "radar_data": [
                {"subject": "Attacking", "A": 80 + (elo_diff / 10 if elo_diff > 0 else 0), "B": 80 + (-elo_diff / 10 if elo_diff < 0 else 0), "fullMark": 100},
                {"subject": "Defensive", "A": 75 + (elo_diff / 15 if elo_diff > 0 else 0), "B": 75 + (-elo_diff / 15 if elo_diff < 0 else 0), "fullMark": 100},
                {"subject": "Possession", "A": 70 + (elo_diff / 12 if elo_diff > 0 else 0), "B": 70 + (-elo_diff / 12 if elo_diff < 0 else 0), "fullMark": 100},
                {"subject": "Pressing", "A": 85, "B": 82, "fullMark": 100},
                {"subject": "Transition", "A": 78, "B": 88, "fullMark": 100},
                {"subject": "Set Pieces", "A": 65, "B": 70, "fullMark": 100},
            ],
            "market_edge": {
                "ai_prob": float(max(h, d, a)) if has_primary_probabilities else None,
                "bookmaker_prob": 1.0 / float(latest.get("odds", {}).get(getattr(latest_pred, 'bet_side', None)) or 2.0) if (latest_pred and getattr(latest_pred, 'bet_side', None) and latest.get("odds", {}).get(latest_pred.bet_side)) else None,
                "edge": float(latest["edge"]) if latest.get("edge") is not None else None,
                "expected_roi": float(latest["edge"]) * 100 if latest.get("edge") is not None else None,
                "kelly_stake": float(getattr(latest_pred, 'recommended_stake', 0.0)) if latest_pred and getattr(latest_pred, 'recommended_stake', None) is not None else None,
            }
        },
        "predictions_count": len(preds),
        "enabled_markets": markets,
        "recent_form": {
            "home": await _recent_form(db, team=match.home_team, before=match.kickoff_time),
            "away": await _recent_form(db, team=match.away_team, before=match.kickoff_time),
        },
        "h2h": await _head_to_head(db, match),
    }

@router.get("/{match_id}/analytics")
async def get_match_analytics(match_id: int, db: AsyncSession = Depends(get_db)):
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    pred = (await db.execute(
        select(Prediction).where(Prediction.match_id == match_id).order_by(Prediction.timestamp.desc()).limit(1)
    )).scalar_one_or_none()

    audit = (await db.execute(
        select(AIPredictionAudit).where(AIPredictionAudit.match_id == str(match_id)).order_by(AIPredictionAudit.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    markets = await _load_markets(db)
    fmt = _fmt_match(match, pred, markets)

    return {
        "match": fmt,
        "prediction": {
            "side": pred.bet_side if pred else None,
            "confidence": float(pred.confidence or 0.5) if pred else 0.5,
            "edge": float(pred.vig_free_edge or 0.0) if pred else 0.0,
            "risk_score": float(audit.risk_score or 0.0) if audit else 0.0,
            "model_agreement": float(audit.model_agreement or 0.0) if audit else 0.0,
        } if pred else None,
        "market_efficiency": "High" if fmt.get("odds", {}).get("draw") else "Medium",
    }


@router.get("/{match_id}/ensemble")
async def get_ensemble_breakdown(match_id: int, db: AsyncSession = Depends(get_db)):
    """
    Detailed breakdown of how the ensemble reached its conclusion.
    """
    pred = (await db.execute(
        select(Prediction).where(Prediction.match_id == match_id).order_by(Prediction.timestamp.desc()).limit(1)
    )).scalar_one_or_none()

    if not pred:
        return {"error": "No prediction yet", "match_id": match_id}

    return {
        "match_id": match_id,
        "model_contributions": pred.model_insights or [],
        "weights": pred.model_weights or {},
        "timestamp": pred.timestamp.isoformat() if pred.timestamp else None,
    }


@router.post("/sync")
async def sync_fixtures(
    days: int = Query(default=60, ge=1, le=90),
):
    """
    Fetch and store upcoming fixtures.

    Strategy (two-phase, always runs both):
    1. Football-Data.org  — used when FOOTBALL_DATA_API_KEY is set; covers the
       top 8 European leagues up to `days` ahead.
    2. TheSportsDB        — free, no key required; covers 18 leagues via season
       schedule + day-by-day scan. Runs regardless of Football-Data status so
       the database always gets populated.

    Deduplication: external_id first, then date::home::away::league fingerprint.
    Manually-uploaded or seeded fixtures are never overwritten.
    """
    import httpx
    from app.data.match_dedup import compute_fingerprint, find_existing_match
    from app.services.sportsdb_api import sync_upcoming_fixtures as _sdb_sync

    football_key = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(days=1)
    date_from = tomorrow.strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=days)).strftime("%Y-%m-%d")

    stored_fd = 0
    skipped_existing = 0
    skipped_dedup = 0
    rate_limited_leagues: list[str] = []
    fd_source_used = False

    # ── Phase 0: iSports API (Primary Fixture Source) ───────────────────────
    isports_key = os.getenv("ISPORTS_API_KEY", "")
    if isports_key:
        try:
            client = ISportsClient(isports_key)

            async def fetch_and_process_league(l_name, l_id):
                local_count = 0
                try:
                    raw_matches = await client.get_fixtures_and_results(l_id)
                    from app.data.match_dedup import compute_fingerprint
                    async with AsyncSessionLocal() as db_inner:
                        for m in raw_matches:
                            # status 0 is not started
                            if str(m.get("status")) == "0":
                                formatted = client.format_match_data(m, l_name)
                                # Find or create
                                try:
                                    kickoff = datetime.fromisoformat(formatted["kickoff"].replace("Z", "+00:00")).replace(tzinfo=None)
                                except Exception:
                                    continue

                                stmt = select(Match).where(
                                    Match.home_team == formatted["home_team"],
                                    Match.away_team == formatted["away_team"],
                                    Match.kickoff_time >= kickoff - timedelta(hours=24),
                                    Match.kickoff_time <= kickoff + timedelta(hours=24)
                                )
                                existing = (await db_inner.execute(stmt)).scalar_one_or_none()

                                if not existing:
                                    new_m = Match(
                                        home_team=formatted["home_team"],
                                        away_team=formatted["away_team"],
                                        league=formatted["league"],
                                        kickoff_time=kickoff,
                                        status="scheduled",
                                        source="isports",
                                        fingerprint=compute_fingerprint(
                                            formatted["home_team"], formatted["away_team"], kickoff, formatted["league"]
                                        )
                                    )
                                    db_inner.add(new_m)
                                    local_count += 1
                        await db_inner.commit()
                except Exception as le:
                    logger.error(f"iSports sync failed for {l_name}: {le}")
                return local_count

            tasks = [fetch_and_process_league(name, lid) for name, lid in ISPORTS_LEAGUE_IDS.items()]
            results = await asyncio.gather(*tasks)
            stored_isports = sum(results)
            logger.info(f"iSports Phase 0 synced {stored_isports} matches")
            stored_isports_val = stored_isports # For final reporting consistency
            stored_fd += stored_isports_val
        except Exception as e:
            logger.error(f"iSports Phase 0 failed: {e}")

    # ── Phase 1: Football-Data.org ──────────────────────────────────────────
    if football_key:
        fd_source_used = True
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
                                    kickoff = datetime.fromisoformat(
                                        kickoff_str.replace("Z", "+00:00")
                                    ).replace(tzinfo=None)
                                except Exception:
                                    continue
                                home_team = m["homeTeam"]["name"]
                                away_team = m["awayTeam"]["name"]

                                existing = (await db.execute(
                                    select(Match).where(Match.external_id == ext_id)
                                )).scalar_one_or_none()
                                if existing:
                                    skipped_existing += 1
                                    continue
                                existing_fp = await find_existing_match(
                                    db, home_team, away_team, kickoff, league
                                )
                                if existing_fp:
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
                                    fingerprint=compute_fingerprint(
                                        home_team, away_team, kickoff, league
                                    ),
                                    opening_odds_home=odds_data.get("homeWin"),
                                    opening_odds_draw=odds_data.get("draw"),
                                    opening_odds_away=odds_data.get("awayWin"),
                                ))
                                stored_fd += 1
                        elif r.status_code == 429:
                            logger.warning(f"Rate limit hit for {league}")
                            rate_limited_leagues.append(league)
                    except Exception as e:
                        logger.error(f"Sync failed for {league}: [{type(e).__name__}] {e!r}")
                try:
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    logger.error(f"DB commit failed during Football-Data sync: {e}")

    # ── Phase 2: TheSportsDB (always runs) ──────────────────────────────────
    sdb_result: dict = {"inserted": 0, "updated": 0, "skipped": 0, "total_fetched": 0}
    try:
        async with AsyncSessionLocal() as sdb_db:
            sdb_result = await _sdb_sync(sdb_db, days_ahead=days)
    except Exception as sdb_err:
        logger.error(f"TheSportsDB sync error: {sdb_err}")

    # ── Summary ─────────────────────────────────────────────────────────────
    from sqlalchemy import func as _func
    async with AsyncSessionLocal() as _db:
        _existing_count = (
            await _db.execute(select(_func.count(Match.id)))
        ).scalar_one()

    total_new = stored_fd + sdb_result["inserted"]
    sources_used = []
    if fd_source_used:
        sources_used.append("football-data.org")
    sources_used.append("thesportsdb")

    return {
        "stored": total_new,
        "football_data_new": stored_fd,
        "sportsdb_new": sdb_result["inserted"],
        "sportsdb_updated": sdb_result["updated"],
        "sportsdb_fetched": sdb_result["total_fetched"],
        "skipped_existing": skipped_existing + sdb_result["skipped"],
        "skipped_dedup": skipped_dedup,
        "rate_limited_leagues": rate_limited_leagues,
        "sources": sources_used,
        "existing_total": _existing_count,
        "window": f"{date_from} → {date_to}",
        "message": (
            f"Synced {total_new} new fixtures "
            f"({stored_fd} from Football-Data, {sdb_result['inserted']} from TheSportsDB). "
            f"{_existing_count} total fixtures in database."
        ),
    }
