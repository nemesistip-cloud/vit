from app.core.markets import get_markets_for_sport
# app/api/routes/predict.py
# VIT Sports Analytics Network — v2.1.0
# Native AI Only version

import hashlib
import json
import logging
import math
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timezone

from app.config import APP_VERSION, MAX_STAKE, MIN_EDGE_THRESHOLD, MAX_PREDICTIONS_PER_DAY, PUBLIC_APP_URL
from app.db.database import get_db
from app.db.models import Match, Prediction
from app.schemas.schemas import MatchRequest, PredictionResponse
from app.services.clv_tracker import CLVTracker
from app.services.market_utils import MarketUtils
from app.api.middleware.auth import verify_api_key
from app.api.deps import get_optional_user
from app.services.alerts import BetAlert
from app.core.dependencies import get_orchestrator_dep, get_telegram_dep
from app.services.multi_sport_orchestrator import MultiSportOrchestrator

from app.tasks.clv import update_clv_task
from app.tasks.edges import recalculate_edges_task
from app.services.decision_logger import DecisionLogger
from app.services.predict_features import build_predict_features

logger = logging.getLogger(__name__)

TWO_WAY_SPORTS = {
    "basketball", "tennis", "cricket", "american_football", "rugby",
    "rugby_union", "baseball", "ice_hockey", "mma", "boxing",
    "formula1", "esports"
}


def _normalize_sport_name(sport: Optional[str]) -> str:
    return (sport or "football").lower().replace(" ", "_")


def validate_market_odds(market_odds: Optional[dict], sport: Optional[str] = None) -> bool:
    """Validate that the request includes plausible odds for the requested sport."""
    if not isinstance(market_odds, dict):
        return False

    sport_name = _normalize_sport_name(sport)
    if sport_name in TWO_WAY_SPORTS:
        home = MarketUtils.validate_odds(market_odds.get("home"))
        away = MarketUtils.validate_odds(market_odds.get("away"))
        return home is not None and away is not None and home != away

    home = MarketUtils.validate_odds(market_odds.get("home"))
    draw = MarketUtils.validate_odds(market_odds.get("draw"))
    away = MarketUtils.validate_odds(market_odds.get("away"))
    return home is not None and draw is not None and away is not None


def validate_prediction_response(payload: Optional[dict], market_odds: Optional[dict] = None, sport: Optional[str] = None) -> dict:
    """Normalize prediction payloads so downstream code always receives usable probabilities."""
    if not isinstance(payload, dict):
        payload = {}

    sport_name = _normalize_sport_name(sport)
    home = float(payload.get("home_prob", 0.0) or 0.0)
    draw = float(payload.get("draw_prob", 0.0) or 0.0)
    away = float(payload.get("away_prob", 0.0) or 0.0)

    if sport_name in TWO_WAY_SPORTS:
        # For two-way markets, keep the draw probability at zero and normalize home/away.
        if home < 0:
            home = 0.0
        if away < 0:
            away = 0.0
        total = home + away
        if total <= 0:
            # Fallback from market odds if available.
            if market_odds and MarketUtils.validate_odds(market_odds.get("home")) and MarketUtils.validate_odds(market_odds.get("away")):
                h_odds = float(market_odds.get("home"))
                a_odds = float(market_odds.get("away"))
                home = 1 / h_odds
                away = 1 / a_odds
                total = home + away
                if total <= 0:
                    home, away = 0.5, 0.5
                else:
                    home, away = home / total, away / total
        else:
            home, away = home / total, away / total
        draw = 0.0
    else:
        # For three-way football-like markets, normalize the probabilities if needed.
        if home < 0 or draw < 0 or away < 0:
            home = max(0.0, home)
            draw = max(0.0, draw)
            away = max(0.0, away)
        total = home + draw + away
        if total <= 0:
            if market_odds:
                home_odds = MarketUtils.validate_odds(market_odds.get("home"))
                draw_odds = MarketUtils.validate_odds(market_odds.get("draw"))
                away_odds = MarketUtils.validate_odds(market_odds.get("away"))
                if home_odds and draw_odds and away_odds:
                    home, draw, away = MarketUtils.remove_vig(home_odds, draw_odds, away_odds).values()
                    total = home + draw + away
        if total > 0:
            home, draw, away = home / total, draw / total, away / total
        else:
            home, draw, away = 0.33, 0.34, 0.33

    payload["home_prob"] = round(min(max(home, 0.0), 1.0), 6)
    payload["draw_prob"] = round(min(max(draw, 0.0), 1.0), 6)
    payload["away_prob"] = round(min(max(away, 0.0), 1.0), 6)
    payload.setdefault("models_used", payload.get("models_used", 0))
    payload.setdefault("models_total", payload.get("models_total", 13))
    payload.setdefault("data_source", payload.get("data_source", "market_implied"))
    return payload


router = APIRouter(
    prefix="/predict",
    tags=["predictions"],
    dependencies=[Depends(verify_api_key)]
)

VERSION = APP_VERSION

def to_naive_utc(dt_input) -> datetime:
    if isinstance(dt_input, str):
        try:
            parsed = datetime.fromisoformat(dt_input.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=None)
        except Exception as e:
            logger.warning(f"Failed to parse kickoff_time '{dt_input}': {e}")
            return datetime.now(timezone.utc).replace(tzinfo=None)
    elif isinstance(dt_input, datetime):
        if dt_input.tzinfo is not None:
            return dt_input.astimezone(timezone.utc).replace(tzinfo=None)
        return dt_input
    return datetime.now(timezone.utc).replace(tzinfo=None)

def create_idempotency_key(match: MatchRequest, user_id: Optional[int] = None) -> str:
    odds = match.market_odds or {}
    # Use fixed-decimal strings to avoid float JSON-serialisation drift
    # (e.g. round(2.345, 2) → 2.34 vs 2.35 across platforms).
    odds_sig = {k: f"{round(float(v), 2):.2f}" for k, v in odds.items() if v}
    kt = match.kickoff_time
    kickoff_bucket = kt.replace(minute=(kt.minute // 30) * 30, second=0, microsecond=0)
    content = {
        "home_team":    match.home_team,
        "away_team":    match.away_team,
        "kickoff_time": kickoff_bucket.isoformat(),
        "league":       match.league,
        "odds_sig":     odds_sig,
        "user_id":      user_id,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:32]

def _argmax_side(hp: float, dp: float, ap: float) -> str:
    return max((("home", hp), ("draw", dp), ("away", ap)), key=lambda x: x[1])[0]

def _entropy_confidence(hp: float, dp: float, ap: float) -> float:
    probs = [p for p in (hp, dp, ap) if p > 0]
    if not probs: return 0.50
    ent = -sum(p * math.log(p) for p in probs); max_ent = math.log(3); normalised = max(0.0, min(1.0, 1.0 - (ent / max_ent)))
    return round(0.50 + normalised * 0.45, 3)


def compute_model_consensus(
    model_insights: list,
    final_pick: str = "home",
    total_specs: int = None,
) -> dict:
    """Compute per-side vote-share across all model results.

    Each model casts one vote for the side it assigns the highest probability.
    Percentages are expressed out of *total_specs* (full ensemble size, even if
    some models failed) so the caller can see participation clearly.
    """
    if not model_insights:
        return {
            "leader": final_pick, "home": 0.0, "draw": 0.0, "away": 0.0,
            "votes": {"home": 0, "draw": 0, "away": 0}, "models_polled": 0,
        }
    votes: dict = {"home": 0, "draw": 0, "away": 0}
    for m in model_insights:
        hp = float(m.get("home_prob") or 0.0)
        dp = float(m.get("draw_prob") or 0.0)
        ap = float(m.get("away_prob") or 0.0)
        side = max((("home", hp), ("draw", dp), ("away", ap)), key=lambda x: x[1])[0]
        votes[side] += 1
    n = len(model_insights)
    denom = max(1.0, float(total_specs or n or 0))
    return {
        "leader": final_pick,
        "home":  round(votes["home"]  / denom * 100, 1),
        "draw":  round(votes["draw"]  / denom * 100, 1),
        "away":  round(votes["away"]  / denom * 100, 1),
        "votes": votes,
        "models_polled": n,
    }


def build_alternative_bets(best_bet: dict, top_n: int = 5, min_edge: float = 0.0) -> list:
    """Build ordered list of alternative bet recommendations from the best-bet dict."""
    if not best_bet:
        return []
    alts: list = []
    if best_bet.get("best_side"):
        alts.append({
            "market": best_bet.get("best_market", "1x2"),
            "side": best_bet["best_side"],
            "edge": round(float(best_bet.get("edge", 0.0)), 4),
            "odds": best_bet.get("odds"),
            "kelly_stake": best_bet.get("kelly_stake"),
            "recommended": True,
        })
    ou_p = best_bet.get("over_25_prob") or best_bet.get("over_2_5_prob")
    if ou_p is not None:
        alts.append({
            "market": "over_under_2.5",
            "side": "over" if float(ou_p) >= 0.5 else "under",
            "edge": round(float(best_bet.get("edge", 0.0)) * 0.7, 4),
            "recommended": False,
        })
    btts_p = best_bet.get("btts_prob")
    if btts_p is not None:
        alts.append({
            "market": "btts",
            "side": "yes" if float(btts_p) >= 0.5 else "no",
            "edge": round(float(best_bet.get("edge", 0.0)) * 0.6, 4),
            "recommended": False,
        })
    return [a for a in alts if a["edge"] >= min_edge][:top_n]

def build_prediction_response(prediction: Prediction, match: Match, orchestrator: Optional[object] = None, sport: str = "football", available_markets: list[str] = None, data_quality: Optional[dict] = None, data_source: str = "native_ensemble") -> PredictionResponse:
    conf = prediction.confidence
    rating = "EXCELLENT" if conf >= 0.80 else ("VERY GOOD" if conf >= 0.72 else ("GOOD" if conf >= 0.63 else ("FAIR" if conf >= 0.55 else "POOR")))
    accuracy = round(min(82.0, max(54.0, 44.0 + conf * 50.0)), 1)
    return PredictionResponse(
        match_id=prediction.match_id, sport=sport, available_markets=available_markets or [],
        home_prob=prediction.home_prob, draw_prob=prediction.draw_prob, away_prob=prediction.away_prob,
        over_25_prob=prediction.over_25_prob, under_25_prob=prediction.under_25_prob, btts_prob=prediction.btts_prob,
        model_consensus=prediction.model_consensus, alternative_bets=prediction.alternative_bets, consensus_prob=prediction.consensus_prob,
        final_ev=prediction.final_ev, recommended_stake=prediction.recommended_stake, edge=prediction.vig_free_edge, confidence=prediction.confidence, timestamp=prediction.timestamp,
        models_used=len(prediction.model_insights) if prediction.model_insights else 0,
        models_total=13,
        data_source=data_source, bet_side=prediction.bet_side, entry_odds=prediction.entry_odds, raw_edge=prediction.raw_edge, normalized_edge=prediction.normalized_edge, vig_free_edge=prediction.vig_free_edge,
        model_weights=prediction.model_weights or {}, model_insights=prediction.model_insights or [], neural_consensus_score=(prediction.consensus_prob * 100), analytics_rating=rating, prediction_accuracy_estimate=accuracy, data_quality=data_quality
    )

@router.post("", response_model=PredictionResponse)
async def predict(
    match: MatchRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator = Depends(get_orchestrator_dep),
    telegram_alerts = Depends(get_telegram_dep),
    current_user = Depends(get_optional_user),
):
    """
    Generate prediction for a match.

    v2.1.0:
    - Passes full market odds to orchestrator
    - Sends Telegram alert for ALL predictions (edge or no edge)
      so the channel always shows match status
    - BetAlert includes model count, all probs, all odds, data source

    v2.4.0:
    - Accepts fixture_id to track which specific fixture was predicted
    - Logs fixture_id for debugging and fixture-prediction mapping
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    fixture_id = match.fixture_id if match.fixture_id else "unknown"
    user_id: Optional[int] = current_user.id if current_user else None
    sport = (match.sport or "football").lower()
    available_markets = get_markets_for_sport(sport)

    # C-1 / T10 — per-user daily prediction rate limit (DB-backed: accurate across restarts)
    # Admin / super_admin users are exempt from the daily limit.
    _user_role = getattr(current_user, "role", None) if current_user else None
    _is_admin = _user_role in ("admin", "super_admin")
    if user_id is not None and not _is_admin:
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import func as _rl_func
        from app.core.rate_limit import get_limit_for_tier
        _limit = get_limit_for_tier(getattr(current_user, "tier", "free"))
        _today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        _tomorrow = (_today_start + timedelta(days=1)).isoformat().replace("+00:00", "Z")
        _db_count_res = await db.execute(
            select(_rl_func.count(Prediction.id)).where(
                Prediction.user_id == user_id,
                Prediction.timestamp >= _today_start,
            )
        )
        _db_count = _db_count_res.scalar() or 0
        if _db_count >= _limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Daily prediction limit reached",
                    "limit": _limit,
                    "used": _db_count,
                    "resets_at": _tomorrow,
                },
            )
    idempotency_key = create_idempotency_key(match, user_id)
    naive_kickoff = to_naive_utc(match.kickoff_time)

    # v4.10.0 — fallback / data-quality tracker.
    # Every degraded code path appends a flag here so the response (and the
    # frontend) can clearly distinguish a real-data prediction from one that
    # leaned on synthetic odds, neutral features, or a vig-removal fallback.
    data_quality: dict = {
        "market_odds_fallback":   False,
        "feature_completeness":   None,    # 0..1 from predict_features
        "vig_removal_fallback":   False,
        "pkl_models_loaded":      0,
        "failed_models":          [],
        "warnings":               [],
        "calibration": {                   # Phase C
            "method":              None,
            "calibrated_models":   0,
            "uncalibrated_models": [],
            "partial_models":      [],
        },
    }

    try:
        if not validate_market_odds(match.market_odds, getattr(match, "sport", None)):
            raise ValueError(
                "Valid live market odds are required for prediction. "
                "Provide accurate home/draw/away odds for football, or "
                "home/away odds for two-way sports, instead of relying on synthetic fallback values."
            )

        # --- Idempotency: return existing prediction if same hash ---
        existing = await db.execute(
            select(Prediction).where(Prediction.request_hash == idempotency_key)
        )
        existing_pred = existing.scalar_one_or_none()
        if existing_pred:
            # Return cached prediction instead of 409
            existing_match_res = await db.execute(
                select(Match).where(Match.id == existing_pred.match_id)
            )
            ex_match = existing_match_res.scalar_one_or_none()
            if ex_match:
                logger.info(f"Returning cached prediction for hash={idempotency_key}")
                cached_dq = dict(data_quality)
                cached_dq["warnings"].append("served_from_cache")
                return build_prediction_response(existing_pred, ex_match, orchestrator, sport=sport, data_quality=cached_dq, available_markets=available_markets)

        # --- Find or create match ---
        # 1. Try by external_id (fixture_id)
        db_match = None
        if match.fixture_id and match.fixture_id != "unknown":
            ext_res = await db.execute(
                select(Match).where(Match.external_id == str(match.fixture_id))
            )
            db_match = ext_res.scalar_one_or_none()

        # 2. Try by cross-source fingerprint (date::home::away::league)
        if db_match is None:
            try:
                from app.data.match_dedup import find_existing_match
                db_match = await find_existing_match(db, match.home_team, match.away_team, naive_kickoff, match.league)
            except Exception:
                pass

        # 3. Fallback: fuzzy teams + 24-hour kickoff window (no league constraint to avoid
        #    false misses when league names differ between source and DB)
        if db_match is None:
            from datetime import timedelta
            window_start = naive_kickoff - timedelta(hours=24)
            window_end   = naive_kickoff + timedelta(hours=24)
            existing_match_res = await db.execute(
                select(Match).where(
                    Match.home_team == match.home_team,
                    Match.away_team == match.away_team,
                    Match.kickoff_time >= window_start,
                    Match.kickoff_time <= window_end,
                )
            )
            db_match = existing_match_res.scalars().first()

        if db_match is None:
            # Create new match record — stamp fingerprint so future dedup works
            try:
                from app.data.match_dedup import compute_fingerprint as _cfp
                _fp = _cfp(match.home_team, match.away_team, naive_kickoff, match.league)
            except Exception:
                _fp = None
            db_match = Match(
                home_team=match.home_team,
                away_team=match.away_team,
                league=match.league,
                kickoff_time=naive_kickoff,
                source="predict",
                fingerprint=_fp,
                sport=getattr(match, "sport", "football") or "football",
                opening_odds_home=match.market_odds.get("home"),
                opening_odds_draw=match.market_odds.get("draw"),
                opening_odds_away=match.market_odds.get("away"),
            )
            db.add(db_match)
            await db.flush()
            logger.info(f"Match created: {match.home_team} vs {match.away_team} @ {naive_kickoff}")
        else:
            logger.info(f"Reusing existing match id={db_match.id}: {match.home_team} vs {match.away_team}")

        # --- Run orchestrator with full market odds AND real per-team features ---
        # v4.10.0 (Phase A): replace hardcoded sklearn feature globals with
        # rolling form / H2H / ELO-proxy values queried from the DB.
        try:
            match_features = await build_predict_features(
                db, match.home_team, match.away_team, match.league
            )
        except Exception as exc:
            logger.warning(
                "PREDICT_FALLBACK build_predict_features raised %s — using "
                "neutral feature defaults",
                exc,
            )
            match_features = {}
            data_quality["warnings"].append("feature_builder_exception")

        completeness = float(match_features.get("feature_completeness", 0.0)) if match_features else 0.0
        data_quality["feature_completeness"] = round(completeness, 3)
        if completeness < 0.3:
            logger.warning(
                "PREDICT_FALLBACK low feature completeness=%.2f for %s vs %s — "
                "models will lean heavily on neutral defaults",
                completeness, match.home_team, match.away_team,
            )
            data_quality["warnings"].append("low_feature_completeness")

        # ── Real-time web context injection ──────────────────────────────────
        # Fetch live news/injury snippets for both teams via web search and
        # inject them into the features dict so the LLM Consensus model and
        # AI signal layer have access to current information.
        web_context: dict = {}
        web_context_text: str = ""
        try:
            from app.services.web_search import fetch_match_context, format_context_for_prompt
            web_context = await fetch_match_context(
                match.home_team, match.away_team, match.league or ""
            )
            web_context_text = format_context_for_prompt(
                web_context, match.home_team, match.away_team
            )
            if web_context_text:
                logger.info(
                    "[predict] web-search context fetched for %s vs %s (%d chars)",
                    match.home_team, match.away_team, len(web_context_text),
                )
        except Exception as _wse:
            logger.debug("[predict] web-search context unavailable: %s", _wse)

        features = {
            "home_team":         match.home_team,
            "away_team":         match.away_team,
            "league":            match.league,
            "market_odds":       match.market_odds,     # ← v2.1.0: always passes real odds
            "match_features":    match_features,         # ← v4.10.0: real rolling features
            "web_context":       web_context,            # ← real-time web search snippets
            "web_context_text":  web_context_text,       # ← formatted for AI prompts
        }

        raw_result = await orchestrator.predict(features, idempotency_key, sport=sport)
        pred_data  = raw_result.get("predictions", raw_result)
        result     = validate_prediction_response(pred_data, market_odds=match.market_odds, sport=getattr(match, "sport", None))

        # --- Extract all probabilities ---
        home_prob = float(result.get("home_prob", 0.0))
        draw_prob = float(result.get("draw_prob", 0.0))
        away_prob = float(result.get("away_prob", 0.0))

        # --- Extract market odds (validated live odds only) ---
        sport_lower = getattr(match, "sport", "football") or "football"
        home_odds = MarketUtils.validate_odds(match.market_odds.get("home"))
        draw_odds = MarketUtils.validate_odds(match.market_odds.get("draw"))
        away_odds = MarketUtils.validate_odds(match.market_odds.get("away"))
        if home_odds is None or away_odds is None or (
            sport_lower not in TWO_WAY_SPORTS and draw_odds is None
        ):
            raise ValueError(
                "Market odds must include valid home/draw/away values for football, "
                "or valid home/away odds for two-way sports."
            )
        home_odds = float(home_odds)
        draw_odds = float(draw_odds) if draw_odds is not None else 0.0
        away_odds = float(away_odds)

        # --- Best bet calculation (v4.6.1: multi-market — 1X2 + O/U 2.5 + BTTS) ---
        _o25 = result.get("over_25_prob") or result.get("over_2_5_prob")
        _u25 = result.get("under_25_prob") or result.get("under_2_5_prob")
        _btts = result.get("btts_prob")
        _no_btts = result.get("no_btts_prob")
        _mo = match.market_odds or {}
        best_bet = MarketUtils.determine_best_bet(
            home_prob, draw_prob, away_prob,
            home_odds, draw_odds, away_odds,
            over_25_prob=_o25,
            under_25_prob=_u25,
            over_25_odds=_mo.get("over_2_5") or _mo.get("over_25"),
            under_25_odds=_mo.get("under_2_5") or _mo.get("under_25"),
            btts_prob=_btts,
            no_btts_prob=_no_btts,
            btts_yes_odds=_mo.get("btts_yes") or _mo.get("btts"),
            btts_no_odds=_mo.get("btts_no"),
            # v4.6.1 — Asian Handicap (only scored if bookmaker prices are present)
            ah_line=result.get("ah_line"),
            ah_home_prob=result.get("ah_home_prob"),
            ah_away_prob=result.get("ah_away_prob"),
            ah_home_odds=_mo.get("ah_home"),
            ah_away_odds=_mo.get("ah_away"),
            # v4.6.1 — Correct Score (bookmaker priced ladder)
            cs_probs=result.get("cs_probs"),
            cs_odds=_mo.get("cs_odds") if isinstance(_mo.get("cs_odds"), dict) else None,
        )

        recommended_stake = min(best_bet.get("kelly_stake", 0), MAX_STAKE)

        probs         = {"home": home_prob, "draw": draw_prob, "away": away_prob}
        # consensus_prob should reflect the model's probability for the chosen
        # bet side, not simply the 1x2 maximum.  When the best bet is on a
        # non-1x2 market (e.g. over_2_5, btts_yes) we use that model_prob;
        # for 1x2 bets we read the matching probability directly.
        _chosen_side   = best_bet.get("best_side")
        _chosen_market = best_bet.get("best_market")
        if _chosen_market == "1x2" and _chosen_side in probs:
            consensus_prob = probs[_chosen_side]
        elif best_bet.get("model_prob") is not None:
            consensus_prob = float(best_bet["model_prob"])
        else:
            consensus_prob = max(probs.values())

        # --- v2.1.0: Extract model metadata from orchestrator result ---
        models_used   = result.get("models_used", raw_result.get("models_count", 0))
        models_total  = result.get("models_total", orchestrator._total_model_specs if orchestrator else 0)
        data_source   = result.get("data_source", "market_implied")
        # Confidence: prefer the orchestrator's reported value; otherwise derive
        # from the actual probability distribution. Never fall back to a fixed
        # constant — that would be presenting a hardcoded number as a model
        # confidence to the user.
        raw_conf = result.get("confidence")
        if isinstance(raw_conf, dict) and raw_conf.get("1x2") is not None:
            confidence_val = float(raw_conf["1x2"])
        elif isinstance(raw_conf, (int, float)):
            confidence_val = float(raw_conf)
        else:
            confidence_val = _entropy_confidence(home_prob, draw_prob, away_prob)

        # --- Build model insights for storage ---
        individual_results    = raw_result.get("individual_results", [])
        model_insights_payload = []
        for p in individual_results:
            raw_conf = p.get("confidence", {})
            if isinstance(raw_conf, dict):
                scalar_conf = raw_conf.get("1x2", 0.0)
                conf_breakdown = raw_conf
            else:
                scalar_conf = float(raw_conf or 0.0)
                conf_breakdown = {}
            model_insights_payload.append({
                "model_name":            p.get("model_name"),
                "model_type":            p.get("model_type"),
                "model_weight":          p.get("model_weight", 1.0),
                "supported_markets":     p.get("supported_markets", []),
                "home_prob":             p.get("home_prob"),
                "draw_prob":             p.get("draw_prob"),
                "away_prob":             p.get("away_prob"),
                "over_2_5_prob":         p.get("over_2_5_prob"),
                "btts_prob":             p.get("btts_prob"),
                "home_goals_expectation": p.get("home_goals_expectation"),
                "away_goals_expectation": p.get("away_goals_expectation"),
                "confidence":            scalar_conf,
                "confidence_breakdown":  conf_breakdown,
                "latency_ms":            p.get("latency_ms"),
                "failed":                p.get("failed", False),
                "error":                 p.get("error"),
                "calibration":           p.get("calibration"),
            })

            # Track per-model fallback signals for the data_quality block.
            if p.get("failed"):
                data_quality["failed_models"].append(p.get("model_name") or "unknown")
            # Trained-pkl source: orchestrator marks it via "source": "trained"
            # on per-model meta when the .pkl was loaded. Best-effort count.
            if p.get("source") == "trained" or p.get("pkl_loaded") is True:
                data_quality["pkl_models_loaded"] += 1

            # Phase C — calibration meta (set by model_orchestrator)
            cal = p.get("calibration") or {}
            mname = p.get("model_name") or "unknown"
            if cal.get("applied"):
                data_quality["calibration"]["calibrated_models"] += 1
                if not data_quality["calibration"]["method"]:
                    data_quality["calibration"]["method"] = cal.get("method")
                if cal.get("partial"):
                    data_quality["calibration"]["partial_models"].append(mname)
            else:
                data_quality["calibration"]["uncalibrated_models"].append(mname)

        if data_quality["failed_models"]:
            logger.warning(
                "PREDICT_FALLBACK %d model(s) failed during ensemble run: %s",
                len(data_quality["failed_models"]),
                ", ".join(data_quality["failed_models"]),
            )
            data_quality["warnings"].append("model_failures")

        if models_used < (orchestrator._total_model_specs if orchestrator else 12):
            data_quality["warnings"].append("partial_ensemble")

        if data_quality["calibration"]["calibrated_models"] == 0:
            data_quality["warnings"].append("no_calibration")
        elif data_quality["calibration"]["uncalibrated_models"]:
            data_quality["warnings"].append("partial_calibration")

        # --- v4.6.2: per-model consensus + alternative bet ladder ---
        # Final 1X2 pick is the argmax of the ensemble probabilities, NOT
        # best_bet["best_side"] (which may be a non-1X2 market like over_2_5).
        final_1x2_pick = _argmax_side(home_prob, draw_prob, away_prob)
        model_consensus = compute_model_consensus(
            model_insights_payload,
            final_pick=final_1x2_pick,
            total_specs=getattr(orchestrator, "_total_model_specs", None),
        )
        alternative_bets = build_alternative_bets(
            best_bet, top_n=5, min_edge=0.0,
        )

        # --- Save prediction ---
        # If the caller submitted an explicit market selection, prefer that
        submitted_side = getattr(match, "selected_side", None)
        submitted_market = getattr(match, "market_id", None)
        submitted_stake = getattr(match, "stake", None)

        bet_side_to_store = submitted_side or best_bet.get("best_side")
        entry_odds_to_store = None
        try:
            entry_odds_to_store = float(match.market_odds.get(submitted_side)) if submitted_side and match.market_odds.get(submitted_side) else best_bet.get("odds", 2.0)
        except Exception:
            entry_odds_to_store = best_bet.get("odds", 2.0)

        prediction = Prediction(
            request_hash=idempotency_key,
            match_id=db_match.id,
            user_id=user_id,
            home_prob=home_prob,
            draw_prob=draw_prob,
            away_prob=away_prob,
            over_25_prob=result.get("over_25_prob") or result.get("over_2_5_prob"),
            under_25_prob=result.get("under_25_prob") or result.get("under_2_5_prob"),
            btts_prob=result.get("btts_prob"),
            no_btts_prob=result.get("no_btts_prob"),
            # v4.6.1 — Asian Handicap + Correct Score
            ah_line=result.get("ah_line"),
            ah_home_prob=result.get("ah_home_prob"),
            ah_away_prob=result.get("ah_away_prob"),
            ah_lines=result.get("ah_lines"),
            cs_probs=result.get("cs_probs"),
            top_correct_score=result.get("top_correct_score"),
            top_cs_prob=result.get("top_cs_prob"),
            # v4.6.2 — consensus + alternatives
            model_consensus=model_consensus,
            alternative_bets=alternative_bets,
            consensus_prob=consensus_prob,
            final_ev=best_bet.get("edge", 0),
            recommended_stake=recommended_stake,
            model_weights={
                **(result.get("model_weights") or {}),
                "match_quality_rating":  result.get("match_quality_rating"),
                "home_advantage_bias":   result.get("home_advantage_bias"),
                "market_confidence":     result.get("confidence") if isinstance(result.get("confidence"), dict) else None,
                "model_agreement_pct":   result.get("model_agreement"),
                "ensemble_diversity":    result.get("ensemble_diversity"),
            },
            model_insights=model_insights_payload,
            confidence=confidence_val,
            bet_side=bet_side_to_store,
            entry_odds=entry_odds_to_store,
            raw_edge=best_bet.get("raw_edge", 0),
            normalized_edge=best_bet.get("edge", 0),
            vig_free_edge=best_bet.get("edge", 0),
            # Submitted market metadata (if the caller provided it)
            submitted_market_id=getattr(match, "market_id", None),
            submitted_market_side=getattr(match, "selected_side", None),
            submitted_stake=getattr(match, "stake", None),
        )
        db.add(prediction)
        await db.flush()
        await db.commit()

        logger.info(
            f"Prediction saved: fixture_id={fixture_id}, match={db_match.id}, "
            f"side={best_bet.get('best_side')}, "
            f"edge={best_bet.get('edge', 0):.4f}, "
            f"models={models_used}/{models_total}, "
            f"source={data_source}"
        )

        # C-1 — record the prediction against the daily limit
        if user_id is not None:
            from app.core.rate_limit import record_prediction as _record_pred
            _record_pred(user_id)

        # C-7 — calibration advisory note
        calibration_note: Optional[str] = None
        agreement_pct = float((model_consensus or {}).get("agreement_pct", 0.0))
        edge_val = float(best_bet.get("edge", 0.0))
        if confidence_val > 0.80 and agreement_pct < 0.60:
            calibration_note = "High confidence but low model agreement — treat with caution"
        elif edge_val > 0.05 and confidence_val < 0.55:
            calibration_note = "Good edge but low confidence — consider half-kelly staking"
        elif agreement_pct >= 0.75 and edge_val > 0.03:
            calibration_note = "Strong consensus signal"

        # --- Task System Integration ---
        # Dispatch trigger events for prediction-related tasks (slug-based, no hardcoded IDs)
        if current_user and current_user.id:
            try:
                from app.modules.tasks.service import TaskService
                await TaskService.dispatch_trigger(db, current_user.id, "prediction", increment=1)
                logger.info(f"Task trigger 'prediction' dispatched for user {current_user.id}")
            except Exception as e:
                logger.warning(f"Task trigger dispatch failed (non-fatal): {e}")

        # --- CLV tracking ---
        # Record for ALL predictions that have a bet_side + valid odds (not just edge bets),
        # so every prediction gets profit/CLV tracking after settlement.
        if best_bet.get("best_side") and float(best_bet.get("odds", 0)) > 1.0:
            try:
                await CLVTracker.record_entry(
                    db, db_match.id, prediction.id,
                    best_bet["best_side"], best_bet["odds"]
                )
            except Exception as e:
                logger.warning(f"CLV record_entry failed (non-fatal): {e}")

        # --- Decision logging ---
        try:
            dl = DecisionLogger(db)
            await dl.log_decision(
                match_id=db_match.id,
                prediction_id=prediction.id,
                decision={
                    "type":          "bet",
                    "stake":         recommended_stake,
                    "odds":          best_bet.get("odds", 2.0),
                    "edge":          best_bet.get("edge", 0),
                    "reason":        f"{best_bet.get('best_side','?').upper()} @ {best_bet.get('odds',2.0):.2f} — edge {best_bet.get('edge',0):.2%}",
                    "model_weights": {p.get("model_name"): p.get("model_weight", 1.0)
                                      for p in individual_results},
                },
                context={
                    "market": {
                        "home_odds": home_odds, "draw_odds": draw_odds, "away_odds": away_odds,
                        "home_prob": home_prob, "draw_prob": draw_prob, "away_prob": away_prob,
                    },
                    "bankroll": {},
                },
            )
        except Exception as e:
            logger.warning(f"DecisionLogger failed (non-fatal): {e}")

        # --- v2.1.0: Send Telegram alert ---
        # Always send for edge > 2%, or when there's a clear prediction to share
        edge_value = best_bet.get("edge", 0)
        should_alert = (
            telegram_alerts
            and telegram_alerts.enabled
            and edge_value > MIN_EDGE_THRESHOLD
        )

        if should_alert:
            try:
                # v4.11.0 — surface the highest-weighted contributing model so
                # the alert body can credit it. Falls back gracefully when the
                # ensemble didn't return individual_results (vig-removal path).
                top_model_name = ""
                try:
                    contributors = [
                        p for p in (raw_result.get("individual_results") or [])
                        if not p.get("failed")
                    ]
                    if contributors:
                        top = max(
                            contributors,
                            key=lambda p: float(p.get("model_weight") or 0.0),
                        )
                        top_model_name = top.get("model_name") or ""
                except Exception:
                    top_model_name = ""

                # Risk score: orchestrator's entropy-derived value if present,
                # otherwise compute from the same probabilities so the alert
                # always shows a value when there are real probs.
                risk_value = float(
                    pred_data.get("risk_score")
                    if isinstance(pred_data, dict) else 0.0
                ) or 0.0
                if risk_value <= 0 and (home_prob + draw_prob + away_prob) > 0:
                    ent = 0.0
                    for p in (home_prob, draw_prob, away_prob):
                        if p > 0:
                            ent -= p * math.log(p)
                    risk_value = round(ent / math.log(3), 4)

                alert = BetAlert(
                    match_id=db_match.id,
                    home_team=match.home_team,
                    away_team=match.away_team,
                    prediction=best_bet.get("best_side", "none"),
                    probability=consensus_prob,
                    edge=edge_value,
                    stake=recommended_stake,
                    odds=best_bet.get("odds", 2.0),
                    confidence=confidence_val,
                    kickoff_time=naive_kickoff,
                    # v2.1.0 fields
                    home_prob=home_prob,
                    draw_prob=draw_prob,
                    away_prob=away_prob,
                    home_odds=home_odds,
                    draw_odds=draw_odds,
                    away_odds=away_odds,
                    models_used=models_used,
                    models_total=models_total,
                    data_source=data_source,
                    # v4.11.0 fields — richer message body
                    league=match.league or "",
                    fixture_id=str(match.fixture_id) if match.fixture_id else None,
                    over_25_prob=float(result.get("over_25_prob") or result.get("over_2_5_prob") or 0.0),
                    btts_prob=float(result.get("btts_prob") or 0.0),
                    vig_free_edge=float(prediction.vig_free_edge or 0.0),
                    risk_score=risk_value,
                    top_model=top_model_name,
                    data_quality=data_quality,
                    app_url=PUBLIC_APP_URL,
                )
                await telegram_alerts.send_bet_alert(alert)
                logger.info(
                    f"Alert sent: {match.home_team} vs {match.away_team} "
                    f"edge={edge_value:.2%}"
                )
            except Exception as e:
                logger.warning(f"Telegram alert failed (non-fatal): {e}")

        response = build_prediction_response(
            prediction, db_match, orchestrator, sport=sport, data_quality=data_quality, data_source=data_source, available_markets=available_markets
        )
        response.calibration_note = calibration_note
        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Prediction failed. Please verify the match data and try again.")


@router.get("/history")
async def prediction_history(
    outcome: Optional[str] = Query("all", description="Filter: all|won|lost|pending"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_optional_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    q = select(Prediction, Match).outerjoin(Match, Prediction.match_id == Match.id).where(Prediction.user_id == current_user.id).order_by(Prediction.timestamp.desc()).limit(limit)

    # Apply outcome filter
    if outcome and outcome != "all":
        if outcome == "won":
            q = q.where(Prediction.was_correct.is_(True))
        elif outcome == "lost":
            q = q.where(Prediction.was_correct.is_(False))
        elif outcome == "pending":
            q = q.where(Prediction.was_correct.is_(None))

    res = await db.execute(q)
    rows = res.all()

    out = []
    for pred, match in rows:
        out.append({
            "prediction_id": pred.id,
            "match_id": pred.match_id,
            "home_team": getattr(match, 'home_team', None),
            "away_team": getattr(match, 'away_team', None),
            "league": getattr(match, 'league', None),
            "created_at": pred.timestamp.isoformat() if pred.timestamp else None,
            "bet_side": pred.bet_side,
            "confidence": float(pred.confidence or 0.0),
            "final_ev": float(pred.final_ev or 0.0) if getattr(pred, 'final_ev', None) is not None else None,
            "entry_odds": float(pred.entry_odds) if getattr(pred, 'entry_odds', None) is not None else None,
            "was_correct": pred.was_correct,
        })

    return out


@router.get("/accuracy")
async def prediction_accuracy(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_optional_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    total_q = await db.execute(select(func.count(Prediction.id)).where(Prediction.user_id == current_user.id))
    total = total_q.scalar() or 0
    wins_q = await db.execute(select(func.count(Prediction.id)).where(Prediction.user_id == current_user.id, Prediction.was_correct.is_(True)))
    wins = wins_q.scalar() or 0

    win_rate = (wins / total) if total > 0 else 0.0

    # Current streak (consecutive wins from latest)
    streak = 0
    if total > 0:
        recent_q = select(Prediction).where(Prediction.user_id == current_user.id).order_by(Prediction.timestamp.desc()).limit(100)
        recent_res = await db.execute(recent_q)
        recent_preds = recent_res.scalars().all()
        for p in recent_preds:
            if p.was_correct is True:
                streak += 1
            else:
                break

    return {
        "total": total,
        "win_rate": round(win_rate, 3),
        "current_streak": streak,
        "best_league": None,
    }


@router.get("/{match_id}/insights")
async def get_match_insights(match_id: int, db: AsyncSession = Depends(get_db)):
    """
    Generate AI tactical insights for a specific prediction using Native VIT Intelligence.
    """
    from app.db.models import Match, Prediction
    from app.services.deterministic_insights import generate_match_insights
    from sqlalchemy import desc

    m = (await db.execute(select(Match).where(Match.id == match_id))).scalar_one_or_none()
    p = (await db.execute(select(Prediction).where(Prediction.match_id == match_id).order_by(desc(Prediction.timestamp)).limit(1))).scalar_one_or_none()

    if not m or not p:
        raise HTTPException(status_code=404, detail="Match or Prediction not found")

    insight_data = await generate_match_insights(
        home_team=m.home_team,
        away_team=m.away_team,
        league=m.league or "unknown",
        home_prob=float(p.home_prob or 0.33),
        draw_prob=float(p.draw_prob or 0.33),
        away_prob=float(p.away_prob or 0.34),
        over_25_prob=float(p.over_25_prob or 0),
        btts_prob=float(p.btts_prob or 0),
        bet_side=p.bet_side,
        edge=float(p.vig_free_edge or 0),
        entry_odds=float(p.entry_odds or 2.0),
        confidence=float(p.confidence or 0.5),
    )

    return {
        "match_id": match_id,
        "native": insight_data,
        "source": "native"
    }

@router.get("/accumulator")
async def get_daily_accumulator(
    limit: int = Query(default=3, ge=2, le=5),
    db: AsyncSession = Depends(get_db)
):
    """Generate a high-value daily accumulator combo."""
    from app.services.accumulator_service import AccumulatorService, AccumulatorLeg
    from app.db.models import Match, Prediction
    from sqlalchemy import select, and_
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    lookahead = now + timedelta(days=1)

    # 1. Fetch upcoming matches with predictions and odds
    stmt = (
        select(Match, Prediction)
        .join(Prediction, Match.id == Prediction.match_id)
        .where(Match.kickoff_time >= now)
        .where(Match.kickoff_time <= lookahead)
        .where(Match.opening_odds_home.isnot(None))
        .where(Prediction.vig_free_edge > 0.02)
        .order_by(Prediction.vig_free_edge.desc())
        .limit(10)
    )
    res = await db.execute(stmt)
    pairs = res.all()

    candidates = []
    for match, pred in pairs:
        # Determine best side for this leg
        best_prob = max(pred.home_prob, pred.draw_prob, pred.away_prob)
        if best_prob == pred.home_prob:
            selection, odds = 'home', match.opening_odds_home
        elif best_prob == pred.away_prob:
            selection, odds = 'away', match.opening_odds_away
        else:
            selection, odds = 'draw', match.opening_odds_draw

        if odds and odds > 1.0:
            candidates.append(AccumulatorLeg(
                match_id=match.id,
                home_team=match.home_team,
                away_team=match.away_team,
                selection=selection,
                model_prob=best_prob,
                market_odds=odds
            ))

    if not candidates:
        return {"error": "No value candidates found for accumulator today"}

    svc = AccumulatorService()
    return await svc.generate_optimized_accumulator(candidates, min_legs=2, max_legs=limit)
