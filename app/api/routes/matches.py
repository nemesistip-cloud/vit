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
from app.modules.ai.models import AIPredictionAudit
from app.services.deterministic_insights import generate_match_insights
from app.services.predict_features import build_predict_features, _team_search_terms
from app.services.odds_provider import NormalizedOdds, OddsIntelligence, default_provider_registry, OddsFreshness
from app.services.evidence_engine import EvidenceEngine, PredictionClassification

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
    active = {str(m.get("id")) for m in source if m.get("status") == "active"}
    if not active:
        return {"1x2", "over_under_25", "over_under", "btts", "dnb", "over_under_15", "over_under_35"}
    return active


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
    # Secondary markets are predictions in their own right. They must come
    # from the stored model response, never from 1X2 probabilities or odds.
    return {
        "over_25": None, "under_25": None, "btts": None, "no_btts": None,
        "over_15": None, "under_15": None, "over_35": None, "under_35": None,
        "dnb_home": None, "dnb_away": None,
    }


def _normalize_attribution_items(raw_items: Optional[list]) -> list:
    if not raw_items:
        return []

    normalized = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue

        confidence = item.get("confidence")
        if isinstance(confidence, dict):
            scalar_conf = confidence.get("1x2")
            if scalar_conf is None:
                scalar_conf = confidence.get("home") or confidence.get("draw") or confidence.get("away")
        else:
            scalar_conf = confidence

        try:
            scalar_conf = float(scalar_conf) if scalar_conf is not None else None
        except (TypeError, ValueError):
            scalar_conf = None

        bet_side = item.get("bet_side")
        if not bet_side:
            probs = {
                key: item.get(f"{key}_prob")
                for key in ("home", "draw", "away")
                if item.get(f"{key}_prob") is not None
            }
            if probs:
                bet_side = max(probs.items(), key=lambda kv: kv[1])[0]

        normalized.append({
            "model_name": item.get("model_name") or item.get("name") or "Model",
            "model_type": item.get("model_type"),
            "bet_side": bet_side,
            "confidence": scalar_conf,
            "final_ev": item.get("final_ev") or item.get("edge"),
            "entry_odds": item.get("entry_odds"),
            "reasoning": item.get("reasoning") or item.get("explanation") or item.get("notes"),
            "accuracy_overall": item.get("accuracy_overall"),
            "model_weight": item.get("model_weight"),
            "supported_markets": item.get("supported_markets", []),
            "home_prob": item.get("home_prob"),
            "draw_prob": item.get("draw_prob"),
            "away_prob": item.get("away_prob"),
        })

    return normalized


def _fmt_match(m: Match, pred: Optional[Prediction] = None, markets: Optional[list] = None) -> dict:
    if pred is not None and getattr(pred, "is_seed", False):
        pred = None
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

    over_25_prob = float(pred.over_25_prob) if pred and pred.over_25_prob is not None else None
    under_25_prob = float(pred.under_25_prob) if pred and pred.under_25_prob is not None else None
    btts_prob = float(pred.btts_prob) if pred and pred.btts_prob is not None else None
    no_btts_prob = float(pred.no_btts_prob) if pred and pred.no_btts_prob is not None else None
    over_15_prob = None
    under_15_prob = None
    over_35_prob = None
    under_35_prob = None
    dnb_home_prob = None
    dnb_away_prob = None
    confidence = float(pred.confidence) if pred and pred.confidence is not None else None

    bet_side = getattr(pred, 'bet_side', None)
    if not bet_side and (home_prob is not None or draw_prob is not None or away_prob is not None):
        hp = home_prob if home_prob is not None else -1.0
        dp = draw_prob if draw_prob is not None else -1.0
        ap = away_prob if away_prob is not None else -1.0
        if hp >= dp and hp >= ap:
            bet_side = 'home'
        elif ap >= dp:
            bet_side = 'away'
        else:
            bet_side = 'draw'

    return {
        "bet_side": bet_side,
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
        # Match rows are database snapshots. They are provider-sourced, but
        # must not be labelled LIVE unless a request-time provider refresh
        # actually occurred.
        "data_status": "CACHED" if m.source in {"isports", "sportsdb", "footballdata", "football-data.org"} else "UNAVAILABLE",
        "data_provenance": {
            "data_source": m.source or "unknown",
            "source_type": "provider_cache" if m.source in {"isports", "sportsdb", "footballdata", "football-data.org"} else "unverified",
            "retrieved_at": getattr(m, "updated_at", None).isoformat() if getattr(m, "updated_at", None) else None,
            "fallback_used": False,
        },
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
        if not res and not league and not status:
            try:
                async with AsyncSessionLocal() as sync_db:
                    await sync_upcoming_fixtures(sync_db, days_ahead=7)
                result = await db.execute(stmt)
                rows = result.all()
                match_map = {}
                for m, p in rows:
                    if m.id not in match_map:
                        match_map[m.id] = (m, p)
                    else:
                        _, existing_p = match_map[m.id]
                        if p and (not existing_p or p.timestamp > existing_p.timestamp):
                            match_map[m.id] = (m, p)
                res = [_fmt_match(m, p, markets) for m, p in match_map.values()]
            except Exception as sync_err:
                logger.warning(f"Auto-sync fallback failed: {sync_err}")

        try:
            await cache.set(_cache_key, res, ttl=300)
        except Exception:
            pass
        return res
    except Exception as e:
        logger.exception("get_matches database read failed")
        raise HTTPException(
            status_code=503,
            detail={"code": "SPORTS_DATA_UNAVAILABLE", "message": "Sports data is temporarily unavailable"},
        ) from e


@router.get("/upcoming")
async def get_upcoming_matches(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        _cache_key = f"{FIXTURE_LIST}:upcoming:{sport}"
        _cached = await cache.get(_cache_key)
        if _cached is not None:
            return _cached
        now = datetime.now(timezone.utc).replace(tzinfo=None)
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
    except Exception as e:
        logger.exception("get_upcoming_matches database read failed")
        raise HTTPException(
            status_code=503,
            detail={"code": "SPORTS_DATA_UNAVAILABLE", "message": "Upcoming sports data is temporarily unavailable"},
        ) from e


async def _recent_form(db: AsyncSession, team: str, before: datetime) -> dict:
    terms = _team_search_terms(team)
    conditions = []
    for term in terms:
        conditions.append(Match.home_team.ilike(f'%{term}%'))
        conditions.append(Match.away_team.ilike(f'%{term}%'))

    stmt = (
        select(Match)
        .where(or_(*conditions))
        .where(Match.kickoff_time < before)
        .where(or_(Match.actual_outcome.isnot(None), and_(Match.home_goals.isnot(None), Match.away_goals.isnot(None))))
        .order_by(Match.kickoff_time.desc())
        .limit(5)
    )
    res = await db.execute(stmt)
    matches = res.scalars().all()
    form = []
    for m in matches:
        outcome = m.actual_outcome
        if not outcome and m.home_goals is not None and m.away_goals is not None:
            if m.home_goals > m.away_goals:
                outcome = 'home'
            elif m.home_goals < m.away_goals:
                outcome = 'away'
            else:
                outcome = 'draw'

        if outcome == 'draw':
            form.append('D')
        elif any(t.lower() in m.home_team.lower() for t in terms) and outcome == 'home':
            form.append('W')
        elif any(t.lower() in m.away_team.lower() for t in terms) and outcome == 'away':
            form.append('W')
        else:
            form.append('L')

    return {
        'results': form,
        'form': ''.join(form) if form else 'N/A',
        'matches_played': len(matches),
        'matches': [
            {
                'home': m.home_team,
                'away': m.away_team,
                'score': f'{m.home_goals}-{m.away_goals}' if m.home_goals is not None else None,
                'outcome': m.actual_outcome,
                'date': m.kickoff_time.isoformat() if m.kickoff_time else None
            }
            for m in matches
        ]
    }


async def _head_to_head(db: AsyncSession, m: Match) -> dict:
    home_terms = _team_search_terms(m.home_team)
    away_terms = _team_search_terms(m.away_team)
    home_conds = [or_(Match.home_team.ilike(f'%{t}%'), Match.away_team.ilike(f'%{t}%')) for t in home_terms]
    away_conds = [or_(Match.home_team.ilike(f'%{t}%'), Match.away_team.ilike(f'%{t}%')) for t in away_terms]

    stmt = (
        select(Match)
        .where(and_(
            or_(*home_conds),
            or_(*away_conds),
            or_(Match.actual_outcome.isnot(None), and_(Match.home_goals.isnot(None), Match.away_goals.isnot(None)))
        ))
        .where(Match.id != m.id)
        .order_by(Match.kickoff_time.desc())
        .limit(5)
    )
    res = await db.execute(stmt)
    matches = res.scalars().all()

    home_wins = 0
    away_wins = 0
    draws = 0

    for match in matches:
        outcome = match.actual_outcome
        if not outcome and match.home_goals is not None and match.away_goals is not None:
            if match.home_goals > match.away_goals:
                outcome = 'home'
            elif match.home_goals < match.away_goals:
                outcome = 'away'
            else:
                outcome = 'draw'

        if outcome == 'draw':
            draws += 1
        elif any(t.lower() in match.home_team.lower() for t in home_terms) and outcome == 'home':
            home_wins += 1
        elif any(t.lower() in match.away_team.lower() for t in home_terms) and outcome == 'away':
            home_wins += 1
        else:
            away_wins += 1

    return {
        'count': len(matches),
        'matches_played': len(matches),
        'home_wins': home_wins,
        'away_wins': away_wins,
        'draws': draws,
        'matches': [
            {
                'home': match.home_team,
                'away': match.away_team,
                'score': f'{match.home_goals}-{match.away_goals}' if match.home_goals is not None else None,
                'outcome': match.actual_outcome,
                'date': match.kickoff_time.isoformat() if match.kickoff_time else None
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
    try:
        _cache_key = f"{FIXTURE_LIST}:live:{sport}"
        _cached = await cache.get(_cache_key)
        if _cached is not None:
            return _cached

        from app.services.live_match_ingestion import live_ingestion_service
        ingested = await live_ingestion_service.fetch_and_normalize_all(force_refresh=True)
        live_list = ingested.get("live", [])

        if sport:
            sport_norm = sport.lower().replace(" ", "_")
            live_list = [m for m in live_list if (m.sport or "football").lower().replace(" ", "_") == sport_norm]

        markets = await _load_markets(db)

        # Collect db_match_ids to fetch predictions
        db_ids = [m.db_match_id for m in live_list if m.db_match_id]
        pred_map = {}
        if db_ids:
            pred_stmt = select(Prediction).where(Prediction.match_id.in_(db_ids)).order_by(Prediction.timestamp.desc())
            pred_rows = (await db.execute(pred_stmt)).scalars().all()
            for p in pred_rows:
                if p.match_id not in pred_map and not getattr(p, "is_seed", False):
                    pred_map[p.match_id] = p

        res = []
        for lm in live_list:
            pred = pred_map.get(lm.db_match_id) if lm.db_match_id else None
            home_prob = float(pred.home_prob) if pred and pred.home_prob is not None else None
            draw_prob = float(pred.draw_prob) if pred and pred.draw_prob is not None else None
            away_prob = float(pred.away_prob) if pred and pred.away_prob is not None else None
            confidence = float(pred.confidence) if pred and pred.confidence is not None else None
            bet_side = getattr(pred, "bet_side", None)
            entry_odds = getattr(pred, "entry_odds", None)

            match_id = lm.db_match_id if lm.db_match_id else abs(hash(lm.id)) % 1000000 + 100000

            res.append({
                "id": match_id,
                "match_id": match_id,
                "external_id": lm.provider_match_id,
                "home_team": lm.home,
                "away_team": lm.away,
                "league": _fmt_league(lm.league),
                "league_key": lm.league,
                "kickoff_time": lm.kickoff_time or datetime.now(timezone.utc).isoformat(),
                "status": "live",
                "minute": lm.minute,
                "period": lm.period,
                "home_score": lm.home_score,
                "away_score": lm.away_score,
                "home_goals": lm.home_score,
                "away_goals": lm.away_score,
                "stoppage_time": lm.stoppage_time,
                "home_red_cards": lm.home_red_cards,
                "away_red_cards": lm.away_red_cards,
                "home_yellow_cards": lm.home_yellow_cards,
                "away_yellow_cards": lm.away_yellow_cards,
                "events": lm.events,
                "stats": lm.stats,
                "sport": lm.sport,
                "source": lm.provider,
                "home_prob": home_prob,
                "draw_prob": draw_prob,
                "away_prob": away_prob,
                "confidence": confidence,
                "bet_side": bet_side,
                "entry_odds": entry_odds,
                "data_status": "LIVE",
                "data_provenance": {
                    "data_source": lm.provider,
                    "provider_match_id": lm.provider_match_id,
                    "retrieved_at": datetime.fromtimestamp(lm.source_timestamp, timezone.utc).isoformat(),
                    "last_successful_update": datetime.fromtimestamp(lm.last_successful_update, timezone.utc).isoformat(),
                    "fallback_used": lm.provider == "db",
                }
            })

        await cache.set(_cache_key, res, ttl=10)
        return res
    except Exception as e:
        logger.exception("get_live_matches read failed")
        raise HTTPException(
            status_code=503,
            detail={"code": "SPORTS_DATA_UNAVAILABLE", "message": "Live sports data is temporarily unavailable"},
        ) from e


@router.get("/recent")
async def get_recent_matches(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        _cache_key = f"{FIXTURE_LIST}:recent:{sport}"
        _cached = await cache.get(_cache_key)
        if _cached is not None:
            return _cached
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
    except Exception as e:
        logger.exception("get_recent_matches database read failed")
        raise HTTPException(
            status_code=503,
            detail={"code": "SPORTS_DATA_UNAVAILABLE", "message": "Recent sports data is temporarily unavailable"},
        ) from e


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
    all_preds = pred_q.scalars().all()
    # Seed/demo predictions are training artifacts and must not become the
    # prediction shown for a live provider fixture.
    preds = [p for p in all_preds if not getattr(p, "is_seed", False)]
    latest_pred = preds[0] if preds else None

    # Audit log lookup
    audit_q = await db.execute(
        select(AIPredictionAudit)
        .where(AIPredictionAudit.match_id == str(match_id))
        .order_by(AIPredictionAudit.created_at.desc())
    )
    latest_audit = audit_q.scalar_one_or_none()

    markets = await _load_markets(db)

    # Determine canonical prediction status
    if not latest_pred:
        prediction_status = "not_initialized"
    elif getattr(latest_pred, 'status', None) == "INITIALIZING":
        prediction_status = "initializing"
    elif getattr(latest_pred, 'status', None) == "FAILED":
        prediction_status = "failed"
    elif getattr(latest_pred, 'status', None) == "STALE":
        prediction_status = "stale"
    else:
        now = datetime.now(timezone.utc)
        ts = latest_pred.timestamp
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts and (now - ts).total_seconds() > 86400:
            prediction_status = "stale"
        else:
            prediction_status = "ready"

    is_seed = getattr(latest_pred, 'is_seed', False) if latest_pred else False
    prediction_source = getattr(latest_pred, 'source', "live_generated") if latest_pred else None

    latest = _fmt_match(match, latest_pred if prediction_status in ("ready", "stale") else None, markets)
    h = latest.get("home_prob")
    d = latest.get("draw_prob")
    a = latest.get("away_prob")

    features = await build_predict_features(db, match.home_team, match.away_team, match.league)
    elo_diff = features.get("elo_diff", 0.0)

    has_primary_probabilities = (prediction_status in ("ready", "stale")) and h is not None and d is not None and a is not None

    if not has_primary_probabilities:
        tactical_insights = {
            "summary": "Prediction has not been initialized for this match yet." if prediction_status == "not_initialized" else "Prediction calculation in progress...",
            "key_factors": [],
            "recommendation": "Click 'Initialize Prediction' to generate real-time AI insights." if prediction_status == "not_initialized" else "Please wait while the ensemble processes model outputs.",
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
                "summary": "Intelligence gathering complete.",
                "key_factors": [],
                "recommendation": "Monitor market movements."
            }

    return {
        **latest,
        "prediction_status": prediction_status,
        "prediction_source": prediction_source,
        "is_seed": is_seed,
        "job_id": getattr(latest_pred, 'job_id', None) if latest_pred else None,
        "error_message": getattr(latest_pred, 'error_message', None) if latest_pred else None,
        "evidence": {
            "score": (latest_pred.provenance or {}).get("evidence_score", 0.0) if (latest_pred and getattr(latest_pred, 'provenance', None)) else 0.0,
            "classification": (latest_pred.provenance or {}).get("evidence_classification", "UNAVAILABLE") if (latest_pred and getattr(latest_pred, 'provenance', None)) else "UNAVAILABLE",
            "breakdown": (latest_pred.provenance or {}).get("evidence_breakdown", {}) if (latest_pred and getattr(latest_pred, 'provenance', None)) else {},
            "checklist": (latest_pred.provenance or {}).get("checklist", {}) if (latest_pred and getattr(latest_pred, 'provenance', None)) else {},
            "odds_consensus": (latest_pred.provenance or {}).get("odds_consensus", {}) if (latest_pred and getattr(latest_pred, 'provenance', None)) else {},
            "bookmaker_count": (latest_pred.provenance or {}).get("bookmaker_count", 0) if (latest_pred and getattr(latest_pred, 'provenance', None)) else 0,
            "missing_elements": (latest_pred.provenance or {}).get("missing_elements", []) if (latest_pred and getattr(latest_pred, 'provenance', None)) else [],
        },
        "provenance": getattr(latest_pred, 'provenance', None) if latest_pred else None,
        "intelligence": {
            "consensus": {
                "home_prob": float(h) if has_primary_probabilities else None,
                "draw_prob": float(d) if has_primary_probabilities else None,
                "away_prob": float(a) if has_primary_probabilities else None,
                "confidence": float(getattr(latest_pred, 'confidence', 0.0)) if (has_primary_probabilities and latest_pred and getattr(latest_pred, 'confidence', None) is not None) else None,
                "risk_score": float(getattr(latest_audit, 'risk_score', 0.0)) if (has_primary_probabilities and latest_audit and getattr(latest_audit, 'risk_score', None) is not None) else None,
                "model_agreement": float(getattr(latest_audit, 'model_agreement', 0.0)) if (has_primary_probabilities and latest_audit and getattr(latest_audit, 'model_agreement', None) is not None) else None,
                "models_active": int(getattr(latest_audit, 'pkl_models_active', 0)) if (has_primary_probabilities and latest_audit and getattr(latest_audit, 'pkl_models_active', None) is not None) else None,
                "elo_diff": float(elo_diff),
                "squad_value_diff": None,
                "timestamp": latest_pred.timestamp.isoformat() if (has_primary_probabilities and latest_pred and getattr(latest_pred, 'timestamp', None)) else None,
            },
            "attribution": _normalize_attribution_items(
                getattr(latest_audit, 'individual_results', None)
                or getattr(latest_pred, 'model_insights', [])
                or []
            ) if has_primary_probabilities else [],
            "tactical": tactical_insights,
            "market_edge": {
                "ai_prob": float(max(h, d, a)) if has_primary_probabilities else None,
                "bookmaker_prob": 1.0 / float(latest.get("odds", {}).get(getattr(latest_pred, 'bet_side', None)) or 2.0) if (has_primary_probabilities and latest_pred and getattr(latest_pred, 'bet_side', None) and latest.get("odds", {}).get(latest_pred.bet_side)) else None,
                "edge": float(latest["edge"]) if (has_primary_probabilities and latest.get("edge") is not None) else None,
                "expected_roi": float(latest["edge"]) * 100 if (has_primary_probabilities and latest.get("edge") is not None) else None,
                "kelly_stake": float(getattr(latest_pred, 'recommended_stake', 0.0)) if (has_primary_probabilities and latest_pred and getattr(latest_pred, 'recommended_stake', None) is not None) else None,
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


async def _execute_match_prediction(match_id: int, db: AsyncSession) -> dict:
    match_q = await db.execute(select(Match).where(Match.id == match_id))
    match = match_q.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match.source not in {"isports", "sportsdb", "footballdata", "football-data.org", "the_odds_api"}:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "MATCH_SOURCE_UNVERIFIED",
                "message": "Predictions are only available for provider-sourced fixtures",
            },
        )

    pred_q = await db.execute(
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(Prediction.timestamp.desc())
    )
    preds = pred_q.scalars().all()
    latest_pred = preds[0] if preds else None

    now = datetime.now(timezone.utc)
    if latest_pred and getattr(latest_pred, 'status', None) == "INITIALIZING":
        ts = latest_pred.timestamp
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts and (now - ts).total_seconds() < 120:
            return {
                "prediction_status": "initializing",
                "job_id": getattr(latest_pred, 'job_id', None),
                "message": "Prediction generation is already in progress."
            }

    job_id = f"job_pred_{match_id}_{int(now.timestamp())}"

    new_pred = Prediction(
        match_id=match.id,
        status="INITIALIZING",
        source="live_generated",
        is_seed=False,
        job_id=job_id,
        home_prob=0.0,
        draw_prob=0.0,
        away_prob=0.0,
        confidence=0.0
    )
    db.add(new_pred)
    await db.commit()
    await db.refresh(new_pred)

    try:
        # 1. Fetch Features
        features = await build_predict_features(db, match.home_team, match.away_team, match.league)
        h2h = await _head_to_head(db, match)
        recent_form_data = {
            "home": await _recent_form(db, team=match.home_team, before=match.kickoff_time),
            "away": await _recent_form(db, team=match.away_team, before=match.kickoff_time),
        }

        # 2. Reconcile Multi-Provider Odds (NO manufactured / fake odds allowed)
        odds_list: List[NormalizedOdds] = []
        odds_values = (
            match.opening_odds_home or match.closing_odds_home,
            match.opening_odds_draw or match.closing_odds_draw,
            match.opening_odds_away or match.closing_odds_away,
        )
        if all(val is not None and float(val) > 1.0 for val in odds_values):
            odds_list.append(NormalizedOdds(
                fixture_id=str(match.external_id or match.id),
                sport=match.sport or "football",
                market="match_winner",
                selection="home",
                odds=float(odds_values[0]),
                bookmaker="MatchRecord",
                timestamp=match.kickoff_time or now,
                provider=match.source or "provider",
            ))
            if odds_values[1] and float(odds_values[1]) > 1.0:
                odds_list.append(NormalizedOdds(
                    fixture_id=str(match.external_id or match.id),
                    sport=match.sport or "football",
                    market="match_winner",
                    selection="draw",
                    odds=float(odds_values[1]),
                    bookmaker="MatchRecord",
                    timestamp=match.kickoff_time or now,
                    provider=match.source or "provider",
                ))
            odds_list.append(NormalizedOdds(
                fixture_id=str(match.external_id or match.id),
                sport=match.sport or "football",
                market="match_winner",
                selection="away",
                odds=float(odds_values[2]),
                bookmaker="MatchRecord",
                timestamp=match.kickoff_time or now,
                provider=match.source or "provider",
            ))

        reconciled_odds = OddsIntelligence.reconcile(odds_list, sport=match.sport or "football", market="match_winner")

        # 3. Data / Evidence Quality Engine Evaluation
        evidence = EvidenceEngine.evaluate(
            match_source=match.source,
            match_features=features,
            reconciled_odds=reconciled_odds,
            h2h_data=h2h,
            recent_form_data=recent_form_data,
            model_agreement_pct=0.75,
            market="match_winner"
        )

        if not evidence.is_sufficient:
            new_pred.status = "FAILED"
            new_pred.error_message = f"PREDICTION UNAVAILABLE: {evidence.rejection_reason or 'Insufficient data evidence'}"
            new_pred.provenance = {
                "job_id": job_id,
                "status": "UNAVAILABLE",
                "evidence_score": evidence.total_score,
                "evidence_classification": evidence.classification.value,
                "missing_elements": evidence.missing_elements,
                "rejection_reason": evidence.rejection_reason,
            }
            await db.commit()
            return {
                "prediction_status": "unavailable",
                "job_id": job_id,
                "evidence_score": evidence.total_score,
                "evidence_classification": evidence.classification.value,
                "missing_elements": evidence.missing_elements,
                "message": f"PREDICTION UNAVAILABLE. {evidence.rejection_reason or 'Insufficient evidence coverage.'}",
                "retryable": False
            }

        # 4. Invoke Prediction Orchestrator
        from app.core.dependencies import get_orchestrator_dep
        from app.services.multi_sport_orchestrator import MultiSportOrchestrator
        try:
            base_orch = await get_orchestrator_dep()
            orchestrator = MultiSportOrchestrator(football_orchestrator=base_orch)
        except Exception as exc:
            raise RuntimeError(f"Prediction model unavailable: {exc}") from exc

        market_odds_payload = reconciled_odds.consensus_odds if reconciled_odds else None
        idempotency_key = f"match_init_{match_id}_{job_id}"
        raw_result = await orchestrator.predict(
            features={
                "home_team": match.home_team,
                "away_team": match.away_team,
                "league": match.league,
                "market_odds": market_odds_payload,
                "match_features": features,
            },
            idempotency_key=idempotency_key,
            sport=match.sport or "football"
        )

        if raw_result and "predictions" in raw_result:
            pred_res = raw_result.get("predictions", {})
        elif raw_result and isinstance(raw_result, dict) and "home_prob" in raw_result:
            pred_res = raw_result
        else:
            raise RuntimeError("Prediction model returned no prediction")

        required = ("home_prob", "draw_prob", "away_prob")
        if any(pred_res.get(key) is None for key in required):
            raise RuntimeError("Prediction model returned incomplete probabilities")
        h = float(pred_res["home_prob"])
        d = float(pred_res["draw_prob"])
        a = float(pred_res["away_prob"])
        confidence_value = raw_result.get("confidence") if isinstance(raw_result, dict) else None
        if isinstance(confidence_value, dict):
            confidence_value = confidence_value.get("1x2")
        if confidence_value is None:
            confidence_value = pred_res.get("confidence", {}).get("1x2", 0.0) if isinstance(pred_res.get("confidence"), dict) else pred_res.get("confidence")
        conf = float(confidence_value or 0.0)

        # 5. Value Engine Analysis
        m_edge = 0.0
        kelly = 0.0
        best_side = "home"
        entry_price = 2.0

        if reconciled_odds and reconciled_odds.consensus_odds:
            options = [
                ("home", h, reconciled_odds.consensus_odds.get("home", 2.0)),
                ("draw", d, reconciled_odds.consensus_odds.get("draw", 3.0)),
                ("away", a, reconciled_odds.consensus_odds.get("away", 3.0)),
            ]
            valid_opts = [o for o in options if o[2] and o[2] > 1.0]
            if valid_opts:
                best_opt = max(valid_opts, key=lambda x: x[1] - (1.0 / x[2]))
                best_side = best_opt[0]
                entry_price = best_opt[2]
                m_edge = round(best_opt[1] - (1.0 / best_opt[2]), 4)
                kelly = max(0.0, round((best_opt[1] * best_opt[2] - 1.0) / (best_opt[2] - 1.0) * 0.25, 4)) if best_opt[2] > 1.0 else 0.0

        new_pred.home_prob = round(h, 4)
        new_pred.draw_prob = round(d, 4)
        new_pred.away_prob = round(a, 4)
        new_pred.over_25_prob = float(pred_res["over_25_prob"]) if pred_res.get("over_25_prob") is not None else None
        new_pred.under_25_prob = float(pred_res["under_25_prob"]) if pred_res.get("under_25_prob") is not None else None
        new_pred.btts_prob = float(pred_res["btts_prob"]) if pred_res.get("btts_prob") is not None else None
        new_pred.no_btts_prob = float(pred_res["no_btts_prob"]) if pred_res.get("no_btts_prob") is not None else None
        new_pred.status = "READY"
        new_pred.source = "live_generated"
        new_pred.is_seed = False
        new_pred.confidence = round(conf, 4)
        new_pred.raw_edge = m_edge
        new_pred.vig_free_edge = m_edge
        new_pred.recommended_stake = min(0.05, kelly)
        new_pred.bet_side = best_side
        new_pred.entry_odds = entry_price
        new_pred.provenance = {
            "job_id": job_id,
            "source": match.source,
            "external_id": match.external_id,
            "model_version": "v4.10.0-ensemble",
            "generated_at": now.isoformat(),
            "evidence_score": evidence.total_score,
            "evidence_classification": evidence.classification.value,
            "evidence_breakdown": {
                "verified_fixture": evidence.verified_fixture,
                "team_statistics": evidence.team_statistics,
                "recent_form": evidence.recent_form,
                "current_odds": evidence.current_odds,
                "bookmaker_agreement": evidence.bookmaker_agreement,
                "h2h_context": evidence.h2h_context,
                "model_agreement": evidence.model_agreement,
            },
            "checklist": evidence.checklist,
            "odds_consensus": reconciled_odds.consensus_odds if reconciled_odds else None,
            "vig_free_probabilities": reconciled_odds.vig_free_probabilities if reconciled_odds else None,
            "bookmaker_count": reconciled_odds.bookmaker_count if reconciled_odds else 0,
            "odds_freshness": reconciled_odds.freshness.value if reconciled_odds else None,
            "feature_completeness": features.get("feature_completeness", 0.0),
        }
        await db.commit()
        await db.refresh(new_pred)

        return {
            "prediction_status": "ready",
            "job_id": job_id,
            "prediction_id": new_pred.id,
            "source": new_pred.source,
            "is_seed": False,
            "probabilities": {
                "home_prob": new_pred.home_prob,
                "draw_prob": new_pred.draw_prob,
                "away_prob": new_pred.away_prob,
            },
            "confidence": new_pred.confidence,
            "edge": new_pred.vig_free_edge,
            "bet_side": new_pred.bet_side,
            "evidence_score": evidence.total_score,
            "evidence_classification": evidence.classification.value,
            "provenance": new_pred.provenance
        }
    except Exception as exc:
        logger.error(f"[matches] Prediction initialization failed for match {match_id}: {exc}", exc_info=True)
        new_pred.status = "FAILED"
        new_pred.error_message = str(exc)
        await db.commit()
        return {
            "prediction_status": "failed",
            "job_id": job_id,
            "error": str(exc),
            "retryable": True
        }



@router.post("/{match_id}/predict/initialize")
async def initialize_match_prediction(match_id: int, db: AsyncSession = Depends(get_db)):
    return await _execute_match_prediction(match_id, db)


@router.post("/{match_id}/predict/rerun")
async def rerun_match_prediction(match_id: int, db: AsyncSession = Depends(get_db)):
    return await _execute_match_prediction(match_id, db)

@router.get("/{match_id}/analytics")
async def get_match_analytics(match_id: int, db: AsyncSession = Depends(get_db)):
    match = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    pred_rows = (await db.execute(
        select(Prediction).where(Prediction.match_id == match_id).order_by(Prediction.timestamp.desc()).limit(1)
    )).scalars().all()
    pred = next((candidate for candidate in pred_rows if not getattr(candidate, "is_seed", False)), None)

    audit = (await db.execute(
        select(AIPredictionAudit).where(AIPredictionAudit.match_id == str(match_id)).order_by(AIPredictionAudit.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    markets = await _load_markets(db)
    fmt = _fmt_match(match, pred, markets)

    return {
        "match": fmt,
        "prediction": {
            "side": pred.bet_side if pred else None,
            "confidence": float(pred.confidence) if pred and pred.confidence is not None else None,
            "edge": float(pred.vig_free_edge) if pred and pred.vig_free_edge is not None else None,
            "risk_score": float(audit.risk_score) if audit and audit.risk_score is not None else None,
            "model_agreement": float(audit.model_agreement) if audit and audit.model_agreement is not None else None,
        } if pred else None,
        "market_efficiency": "available" if any(value is not None for value in fmt.get("odds", {}).values()) else "unavailable",
    }


@router.get("/{match_id}/ensemble")
async def get_ensemble_breakdown(match_id: int, db: AsyncSession = Depends(get_db)):
    """
    Detailed breakdown of how the ensemble reached its conclusion.
    """
    pred_rows = (await db.execute(
        select(Prediction).where(Prediction.match_id == match_id).order_by(Prediction.timestamp.desc()).limit(20)
    )).scalars().all()
    pred = next((candidate for candidate in pred_rows if not getattr(candidate, "is_seed", False)), None)

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
