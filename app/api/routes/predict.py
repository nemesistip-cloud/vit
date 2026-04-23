# app/api/routes/predict.py
# VIT Sports Intelligence Network — v2.1.0
# Fix: Full prediction data passed to BetAlert (models_used, all probs, all odds)
# Fix: Alert sent on ANY prediction (not just >3% edge) so Telegram shows status
# Fix: Models count and data source included in response

import hashlib
import json
import logging
import math
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.config import APP_VERSION, MAX_STAKE, MIN_EDGE_THRESHOLD
from app.db.database import get_db
from app.db.models import Match, Prediction
from app.schemas.schemas import MatchRequest, PredictionResponse
from app.services.clv_tracker import CLVTracker
from app.services.market_utils import MarketUtils
from app.api.middleware.auth import verify_api_key
from app.api.deps import get_optional_user
from app.services.alerts import BetAlert
from app.core.dependencies import get_orchestrator_dep, get_telegram_dep

from app.tasks.clv import update_clv_task
from app.tasks.edges import recalculate_edges_task
from app.services.decision_logger import DecisionLogger
from app.services.predict_features import build_predict_features

logger = logging.getLogger(__name__)

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
    # Include rounded odds so market movement triggers a fresh prediction.
    # Include user_id so different users never share a cached prediction record.
    odds = match.market_odds or {}
    odds_sig = {k: round(float(v), 2) for k, v in odds.items() if v}
    content = {
        "home_team":    match.home_team,
        "away_team":    match.away_team,
        "kickoff_time": match.kickoff_time.isoformat(),
        "league":       match.league,
        "odds_sig":     odds_sig,
        "user_id":      user_id,
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:32]


def _entropy_confidence(hp: float, dp: float, ap: float) -> float:
    """
    Map a 1x2 probability distribution to a confidence score in [0.50, 0.95].

    Uniform (1/3, 1/3, 1/3) → 0.50 (no information).
    Sharp consensus (e.g. 0.85, 0.10, 0.05) → ~0.93.

    Mirrors the entropy→confidence mapping inside ModelOrchestrator so that
    the vig-removal fallback path produces a confidence value derived from
    the actual data rather than a hardcoded constant.
    """
    probs = [p for p in (hp, dp, ap) if p > 0]
    if not probs:
        return 0.50
    ent = -sum(p * math.log(p) for p in probs)
    max_ent = math.log(3)
    normalised = max(0.0, min(1.0, 1.0 - (ent / max_ent)))
    return round(0.50 + normalised * 0.45, 3)


def validate_prediction_response(result: dict, market_odds: Optional[dict] = None) -> dict:
    """
    Validate orchestrator response — normalise probabilities, fail fast on missing fields.

    Fallback policy (per VIT spec §1.4):
    NEVER return 33/33/33 uniform distribution.
    If the ensemble returns zero-sum, apply vig-removed market probabilities instead.
    """
    required = ["home_prob", "draw_prob", "away_prob"]
    for field in required:
        if field not in result:
            raise ValueError(f"Orchestrator response missing: {field}")

    hp = float(result["home_prob"])
    dp = float(result["draw_prob"])
    ap = float(result["away_prob"])
    total = hp + dp + ap

    if total <= 0:
        # Spec §1.4: use vig-removed market odds — never 33/33/33
        logger.warning("Orchestrator returned zero-sum probabilities — applying market vig-removal fallback")
        odds = market_odds or {}
        ho = MarketUtils.validate_odds(odds.get("home"))
        do_ = MarketUtils.validate_odds(odds.get("draw"))
        ao = MarketUtils.validate_odds(odds.get("away"))
        if ho and do_ and ao:
            implied = {"home": 1 / ho, "draw": 1 / do_, "away": 1 / ao}
            vig_total = sum(implied.values())
            result["home_prob"] = implied["home"] / vig_total
            result["draw_prob"] = implied["draw"] / vig_total
            result["away_prob"] = implied["away"] / vig_total
            result["fallback_used"] = True
            # Derive confidence from the actual spread of vig-removed market
            # probabilities (entropy-based) rather than a constant. Uniform
            # ~0.50, sharp consensus ~0.95 — matches ModelOrchestrator's
            # entropy→confidence mapping so downstream logic stays consistent.
            result["confidence"] = _entropy_confidence(
                result["home_prob"], result["draw_prob"], result["away_prob"]
            )
            logger.info(
                "Fallback probs from vig-removal: H=%.3f D=%.3f A=%.3f conf=%.3f",
                result["home_prob"], result["draw_prob"], result["away_prob"],
                result["confidence"],
            )
        else:
            # No odds at all — raise so the caller can surface the error clearly
            raise ValueError(
                "Orchestrator produced zero-sum probabilities and no valid market odds "
                "were supplied — cannot generate a prediction for this fixture."
            )
    else:
        # Always normalise — ensemble models can drift; 15% tolerance before hard error
        if abs(total - 1.0) > 0.15:
            raise ValueError(f"Probabilities sum to {total:.4f} (>15% off) — likely model failure")
        result["home_prob"] = hp / total
        result["draw_prob"] = dp / total
        result["away_prob"] = ap / total

    return result


def build_prediction_response(
    prediction: Prediction,
    match: Match,
    orchestrator: Optional[object] = None,
    data_quality: Optional[dict] = None,
    data_source: str = "neural_ensemble",
) -> PredictionResponse:
    # Calculate intelligence metrics
    models_used = len(prediction.model_insights) if prediction.model_insights else 0
    neural_consensus_score = prediction.consensus_prob * 100  # Convert to percentage
    
    # Intelligence rating based on confidence and edge
    if prediction.confidence > 0.8 and prediction.vig_free_edge > 0.05:
        intelligence_rating = "EXCELLENT"
    elif prediction.confidence > 0.7 and prediction.vig_free_edge > 0.03:
        intelligence_rating = "VERY GOOD"
    elif prediction.confidence > 0.6 and prediction.vig_free_edge > 0.02:
        intelligence_rating = "GOOD"
    elif prediction.confidence > 0.5:
        intelligence_rating = "FAIR"
    else:
        intelligence_rating = "POOR"
    
    # Estimate prediction accuracy based on historical patterns
    prediction_accuracy_estimate = min(85.0, prediction.confidence * 100 + prediction.vig_free_edge * 200)
    
    return PredictionResponse(
        match_id=prediction.match_id,
        home_prob=prediction.home_prob,
        draw_prob=prediction.draw_prob,
        away_prob=prediction.away_prob,
        over_25_prob=prediction.over_25_prob,
        under_25_prob=prediction.under_25_prob,
        btts_prob=prediction.btts_prob,
        consensus_prob=prediction.consensus_prob,
        final_ev=prediction.final_ev,
        recommended_stake=prediction.recommended_stake,
        edge=prediction.vig_free_edge,
        confidence=prediction.confidence,
        timestamp=prediction.timestamp,
        
        # Enhanced Intelligence Data
        models_used=models_used,
        models_total=getattr(orchestrator, '_total_model_specs', models_used) if orchestrator else models_used,
        data_source=data_source,  # Real source from orchestrator (e.g. "differentiated_ensemble_v3")
        bet_side=prediction.bet_side,
        entry_odds=prediction.entry_odds,
        raw_edge=prediction.raw_edge,
        normalized_edge=prediction.normalized_edge,
        vig_free_edge=prediction.vig_free_edge,
        model_weights=prediction.model_weights or {},
        model_insights=prediction.model_insights or [],
        neural_consensus_score=neural_consensus_score,
        intelligence_rating=intelligence_rating,
        prediction_accuracy_estimate=prediction_accuracy_estimate,
        data_quality=data_quality,
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
        if not MarketUtils.validate_odds_dict(match.market_odds):
            logger.warning(
                "PREDICT_FALLBACK market_odds invalid for %s vs %s — using "
                "league-average fallback odds for league=%s",
                match.home_team, match.away_team, match.league,
            )
            match.market_odds = MarketUtils.get_fallback_odds(match.league)
            data_quality["market_odds_fallback"] = True
            data_quality["warnings"].append("market_odds_fallback")

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
                return build_prediction_response(existing_pred, ex_match, orchestrator, cached_dq)

        # --- Find or create match ---
        # First try by external_id (fixture_id)
        db_match = None
        if match.fixture_id and match.fixture_id != "unknown":
            ext_res = await db.execute(
                select(Match).where(Match.external_id == str(match.fixture_id))
            )
            db_match = ext_res.scalar_one_or_none()

        # Then try by teams + kickoff (within 1-hour window for tolerance)
        # Use .scalars().first() instead of scalar_one_or_none() to safely handle
        # duplicate rows without raising MultipleResultsFound.
        if db_match is None:
            window_start = naive_kickoff.replace(second=0, microsecond=0)
            existing_match_res = await db.execute(
                select(Match).where(
                    Match.home_team == match.home_team,
                    Match.away_team == match.away_team,
                    Match.league == match.league,
                    Match.kickoff_time >= window_start,
                )
            )
            db_match = existing_match_res.scalars().first()

        if db_match is None:
            # Create new match record
            db_match = Match(
                home_team=match.home_team,
                away_team=match.away_team,
                league=match.league,
                kickoff_time=naive_kickoff,
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

        features = {
            "home_team":      match.home_team,
            "away_team":      match.away_team,
            "league":         match.league,
            "market_odds":    match.market_odds,     # ← v2.1.0: always passes real odds
            "match_features": match_features,         # ← v4.10.0: real rolling features
        }

        raw_result = await orchestrator.predict(features, idempotency_key)
        pred_data  = raw_result.get("predictions", raw_result)
        result     = validate_prediction_response(pred_data, market_odds=match.market_odds)

        # Vig-removal fallback was triggered inside validate_prediction_response
        if result.get("fallback_used"):
            logger.warning(
                "PREDICT_FALLBACK ensemble returned zero-sum probabilities for "
                "%s vs %s — used vig-removed market odds as final probabilities",
                match.home_team, match.away_team,
            )
            data_quality["vig_removal_fallback"] = True
            data_quality["warnings"].append("vig_removal_fallback")

        # --- Extract all probabilities ---
        home_prob = float(result.get("home_prob", 0.0))
        draw_prob = float(result.get("draw_prob", 0.0))
        away_prob = float(result.get("away_prob", 0.0))

        # --- Extract market odds (with league-aware fallbacks) ---
        fallback = MarketUtils.get_fallback_odds(match.league)
        home_odds = float(match.market_odds.get("home") or fallback.get("home", 2.30))
        draw_odds = float(match.market_odds.get("draw") or fallback.get("draw", 3.30))
        away_odds = float(match.market_odds.get("away") or fallback.get("away", 3.10))

        # --- Best bet calculation ---
        best_bet = MarketUtils.determine_best_bet(
            home_prob, draw_prob, away_prob,
            home_odds, draw_odds, away_odds,
        )

        recommended_stake = min(best_bet.get("kelly_stake", 0), MAX_STAKE)

        probs         = {"home": home_prob, "draw": draw_prob, "away": away_prob}
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

        # --- Save prediction ---
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
            consensus_prob=consensus_prob,
            final_ev=best_bet.get("edge", 0),
            recommended_stake=recommended_stake,
            model_weights=result.get("model_weights", {}),
            model_insights=model_insights_payload,
            confidence=confidence_val,
            bet_side=best_bet.get("best_side"),
            entry_odds=best_bet.get("odds", 2.0),
            raw_edge=best_bet.get("raw_edge", 0),
            normalized_edge=best_bet.get("edge", 0),
            vig_free_edge=best_bet.get("edge", 0),
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

        # --- CLV tracking ---
        if best_bet.get("has_edge") and best_bet.get("best_side") and best_bet.get("odds", 0) > 0:
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
                    app_url=os.getenv("PUBLIC_APP_URL", ""),
                )
                await telegram_alerts.send_bet_alert(alert)
                logger.info(
                    f"Alert sent: {match.home_team} vs {match.away_team} "
                    f"edge={edge_value:.2%}"
                )
            except Exception as e:
                logger.warning(f"Telegram alert failed (non-fatal): {e}")

        return build_prediction_response(
            prediction, db_match, orchestrator, data_quality, data_source=data_source
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Prediction failed. Please verify the match data and try again.")


@router.get("/{match_id}/insights")
async def get_match_insights(
    match_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AI tactical insights for a specific prediction.
    Returns {gemini, claude, grok} format.
    Falls back to ML-derived synthetic insight when no AI keys are configured.
    """
    import os as _os
    from app.db.models import Match, Prediction
    from app.services.gemini_insights import generate_match_insights

    match_row = await db.execute(select(Match).where(Match.id == match_id))
    match = match_row.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    pred_row = await db.execute(
        select(Prediction)
        .where(Prediction.match_id == match_id)
        .order_by(Prediction.timestamp.desc())
        .limit(1)
    )
    pred = pred_row.scalars().first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    conf = float(pred.confidence) if isinstance(pred.confidence, (int, float)) else 0.5
    home_p = float(pred.home_prob or 0.33)
    draw_p = float(pred.draw_prob or 0.33)
    away_p = float(pred.away_prob or 0.34)
    edge_val = float(pred.vig_free_edge or 0.0)
    over25 = float(pred.over_25_prob or 0.0)
    btts = float(pred.btts_prob or 0.0)
    bet_side = pred.bet_side or "home"

    gemini_key = _os.getenv("GEMINI_API_KEY", "").strip()

    if not gemini_key:
        # ML ensemble fallback — generate rule-based insight from prediction data
        probs = {"home": home_p, "draw": draw_p, "away": away_p}
        leader = max(probs, key=probs.get)
        leader_prob = probs[leader]
        side_label = bet_side.upper()
        synthetic_insight = {
            "summary": (
                f"ML ensemble analysis for {match.home_team} vs {match.away_team}. "
                f"Home win probability: {home_p * 100:.1f}%, "
                f"Draw: {draw_p * 100:.1f}%, "
                f"Away: {away_p * 100:.1f}%. "
                f"The {leader} outcome leads with {leader_prob * 100:.1f}% probability."
            ),
            "key_factors": [
                f"Detected edge: {edge_val * 100:.2f}% above market implied probability",
                f"Over 2.5 goals probability: {over25 * 100:.1f}%",
                f"BTTS probability: {btts * 100:.1f}%",
                "Based on 12-model differentiated statistical ensemble",
            ],
            "recommendation": f"Back {side_label} — {edge_val * 100:.2f}% edge detected at {float(pred.entry_odds or 2.0):.2f}",
            "confidence": conf,
            "provider": "ml_ensemble",
        }
        return {
            "match_id": match_id,
            "gemini": synthetic_insight,
            "claude": None,
            "grok": None,
            "source": "ml_fallback",
        }

    raw = await generate_match_insights(
        home_team=match.home_team,
        away_team=match.away_team,
        league=match.league or "unknown",
        home_prob=home_p,
        draw_prob=draw_p,
        away_prob=away_p,
        over_25_prob=pred.over_25_prob,
        btts_prob=pred.btts_prob,
        bet_side=bet_side,
        edge=edge_val,
        entry_odds=pred.entry_odds,
        confidence=conf,
    )

    gemini_insight = None
    if raw.get("available"):
        gemini_insight = {
            "summary": raw.get("summary"),
            "key_factors": raw.get("key_factors", []),
            "recommendation": raw.get("value_assessment"),
            "confidence": conf,
            "provider": "gemini",
        }

    return {
        "match_id": match_id,
        "gemini": gemini_insight,
        "claude": None,
        "grok": None,
        "source": "gemini" if gemini_insight else "unavailable",
    }
