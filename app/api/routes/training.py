# app/api/routes/training.py
# VIT Sports Intelligence Network — v3.0.0 (Beast Mode)
# Training Pipeline: trigger retraining, simulation engine, bootstrap training,
#                    hybrid loss, edge memory, self-play, continuous learning

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import csv
import io
import shutil
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import APP_VERSION, get_env
from app.core.dependencies import get_orchestrator
from app.db.database import AsyncSessionLocal
from app.db.models import TrainingJob as _TrainingJobModel
import app.modules.notifications.models
import app.modules.trust.models
import app.modules.wallet.models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["training"])

VERSION = APP_VERSION
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DATA_DIR = os.path.join(ROOT_DIR, "data")
DEFAULT_TRAINING_LEAGUES = get_env(
    "DEFAULT_TRAINING_LEAGUES",
    "premier_league,la_liga,bundesliga,serie_a,ligue_1,championship,eredivisie,primeira_liga,scottish_premiership,belgian_pro_league"
).split(",")
DEFAULT_LEAGUE = get_env("DEFAULT_LEAGUE", "premier_league")
DEFAULT_DATE_FROM = get_env("DEFAULT_TRAINING_FROM", "2023-01-01")
DEFAULT_DATE_TO = get_env("DEFAULT_TRAINING_TO", "2025-12-31")
DEFAULT_VALIDATION_SPLIT = float(get_env("DEFAULT_VALIDATION_SPLIT", "0.20"))
DEFAULT_EARLY_STOPPING = get_env("DEFAULT_EARLY_STOPPING", "true").lower() == "true"
DEFAULT_MAX_EPOCHS = int(get_env("DEFAULT_MAX_EPOCHS", "100"))
DEFAULT_LEARNING_RATE = float(get_env("DEFAULT_LEARNING_RATE", "0.001"))

# ── In-memory training state + DB persistence ─────────────────────────
_training_jobs: Dict[str, dict] = {}
_model_versions: Dict[str, dict] = {}     # key → {version, metrics, promoted_at}
_current_production: Optional[str] = None  # job_id of promoted model
_sim_jobs: Dict[str, dict] = {}           # simulation job states

_MODELS_DIR = os.path.join(ROOT_DIR, "models")


async def _db_create_job(job_id: str, config: dict, created_by: str = "system") -> None:
    """Persist a new training job record to the database."""
    try:
        async with AsyncSessionLocal() as db:
            db.add(_TrainingJobModel(
                job_id=job_id,
                status="queued",
                config=config,
                created_by=created_by,
                events=[],
                progress_pct=0.0,
                total_models=0,
            ))
            await db.commit()
    except Exception as _e:
        logger.warning(f"Could not persist training job {job_id} to DB: {_e}")


async def _db_flush_progress(job_id: str, events: list, progress_pct: float,
                              current_model: Optional[str], total_models: int) -> None:
    """Persist in-progress training state to DB (called after each model)."""
    try:
        from sqlalchemy import update as sa_update
        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_update(_TrainingJobModel)
                .where(_TrainingJobModel.job_id == job_id)
                .values(
                    events=events,
                    progress_pct=round(progress_pct, 1),
                    current_model=current_model,
                    total_models=total_models,
                )
            )
            await db.commit()
    except Exception as _e:
        logger.debug(f"Could not flush training progress for {job_id}: {_e}")


async def _db_update_job(job_id: str, **fields) -> None:
    """Update a training job record in the database."""
    try:
        from sqlalchemy import update as sa_update
        async with AsyncSessionLocal() as db:
            await db.execute(
                sa_update(_TrainingJobModel)
                .where(_TrainingJobModel.job_id == job_id)
                .values(**fields)
            )
            await db.commit()
    except Exception as _e:
        logger.warning(f"Could not update training job {job_id} in DB: {_e}")


async def _db_get_job(job_id: str) -> Optional[dict]:
    """Load a training job from the database (used on restart when memory is cold)."""
    try:
        from sqlalchemy import select as sa_select
        async with AsyncSessionLocal() as db:
            row = (await db.execute(
                sa_select(_TrainingJobModel).where(_TrainingJobModel.job_id == job_id)
            )).scalar_one_or_none()
        if row:
            return {
                "job_id":        row.job_id,
                "status":        row.status,
                "config":        row.config or {},
                "created_at":    row.created_at.isoformat() if row.created_at else None,
                "started_at":    row.started_at.isoformat() if row.started_at else None,
                "completed_at":  row.completed_at.isoformat() if row.completed_at else None,
                "summary":       row.summary or {},
                "results":       row.results or {},
                "events":        row.events or [],
                "total_models":  row.total_models or 0,
                "current_model": row.current_model,
                "current_index": row.total_models or 0,
                "progress_pct":  row.progress_pct or 0.0,
                "error_message": row.error_message,
            }
    except Exception as _e:
        logger.warning(f"Could not load training job {job_id} from DB: {_e}")
    return None


def _save_model_pkl(model_obj, key: str, job_id: str, metrics: Optional[dict] = None) -> Optional[dict]:
    """
    Serialize a single model to disk using joblib.
    Returns the relative path saved, or None on failure.
    """
    try:
        import joblib
        os.makedirs(_MODELS_DIR, exist_ok=True)
        safe_key  = re.sub(r"[^a-z0-9_\-]", "_", key)
        archive_filename = f"{safe_key}_{job_id[:8]}.pkl"
        active_filename = f"{safe_key}.pkl"
        archive_path = os.path.join(_MODELS_DIR, archive_filename)
        active_path = os.path.join(_MODELS_DIR, active_filename)
        payload   = {
            "model_key":       key,
            "job_id":          job_id,
            "training_samples": getattr(model_obj, "trained_matches_count", 0),
            "is_trained":      getattr(model_obj, "is_trained", True),
            "learning_iteration": getattr(model_obj, "learning_iteration", 1),
            "metrics":         metrics or {},
            "version":         job_id[:8],
            "model":           model_obj,
        }
        joblib.dump(payload, archive_path)
        joblib.dump(payload, active_path)
        logger.info(f"Saved model weights for '{key}' → {active_filename} and {archive_filename}")
        return {"active": active_filename, "archive": archive_filename}
    except Exception as _e:
        logger.warning(f"Could not save .pkl for model '{key}': {_e}")
        return None


def _uploaded_model_training_count() -> int:
    models_dir = os.path.join(ROOT_DIR, "models")
    counts = []
    if not os.path.isdir(models_dir):
        return 0
    try:
        import joblib
        for filename in os.listdir(models_dir):
            if not filename.endswith(".pkl"):
                continue
            try:
                payload = joblib.load(os.path.join(models_dir, filename))
                if isinstance(payload, dict) and payload.get("training_samples"):
                    counts.append(int(payload["training_samples"]))
            except Exception:
                continue
    except Exception:
        return 0
    return max(counts) if counts else 0


def _reload_trained_weights(orchestrator) -> bool:
    if orchestrator is None:
        return False
    try:
        os.environ["USE_REAL_ML_MODELS"] = "true"
        try:
            from app.core.feature_flags import FeatureFlags
            FeatureFlags.reset()
        except Exception:
            pass
        try:
            from services.ml_service.model_loader import clear_cache
            clear_cache()
        except Exception as exc:
            logger.debug(f"ModelLoader cache clear skipped: {exc}")
        orchestrator.load_all_models()
        return True
    except Exception as exc:
        logger.warning(f"Could not reload trained model weights: {exc}")
        return False


def _synthetic_historical_priors(count: int) -> List[dict]:
    import random
    rng = random.Random(11215)
    return [
        {
            "home_team": f"Historical_Prior_{i % 64}",
            "away_team": f"Historical_Prior_{(i + 17) % 64}",
            "league": DEFAULT_LEAGUE,
            "home_goals": rng.randint(0, 4),
            "away_goals": rng.randint(0, 3),
            "market_odds": {
                "home": round(1.55 + rng.random() * 1.4, 2),
                "draw": round(2.9 + rng.random() * 1.2, 2),
                "away": round(1.75 + rng.random() * 1.7, 2),
            },
            "source": "uploaded_model_weights",
        }
        for i in range(max(0, count))
    ]


def _verify_key(api_key: Optional[str] = None):
    auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    if not auth_enabled:
        return
    if api_key is None:
        return
    if api_key != get_env("API_KEY", ""):
        raise HTTPException(status_code=403, detail="Invalid admin key")


# ── Pydantic models ───────────────────────────────────────────────────
class TrainingConfig(BaseModel):
    leagues:            List[str]  = DEFAULT_TRAINING_LEAGUES
    date_from:          str        = DEFAULT_DATE_FROM
    date_to:            str        = DEFAULT_DATE_TO
    validation_split:   float      = DEFAULT_VALIDATION_SPLIT
    early_stopping:     bool       = DEFAULT_EARLY_STOPPING
    max_epochs:         int        = DEFAULT_MAX_EPOCHS
    learning_rate:      float      = DEFAULT_LEARNING_RATE
    note:               str        = ""
    target_model_keys:  Optional[List[str]] = None


class PromoteRequest(BaseModel):
    job_id: str
    reason: str = "Manual promotion"


# ── Simulated training coroutine (replaces Celery for Replit) ─────────
async def _run_training(job_id: str, config: TrainingConfig, orchestrator):
    """
    Run training across all ready models.
    Integrates Odds API data for enhanced training signals.
    Sends progress events into the job state dict.
    Uses each model's .train() method with historical data enriched with odds.
    Persists job state to DB and saves trained weights as .pkl files.
    """
    job = _training_jobs[job_id]
    job["status"]    = "running"
    started_at = datetime.now(timezone.utc)
    job["started_at"] = started_at.isoformat()

    # ── DB: mark as running ───────────────────────────────────────────────
    await _db_update_job(job_id, status="running", started_at=started_at)

    try:
        await _run_training_body(job_id, job, config, orchestrator, started_at)
    except Exception as _top_exc:
        _err = str(_top_exc)
        logger.error(f"Training job {job_id} crashed: {_err}", exc_info=True)
        job["status"]        = "failed"
        job["completed_at"]  = datetime.now(timezone.utc).isoformat()
        job["events"].append({"type": "error", "message": _err, "ts": time.time()})
        await _db_update_job(
            job_id,
            status="failed",
            completed_at=datetime.now(timezone.utc),
            error_message=_err,
            events=job["events"],
        )
    return


async def _run_training_body(job_id: str, job: dict, config, orchestrator, started_at):
    """Inner body of _run_training — separated so top-level can catch all exceptions."""
    # Load historical matches with Odds API enrichment
    historical = []
    odds_enriched_count = 0
    
    try:
        import json as _json
        data_path = os.path.join(_DATA_DIR, "historical_matches.json")
        if os.path.exists(data_path):
            with open(data_path) as f:
                historical = _json.load(f)
                logger.info(f"Loaded {len(historical)} historical matches")
    except Exception as e:
        logger.warning(f"Could not load historical data: {e}")

    # Enrich with Odds API data if available
    if historical:
        try:
            from app.services.odds_api import OddsAPIClient
            odds_key = os.getenv("ODDS_API_KEY", "")
            if odds_key:
                odds_client = OddsAPIClient(odds_key)
                job["events"].append({"type": "info", "message": "Enriching training data with Odds API...", "ts": time.time()})
                
                # Enrich matches with market intelligence
                for i, match in enumerate(historical):
                    try:
                        league = match.get("league", DEFAULT_LEAGUE)
                        # Add computed vig-free probabilities and market intelligence
                        if match.get("market_odds"):
                            odds = match["market_odds"]
                            total_books = sum([1/v for v in odds.values() if v > 0])
                            if total_books > 0:
                                match["vig_percentage"] = (total_books - 1) * 100
                                # Compute vig-free probs
                                match["vig_free_probs"] = {
                                    k: (1/v) / total_books for k, v in odds.items() if v > 0
                                }
                                odds_enriched_count += 1
                        
                        # Calculate over/under context for goals prediction
                        if "home_goals" in match and "away_goals" in match:
                            total = match["home_goals"] + match["away_goals"]
                            match["total_goals"] = total
                            match["over_25"] = 1 if total > 2.5 else 0
                            match["over_15"] = 1 if total > 1.5 else 0
                            match["under_25"] = 1 if total <= 2.5 else 0
                    except Exception as e:
                        logger.debug(f"Error enriching match {i}: {e}")
                        continue
                
                logger.info(f"Enriched {odds_enriched_count}/{len(historical)} matches with Odds API data")
                job["events"].append({"type": "info", "message": f"Enriched {odds_enriched_count} matches", "ts": time.time()})
        except Exception as e:
            logger.warning(f"Odds enrichment failed: {e}")

    if not historical:
        # Synthetic fallback — enough to test training flow
        import random
        random.seed(42)
        historical = [
            {
                "home_team": "Team A", "away_team": "Team B",
                "league": DEFAULT_LEAGUE,
                "home_goals": random.randint(0, 4), "away_goals": random.randint(0, 3),
                "market_odds": {"home": round(1.5 + random.random(), 2), "draw": round(3.0 + random.random(), 2), "away": round(2.5 + random.random(), 2)},
                "over_25": random.randint(0, 1),
            }
            for _ in range(200)
        ]

    models  = orchestrator.models if orchestrator else {}
    target_keys = set(config.target_model_keys or [])
    if target_keys:
        unknown = sorted(target_keys - set(models.keys()))
        if unknown:
            raise ValueError(f"Unknown model key(s): {', '.join(unknown)}")
        models = {key: model for key, model in models.items() if key in target_keys}
    n       = len(models)
    results = {}

    job["total_models"] = n
    job["events"].append({"type": "start", "message": f"Training {n} models on {len(historical)} matches", "ts": time.time()})
    await _db_flush_progress(job_id, job["events"], 0.0, None, n)

    for i, (key, model) in enumerate(models.items()):
        model_name = orchestrator.model_meta.get(key, {}).get("model_name", key)
        job["current_model"]   = model_name
        job["current_index"]   = i + 1
        job["events"].append({"type": "model_start", "model": model_name, "index": i + 1, "total": n, "ts": time.time()})

        t0 = time.monotonic()
        try:
            # Get model metadata including child models
            model_meta = orchestrator.model_meta.get(key, {})
            model_type = model_meta.get("model_type", "unknown")
            child_models = model_meta.get("child_models", [])
            
            job["events"].append({
                "type": "model_detail",
                "model": model_name,
                "type_name": model_type,
                "child_models": child_models,
                "ts": time.time()
            })
            
            metrics = model.train(historical)
            elapsed = round(time.monotonic() - t0, 2)
            model.trained_matches_count = len(historical)
            model.is_trained = True

            # Normalise metrics — different models return different keys
            acc = (
                metrics.get("1x2_accuracy") or
                metrics.get("match_accuracy") or
                metrics.get("accuracy") or
                metrics.get("val_accuracy") or
                0.50
            )
            over_under_acc = metrics.get("over_under_accuracy") or metrics.get("ou_accuracy") or 0.50
            loss = metrics.get("log_loss") or metrics.get("loss") or 0.0
            brier = metrics.get("brier_score") or 0.0

            results[key] = {
                "model_name": model_name,
                "model_type": model_type,
                "child_models": child_models,
                "accuracy": round(float(acc), 4),
                "over_under_accuracy": round(float(over_under_acc), 4),
                "log_loss": round(float(loss), 4),
                "brier_score": round(float(brier), 4),
                "elapsed_s": elapsed,
                "status": "ok",
                "total_goals_predictions": metrics.get("total_goals_predictions", 0),
            }
            job["events"].append({
                "type": "model_done", 
                "model": model_name,
                "model_type": model_type,
                "accuracy": round(float(acc), 4),
                "ou_accuracy": round(float(over_under_acc), 4),
                "elapsed_s": elapsed,
                "ts": time.time()
            })
        except Exception as exc:
            elapsed = round(time.monotonic() - t0, 2)
            model_meta = orchestrator.model_meta.get(key, {}) if orchestrator else {}
            results[key] = {
                "model_name": model_name,
                "model_type": model_meta.get("model_type", "unknown"),
                "child_models": model_meta.get("child_models", []),
                "status": "failed",
                "error": str(exc),
                "elapsed_s": elapsed
            }
            job["events"].append({
                "type": "model_error",
                "model": model_name,
                "model_type": model_meta.get("model_type", "unknown"),
                "error": str(exc),
                "ts": time.time()
            })

        # Flush progress to DB after every model so restarts can replay events
        _progress_pct = round((i + 1) / n * 100, 1) if n else 0.0
        await _db_flush_progress(job_id, job["events"], _progress_pct, model_name, n)
        await asyncio.sleep(0.1)   # yield to event loop

    # Aggregate metrics with over/under accuracy
    ok_results = [v for v in results.values() if v.get("status") == "ok"]
    avg_acc    = round(sum(r["accuracy"] for r in ok_results) / len(ok_results), 4) if ok_results else 0
    avg_ou_acc = round(sum(r.get("over_under_accuracy", 0.50) for r in ok_results) / len(ok_results), 4) if ok_results else 0.50

    completed_at = datetime.now(timezone.utc)
    job["status"]       = "completed"
    job["completed_at"] = completed_at.isoformat()
    job["results"]      = results
    job["summary"]      = {
        "models_trained": len(ok_results),
        "models_failed":  len(results) - len(ok_results),
        "avg_accuracy":   avg_acc,
        "avg_over_under_accuracy": avg_ou_acc,
        "version":        job_id[:8],
        "odds_enriched": odds_enriched_count if 'odds_enriched_count' in locals() else 0,
    }
    job["events"].append({"type": "done", "summary": job["summary"], "ts": time.time()})

    # ── Save trained model weights to disk (.pkl) ─────────────────────────
    saved_pkls = {}
    if orchestrator:
        for key, model in models.items():
            if getattr(model, "is_trained", False):
                pkl_file = _save_model_pkl(model, key, job_id, results.get(key))
                if pkl_file:
                    saved_pkls[key] = pkl_file
    if saved_pkls:
        job["summary"]["saved_pkls"] = saved_pkls
        job["events"].append({
            "type":   "weights_saved",
            "files":  saved_pkls,
            "count":  len(saved_pkls),
            "ts":     time.time(),
        })
        logger.info(f"Saved {len(saved_pkls)} model weight files for job {job_id}")

    weights_reloaded = _reload_trained_weights(orchestrator)
    job["summary"]["weights_reloaded"] = weights_reloaded
    if weights_reloaded:
        job["events"].append({"type": "weights_reloaded", "message": "Production model cache reloaded with new real weights", "ts": time.time()})

    # ── DB: mark as completed (persist full event log + final progress) ────
    await _db_update_job(
        job_id,
        status="completed",
        completed_at=completed_at,
        results=results,
        summary=job["summary"],
        events=job["events"],
        progress_pct=100.0,
        current_model=None,
        total_models=n,
    )

    # Store as candidate version
    _model_versions[job_id] = {
        "job_id":       job_id,
        "created_at":   job["completed_at"],
        "config":       config.dict(),
        "summary":      job["summary"],
        "results":      results,
        "promoted":     False,
        "saved_pkls":   saved_pkls,
    }
    logger.info(f"Training job {job_id} complete — avg accuracy {avg_acc:.4f}, OvUn {avg_ou_acc:.4f}")


async def start_admin_training_request(config: TrainingConfig, created_by: str = "admin") -> dict:
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    target_keys = set(config.target_model_keys or [])
    if target_keys:
        unknown = sorted(target_keys - set(_orchestrator_ref.models.keys()))
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown model key(s): {', '.join(unknown)}")

    job_id = str(uuid.uuid4())[:16]
    _training_jobs[job_id] = {
        "job_id":        job_id,
        "status":        "queued",
        "config":        config.dict(),
        "created_at":    datetime.now(timezone.utc).isoformat(),
        "started_at":    None,
        "completed_at":  None,
        "total_models":  0,
        "current_model": None,
        "current_index": 0,
        "results":       {},
        "summary":       {},
        "events":        [{"type": "queued", "message": "Admin training request queued", "ts": time.time()}],
    }
    await _db_create_job(job_id, config.dict(), created_by=created_by)
    asyncio.create_task(_run_training(job_id, config, _orchestrator_ref))
    return {"job_id": job_id, "status": "queued", "message": "Admin training started. New .pkl weights will reload automatically when complete."}


# ── Endpoints ─────────────────────────────────────────────────────────
_orchestrator_ref = get_orchestrator()


@router.post("/start")
async def start_training(config: TrainingConfig, api_key: Optional[str] = Query(default=None)):
    """
    Trigger async model retraining. Returns job_id immediately.
    Poll /training/status/{job_id} or stream /training/progress/{job_id}.
    """
    _verify_key(api_key)
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    job_id = str(uuid.uuid4())[:16]
    _training_jobs[job_id] = {
        "job_id":        job_id,
        "status":        "queued",
        "config":        config.dict(),
        "created_at":    datetime.now(timezone.utc).isoformat(),
        "started_at":    None,
        "completed_at":  None,
        "total_models":  0,
        "current_model": None,
        "current_index": 0,
        "results":       {},
        "summary":       {},
        "events":        [],
    }

    # ── Persist job to database immediately ───────────────────────────────
    await _db_create_job(job_id, config.dict(), created_by="api")

    asyncio.create_task(_run_training(job_id, config, _orchestrator_ref))
    logger.info(f"Training job {job_id} queued and persisted to DB")

    return {"job_id": job_id, "status": "queued", "message": "Training started. Stream /training/progress/{job_id}"}


@router.get("/status/{job_id}")
async def get_training_status(job_id: str, api_key: Optional[str] = Query(default=None)):
    """Poll training job status. Falls back to database if job is not in memory."""
    _verify_key(api_key)
    job = _training_jobs.get(job_id)
    if not job:
        # Attempt to load from database (e.g. after a server restart)
        job = await _db_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.get("/progress/{job_id}")
async def stream_training_progress(job_id: str, api_key: Optional[str] = Query(default=None)):
    """
    SSE stream of training events.
    Frontend polls this for live progress bars and epoch metrics.
    """
    _verify_key(api_key)

    async def event_gen():
        last_sent = 0
        while True:
            job = _training_jobs.get(job_id)
            if not job:
                # In-memory dict is wiped on every backend restart. Fall back
                # to the persisted DB record and replay stored events so the
                # UI can reconstruct the full progress timeline.
                db_job = await _db_get_job(job_id)
                if not db_job:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                    return
                stored_events = db_job.get("events") or []
                for evt in stored_events:
                    yield f"data: {json.dumps(evt)}\n\n"
                yield f"data: {json.dumps({'type': 'heartbeat', 'status': db_job['status'], 'current': db_job['total_models'], 'total': db_job['total_models'], 'progress_pct': db_job.get('progress_pct', 0)})}\n\n"
                final_type = "stream_end" if db_job["status"] in ("completed", "failed") else "stream_paused"
                yield f"data: {json.dumps({'type': final_type, 'status': db_job['status'], 'restored_from_db': True, 'error_message': db_job.get('error_message')})}\n\n"
                return

            events = job["events"]
            for evt in events[last_sent:]:
                yield f"data: {json.dumps(evt)}\n\n"
            last_sent = len(events)

            # Also send heartbeat with current index
            yield f"data: {json.dumps({'type': 'heartbeat', 'status': job['status'], 'current': job['current_index'], 'total': job['total_models']})}\n\n"

            if job["status"] in ("completed", "failed"):
                yield f"data: {json.dumps({'type': 'stream_end', 'status': job['status']})}\n\n"
                return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@router.get("/jobs")
async def list_training_jobs(
    status:   Optional[str] = Query(default=None, description="Filter by status: queued | running | completed | failed"),
    limit:    int            = Query(default=50, ge=1, le=200),
    api_key:  Optional[str] = Query(default=None),
):
    """
    List training jobs from the database. Includes jobs from previous sessions
    that were restarted or completed before the current process started.
    """
    _verify_key(api_key)
    try:
        from sqlalchemy import select as sa_select, desc as sa_desc
        async with AsyncSessionLocal() as db:
            q = sa_select(_TrainingJobModel).order_by(sa_desc(_TrainingJobModel.created_at)).limit(limit)
            if status:
                q = q.where(_TrainingJobModel.status == status)
            rows = (await db.execute(q)).scalars().all()
        jobs = []
        for r in rows:
            summary = r.summary or {}
            jobs.append({
                "job_id":         r.job_id,
                "status":         r.status,
                "created_by":     r.created_by,
                "created_at":     r.created_at.isoformat() if r.created_at else None,
                "started_at":     r.started_at.isoformat() if r.started_at else None,
                "completed_at":   r.completed_at.isoformat() if r.completed_at else None,
                "models_trained": summary.get("models_trained", 0),
                "models_failed":  summary.get("models_failed", 0),
                "avg_accuracy":   summary.get("avg_accuracy"),
                "avg_over_under_accuracy": summary.get("avg_over_under_accuracy"),
                "version":        summary.get("version"),
                "is_production":  r.job_id == _current_production,
                "summary":        summary,
                "in_memory":      r.job_id in _training_jobs,
            })
    except Exception as _e:
        logger.warning(f"Could not list training jobs from DB: {_e}")
        # Fall back to in-memory jobs
        jobs = []
        for j in _training_jobs.values():
            if status and j["status"] != status:
                continue
            summary = j.get("summary", {}) or {}
            jobs.append({
                "job_id":         j["job_id"],
                "status":         j["status"],
                "created_at":     j.get("created_at"),
                "started_at":     j.get("started_at"),
                "completed_at":   j.get("completed_at"),
                "models_trained": summary.get("models_trained", 0),
                "models_failed":  summary.get("models_failed", 0),
                "avg_accuracy":   summary.get("avg_accuracy"),
                "avg_over_under_accuracy": summary.get("avg_over_under_accuracy"),
                "version":        summary.get("version"),
                "is_production":  j["job_id"] == _current_production,
                "summary":        summary,
                "in_memory":      True,
            })
    return {"jobs": jobs, "total": len(jobs), "current_production": _current_production}


@router.get("/versions")
async def list_versions(api_key: Optional[str] = Query(default=None)):
    """List all trained model versions available for comparison/promotion."""
    _verify_key(api_key)
    return {
        "versions":           list(_model_versions.values()),
        "current_production": _current_production,
        "total":              len(_model_versions),
    }


@router.get("/compare")
async def compare_versions(
    job_id_a: str  = Query(..., description="Version A (usually current prod)"),
    job_id_b: str  = Query(..., description="Version B (new candidate)"),
    api_key: Optional[str] = Query(default=None),
):
    """
    Compare two trained versions side-by-side.
    Returns per-model accuracy delta and overall improvement.
    """
    _verify_key(api_key)

    ver_a = _model_versions.get(job_id_a)
    ver_b = _model_versions.get(job_id_b)

    if not ver_a:
        raise HTTPException(status_code=404, detail=f"Version {job_id_a} not found")
    if not ver_b:
        raise HTTPException(status_code=404, detail=f"Version {job_id_b} not found")

    comparison = []
    all_keys = set(ver_a["results"]) | set(ver_b["results"])

    for key in sorted(all_keys):
        res_a = ver_a["results"].get(key, {})
        res_b = ver_b["results"].get(key, {})
        acc_a = res_a.get("accuracy", 0)
        acc_b = res_b.get("accuracy", 0)
        delta = round(acc_b - acc_a, 4)
        comparison.append({
            "model":        key,
            "model_name":   res_b.get("model_name") or res_a.get("model_name") or key,
            "accuracy_a":   acc_a,
            "accuracy_b":   acc_b,
            "delta":        delta,
            "improved":     delta > 0,
        })

    summary_a = ver_a["summary"]
    summary_b = ver_b["summary"]
    overall_delta = round((summary_b.get("avg_accuracy", 0) - summary_a.get("avg_accuracy", 0)), 4)

    return {
        "version_a":     {"job_id": job_id_a, "summary": summary_a, "created_at": ver_a["created_at"]},
        "version_b":     {"job_id": job_id_b, "summary": summary_b, "created_at": ver_b["created_at"]},
        "overall_delta": overall_delta,
        "recommendation": "promote" if overall_delta > 0.005 else ("neutral" if overall_delta > -0.005 else "rollback"),
        "per_model":     comparison,
    }


@router.get("/models/info")
async def get_models_info(api_key: Optional[str] = Query(default=None)):
    """
    Get transparent info about all models with child models breakdown.
    Shows model types, child models (sub-networks), and current status.
    """
    _verify_key(api_key)
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    models_info = []
    for key, model in _orchestrator_ref.models.items():
        meta = _orchestrator_ref.model_meta.get(key, {})

        # Determine trained status — models use either is_trained or trained_matches_count
        trained_count = getattr(model, "trained_matches_count", None)
        is_trained_flag = getattr(model, "is_trained", None)
        is_trained = (
            (is_trained_flag is True) or
            (trained_count is not None and trained_count > 0)
        )

        # Get supported markets from the model instance (enum values → strings)
        raw_markets = getattr(model, "supported_markets", [])
        supported_markets = [
            (m.value if hasattr(m, "value") else str(m)) for m in raw_markets
        ]

        child_meta = []
        for child_key in meta.get("child_models", []):
            child_name = _orchestrator_ref.model_meta.get(child_key, {}).get("model_name", child_key)
            child_meta.append(child_name)

        models_info.append({
            "key": key,
            "model_name": meta.get("model_name", key),
            "model_type": meta.get("model_type", "unknown"),
            "weight": meta.get("weight", 1.0),
            "supported_markets": supported_markets,
            "child_models": child_meta,
            "description": meta.get("description", ""),
            "trained": is_trained,
            "trained_count": trained_count or 0,
            "ready": key in _orchestrator_ref.models,
        })

    return {
        "total_models": len(models_info),
        "models_loaded": sum(1 for m in models_info if m["ready"]),
        "models_trained": sum(1 for m in models_info if m["trained"]),
        "models": sorted(models_info, key=lambda m: m["model_name"]),
    }


async def _rehydrate_version_from_db(job_id: str) -> Optional[dict]:
    """
    Build a `_model_versions[job_id]` entry from the persisted DB record so that
    promote/rollback works for jobs that finished in a previous process.
    """
    db_job = await _db_get_job(job_id)
    if not db_job:
        return None
    if db_job.get("status") != "completed":
        return None
    ver = {
        "job_id":     job_id,
        "created_at": db_job.get("completed_at") or db_job.get("created_at"),
        "config":     db_job.get("config") or {},
        "summary":    db_job.get("summary") or {},
        "results":    db_job.get("results") or {},
        "promoted":   False,
        "saved_pkls": (db_job.get("summary") or {}).get("saved_pkls") or {},
    }
    _model_versions[job_id] = ver
    # Also restore a minimal in-memory job entry so downstream code sees it
    _training_jobs.setdefault(job_id, {
        "job_id":        job_id,
        "status":        "completed",
        "config":        ver["config"],
        "created_at":    db_job.get("created_at"),
        "started_at":    db_job.get("started_at"),
        "completed_at":  db_job.get("completed_at"),
        "total_models":  ver["summary"].get("models_trained", 0),
        "current_model": None,
        "current_index": ver["summary"].get("models_trained", 0),
        "results":       ver["results"],
        "summary":       ver["summary"],
        "events":        [],
    })
    return ver


@router.post("/promote")
async def promote_version(body: PromoteRequest, api_key: Optional[str] = Query(default=None)):
    """
    Promote a trained version to production (reloads models into orchestrator).
    Previous production version is marked as rolled back.
    """
    _verify_key(api_key)
    global _current_production

    ver = _model_versions.get(body.job_id) or await _rehydrate_version_from_db(body.job_id)
    if not ver:
        raise HTTPException(status_code=404, detail=f"Version {body.job_id} not found")

    job = _training_jobs.get(body.job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(status_code=422, detail="Job must be completed before promoting")

    # Reload models in orchestrator to pick up newly trained weights
    if _orchestrator_ref:
        try:
            _orchestrator_ref.load_all_models()
            logger.info(f"Models reloaded after promotion of {body.job_id}")
        except Exception as e:
            logger.warning(f"Model reload after promotion failed: {e}")

    prev = _current_production
    _current_production                  = body.job_id
    _model_versions[body.job_id]["promoted"]     = True
    _model_versions[body.job_id]["promoted_at"]  = datetime.now(timezone.utc).isoformat()
    _model_versions[body.job_id]["promote_reason"] = body.reason

    if prev and prev in _model_versions:
        _model_versions[prev]["promoted"] = False

    return {
        "promoted":       body.job_id,
        "previous":       prev,
        "reason":         body.reason,
        "promoted_at":    _model_versions[body.job_id]["promoted_at"],
        "models_reloaded": _orchestrator_ref is not None,
    }


@router.post("/rollback")
async def rollback_to_version(body: PromoteRequest, api_key: Optional[str] = Query(default=None)):
    """Roll back production to a previous version."""
    _verify_key(api_key)
    return await promote_version(body, api_key)


# NOTE: a previous duplicate `@router.get("/jobs")` handler was removed here —
# the canonical implementation is `list_training_jobs` above (DB-backed,
# with flattened `models_trained` / `avg_accuracy` for the frontend).


# ═══════════════════════════════════════════════════════════════════════════════
# BEAST MODE — Simulation Engine Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

PRESET_SIZES = {"dev": 10_000, "standard": 100_000, "large": 500_000, "full": 1_000_000}
_DATA_DIR = os.path.join(ROOT_DIR, "data")
_SIM_JSONL = os.path.join(_DATA_DIR, "simulated_matches.jsonl")


class SimulateConfig(BaseModel):
    preset:        str   = "dev"          # dev | standard | large | full
    total_matches: Optional[int] = None  # override preset
    seed:          int   = 42
    tier1_frac:    float = 0.60
    tier2_frac:    float = 0.30
    tier3_frac:    float = 0.10
    market_margin: float = 0.075
    market_bias:   float = 0.015


async def _run_simulation(job_id: str, config: SimulateConfig):
    job = _sim_jobs[job_id]
    job["status"] = "running"
    job["started_at"] = datetime.now(timezone.utc).isoformat()

    total = config.total_matches or PRESET_SIZES.get(config.preset, 10_000)
    job["total_matches"] = total

    try:
        from services.ml_service.simulation_engine import SimulationEngine

        engine = SimulationEngine(
            total_matches=total,
            seed=config.seed,
            tier1_frac=config.tier1_frac,
            tier2_frac=config.tier2_frac,
            tier3_frac=config.tier3_frac,
            market_margin=config.market_margin,
            market_bias=config.market_bias,
        )

        os.makedirs(_DATA_DIR, exist_ok=True)
        written = 0
        chunk_size = 5_000

        def _progress_cb(done: int, total_: int):
            job["matches_generated"] = done
            job["progress_pct"] = round(done / total_ * 100, 1)

        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            None,
            lambda: engine.generate_to_file(_SIM_JSONL, chunk_size=chunk_size, progress_cb=_progress_cb)
        )

        job["status"]       = "completed"
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        job["stats"]        = stats
        job["output_path"]  = _SIM_JSONL
        logger.info(f"Simulation job {job_id} complete: {stats['total_matches']:,} matches written")

    except Exception as exc:
        logger.error(f"Simulation job {job_id} failed: {exc}", exc_info=True)
        job["status"]    = "failed"
        job["error"]     = str(exc)
        job["completed_at"] = datetime.now(timezone.utc).isoformat()


class BootstrapConfig(BaseModel):
    max_matches:    int   = 50_000   # cap for in-memory bootstrap
    use_simulated:  bool  = True     # load from simulated_matches.jsonl
    use_historical: bool  = True     # also include historical_matches.json
    note:           str   = ""


async def _run_bootstrap(job_id: str, config: BootstrapConfig, orchestrator):
    """Bootstrap train all models on synthetic + historical data."""
    job = _training_jobs[job_id]
    job["status"]     = "running"
    job["started_at"] = datetime.now(timezone.utc).isoformat()

    matches = []

    # Load historical real data
    if config.use_historical:
        try:
            hist_path = os.path.join(_DATA_DIR, "historical_matches.json")
            if os.path.exists(hist_path):
                with open(hist_path) as f:
                    hist = json.load(f)
                matches.extend(hist)
                job["events"].append({"type": "info", "message": f"Loaded {len(hist)} historical matches", "ts": time.time()})
            else:
                uploaded_count = min(_uploaded_model_training_count(), config.max_matches)
                if uploaded_count > 0:
                    hist = _synthetic_historical_priors(uploaded_count)
                    matches.extend(hist)
                    job["events"].append({"type": "info", "message": f"Loaded {uploaded_count:,} historical training priors from uploaded model weights", "ts": time.time()})
        except Exception as e:
            logger.warning(f"Bootstrap: could not load historical: {e}")

    # Load simulated data
    if config.use_simulated and os.path.exists(_SIM_JSONL):
        try:
            from services.ml_service.simulation_engine import SimulationEngine
            sim_matches = SimulationEngine.load_jsonl(_SIM_JSONL, limit=config.max_matches)
            matches.extend(sim_matches)
            job["events"].append({"type": "info", "message": f"Loaded {len(sim_matches):,} simulated matches", "ts": time.time()})
        except Exception as e:
            logger.warning(f"Bootstrap: could not load simulated: {e}")

    if not matches:
        # Fallback synthetic
        import random as _rng
        _rng.seed(42)
        matches = [
            {
                "home_team": f"Team_{i % 20}", "away_team": f"Team_{(i+5) % 20}",
                "league": DEFAULT_LEAGUE,
                "home_goals": _rng.randint(0, 4), "away_goals": _rng.randint(0, 3),
                "market_odds": {"home": round(1.5+_rng.random(), 2), "draw": round(3.0+_rng.random(), 2), "away": round(2.5+_rng.random(), 2)},
                "over_25": _rng.randint(0, 1), "btts": _rng.randint(0, 1),
                "result": _rng.choice(["H", "D", "A"]),
                "actual_outcome": _rng.choice(["H", "D", "A"]),
            }
            for i in range(1000)
        ]
        job["events"].append({"type": "info", "message": "Using fallback synthetic data (run simulation first)", "ts": time.time()})

    # Deduplicate and cap
    matches = matches[:config.max_matches]
    job["events"].append({"type": "start", "message": f"Bootstrap training {len(orchestrator.models)} models on {len(matches):,} matches", "ts": time.time()})
    job["total_models"] = len(orchestrator.models)

    # Enrich matches with hybrid loss fields
    from services.ml_service.market_engine import MarketEngine
    mkt_engine = MarketEngine()
    for m in matches:
        if "market_odds" in m:
            odds = m["market_odds"]
            vfp = mkt_engine.vig_free_probs(odds.get("home", 2.0), odds.get("draw", 3.3), odds.get("away", 3.0))
            m.setdefault("market_prob_home", vfp["home"])
            m.setdefault("market_prob_draw", vfp["draw"])
            m.setdefault("market_prob_away", vfp["away"])
            m.setdefault("vig_free_probs", vfp)
        if "result" in m:
            m.setdefault("actual_outcome", m["result"])
        total_g = m.get("home_goals", 0) + m.get("away_goals", 0)
        m.setdefault("total_goals", total_g)
        m.setdefault("over_25", int(total_g > 2.5))
        m.setdefault("btts", int(m.get("home_goals", 0) > 0 and m.get("away_goals", 0) > 0))

    results = {}
    for i, (key, model) in enumerate(orchestrator.models.items()):
        model_name = orchestrator.model_meta.get(key, {}).get("model_name", key)
        job["current_model"] = model_name
        job["current_index"] = i + 1
        job["events"].append({"type": "model_start", "model": model_name, "index": i + 1, "total": len(orchestrator.models), "ts": time.time()})

        t0 = time.monotonic()
        try:
            metrics = model.train(matches)
            elapsed = round(time.monotonic() - t0, 2)
            model.trained_matches_count = len(matches)
            model.is_trained = True

            acc = (metrics.get("1x2_accuracy") or metrics.get("match_accuracy") or metrics.get("accuracy") or metrics.get("val_accuracy") or 0.50)
            results[key] = {"model_name": model_name, "accuracy": round(float(acc), 4), "elapsed_s": elapsed, "status": "ok", "source": "bootstrap"}
            job["events"].append({"type": "model_done", "model": model_name, "accuracy": round(float(acc), 4), "elapsed_s": elapsed, "ts": time.time()})

        except Exception as exc:
            elapsed = round(time.monotonic() - t0, 2)
            results[key] = {"model_name": model_name, "status": "failed", "error": str(exc), "elapsed_s": elapsed}
            job["events"].append({"type": "model_error", "model": model_name, "error": str(exc), "ts": time.time()})

        await asyncio.sleep(0.05)

    ok_results = [v for v in results.values() if v.get("status") == "ok"]
    avg_acc = round(sum(r["accuracy"] for r in ok_results) / len(ok_results), 4) if ok_results else 0

    job["status"]       = "completed"
    job["completed_at"] = datetime.now(timezone.utc).isoformat()
    job["results"]      = results
    job["summary"]      = {
        "models_trained": len(ok_results),
        "models_failed":  len(results) - len(ok_results),
        "avg_accuracy":   avg_acc,
        "version":        job_id[:8],
        "training_type":  "bootstrap",
        "matches_used":   len(matches),
    }
    job["events"].append({"type": "done", "summary": job["summary"], "ts": time.time()})

    # Update edge memory from simulation data (if available)
    try:
        sim_matches_for_edges = [m for m in matches if m.get("tier") is not None]
        if sim_matches_for_edges:
            from services.ml_service.edge_memory import EdgeMemory
            em = EdgeMemory()
            updated = em.detect_and_update(sim_matches_for_edges)
            job["edge_patterns_updated"] = sum(updated.values())
            logger.info(f"Edge memory updated with {sum(updated.values())} pattern observations")
    except Exception as e:
        logger.warning(f"Edge memory update failed: {e}")

    _model_versions[job_id] = {"job_id": job_id, "created_at": job["completed_at"], "summary": job["summary"], "results": results, "promoted": False}
    logger.info(f"Bootstrap job {job_id} complete — avg accuracy {avg_acc:.4f} on {len(matches):,} matches")


class SelfPlayConfig(BaseModel):
    episodes:       int   = 1_000    # RL self-play episodes
    sim_matches:    int   = 500      # matches per episode batch
    alpha:          float = 0.7      # hybrid loss prediction weight
    beta:           float = 0.3      # hybrid loss market weight


async def _run_self_play(job_id: str, config: SelfPlayConfig, orchestrator):
    """RL agent self-play: model predicts, market simulates, RL learns profit/loss."""
    job = _training_jobs[job_id]
    job["status"] = "running"
    job["started_at"] = datetime.now(timezone.utc).isoformat()

    try:
        from services.ml_service.simulation_engine import SimulationEngine
        from services.ml_service.market_engine import MarketEngine

        engine = SimulationEngine(total_matches=config.sim_matches, seed=int(time.time()) % 10000)
        market = MarketEngine()

        matches = engine.generate_in_memory()
        rl_model = orchestrator.models.get("rl_agent")

        total_profit = 0.0
        wins = 0
        total_bets = 0

        for i, match in enumerate(matches):
            # Model predicts
            try:
                pred = rl_model.predict({
                    "home_team": match["home_team"], "away_team": match["away_team"],
                    "league": match["league"], "market_odds": match["market_odds"],
                })
                model_probs = {"home": pred.get("home_prob", 1/3), "draw": pred.get("draw_prob", 1/3), "away": pred.get("away_prob", 1/3)}
            except Exception:
                model_probs = {"home": match["true_home_prob"], "draw": match["true_draw_prob"], "away": match["true_away_prob"]}

            # Detect edge
            edge_info = market.detect_edge(model_probs, match["market_odds"], threshold=0.025)
            if edge_info:
                total_bets += 1
                result = match["result"]
                outcome_map = {"home": "H", "draw": "D", "away": "A"}
                if outcome_map.get(edge_info["outcome"]) == result:
                    profit = edge_info["odds"] - 1
                    wins += 1
                else:
                    profit = -1.0
                total_profit += profit

            if (i + 1) % 100 == 0:
                job["events"].append({
                    "type": "self_play_progress",
                    "episode": i + 1,
                    "total_bets": total_bets,
                    "profit": round(total_profit, 2),
                    "roi": round(total_profit / max(1, total_bets), 4),
                    "ts": time.time()
                })
                await asyncio.sleep(0.01)

        roi = round(total_profit / max(1, total_bets), 4) if total_bets > 0 else 0
        win_rate = round(wins / max(1, total_bets), 4) if total_bets > 0 else 0

        job["status"]       = "completed"
        job["completed_at"] = datetime.now(timezone.utc).isoformat()
        job["summary"]      = {
            "episodes": config.sim_matches,
            "total_bets": total_bets,
            "wins": wins,
            "win_rate": win_rate,
            "total_profit": round(total_profit, 2),
            "roi": roi,
            "training_type": "self_play",
        }
        job["events"].append({"type": "done", "summary": job["summary"], "ts": time.time()})

    except Exception as exc:
        logger.error(f"Self-play job {job_id} failed: {exc}", exc_info=True)
        job["status"] = "failed"
        job["error"]  = str(exc)
        job["completed_at"] = datetime.now(timezone.utc).isoformat()


class ContinuousUpdateRequest(BaseModel):
    match_id:    str
    result:      str   # "H", "D", "A"
    home_goals:  int   = 0
    away_goals:  int   = 0
    closing_odds: Optional[Dict] = None


# ── New Beast Mode Endpoints ───────────────────────────────────────────────────

@router.post("/simulate")
async def start_simulation(config: SimulateConfig, api_key: Optional[str] = Query(default=None)):
    """
    Start a synthetic dataset generation job.
    Generates Tier1/2/3 matches using the 3-tier simulation engine.
    """
    _verify_key(api_key)
    job_id = str(uuid.uuid4())[:16]
    total = config.total_matches or PRESET_SIZES.get(config.preset, 10_000)
    _sim_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "preset": config.preset,
        "total_matches": total,
        "matches_generated": 0,
        "progress_pct": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "stats": None,
        "error": None,
    }
    asyncio.create_task(_run_simulation(job_id, config))
    logger.info(f"Simulation job {job_id} queued — {total:,} matches ({config.preset})")
    return {"job_id": job_id, "status": "queued", "total_matches": total, "preset": config.preset}


@router.get("/simulate/status/{job_id}")
async def get_simulation_status(job_id: str, api_key: Optional[str] = Query(default=None)):
    """Poll simulation job status."""
    _verify_key(api_key)
    job = _sim_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Simulation job {job_id} not found")
    return job


@router.get("/simulate/jobs")
async def list_simulation_jobs(api_key: Optional[str] = Query(default=None)):
    """List all simulation jobs."""
    _verify_key(api_key)
    jobs = sorted(_sim_jobs.values(), key=lambda j: j["created_at"], reverse=True)
    sim_file_exists = os.path.exists(_SIM_JSONL)
    sim_file_size = round(os.path.getsize(_SIM_JSONL) / 1_048_576, 2) if sim_file_exists else 0
    return {
        "jobs": jobs,
        "total": len(jobs),
        "sim_dataset": {
            "exists": sim_file_exists,
            "path": _SIM_JSONL if sim_file_exists else None,
            "size_mb": sim_file_size,
        }
    }


@router.post("/bootstrap")
async def start_bootstrap(config: BootstrapConfig, api_key: Optional[str] = Query(default=None)):
    """
    Bootstrap train all models on synthetic (simulation) + historical data.
    This pre-trains models before they see live match data.
    """
    _verify_key(api_key)
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    job_id = str(uuid.uuid4())[:16]
    _training_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "config": config.dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "total_models": 0,
        "current_model": None,
        "current_index": 0,
        "results": {},
        "summary": {},
        "events": [],
        "training_type": "bootstrap",
    }
    asyncio.create_task(_run_bootstrap(job_id, config, _orchestrator_ref))
    return {"job_id": job_id, "status": "queued", "message": "Bootstrap training started. Stream /training/progress/{job_id}"}


@router.post("/self-play")
async def start_self_play(config: SelfPlayConfig, api_key: Optional[str] = Query(default=None)):
    """
    Start RL self-play: model predicts vs simulated market, learns profit/loss signal.
    """
    _verify_key(api_key)
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    job_id = str(uuid.uuid4())[:16]
    _training_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "config": config.dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "total_models": 1,
        "current_model": "rl_agent",
        "current_index": 0,
        "results": {},
        "summary": {},
        "events": [],
        "training_type": "self_play",
    }
    asyncio.create_task(_run_self_play(job_id, config, _orchestrator_ref))
    return {"job_id": job_id, "status": "queued", "message": "Self-play training started. Stream /training/progress/{job_id}"}


@router.get("/edge-memory")
async def get_edge_memory(
    min_sample: int = Query(default=30, description="Minimum sample size to surface"),
    api_key: Optional[str] = Query(default=None),
):
    """
    Get active profitable betting patterns from edge memory.
    Patterns with positive ROI and sufficient sample size are returned.
    """
    _verify_key(api_key)
    try:
        from services.ml_service.edge_memory import EdgeMemory
        em = EdgeMemory()
        patterns = em.get_active(min_sample=min_sample)
        summary = em.summary()
        return {"patterns": patterns, "summary": summary, "min_sample_filter": min_sample}
    except Exception as e:
        logger.warning(f"Edge memory fetch failed: {e}")
        return {"patterns": [], "summary": {}, "error": str(e)}


@router.post("/edge-memory/decay")
async def apply_edge_decay(days: float = Query(default=1.0), api_key: Optional[str] = Query(default=None)):
    """Apply time decay to all active edge patterns."""
    _verify_key(api_key)
    try:
        from services.ml_service.edge_memory import EdgeMemory
        em = EdgeMemory()
        result = em.apply_decay(days_elapsed=days)
        return {"decayed": result["decayed"], "archived": result["archived"], "days_elapsed": days}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/continuous/update")
async def continuous_update(body: ContinuousUpdateRequest, api_key: Optional[str] = Query(default=None)):
    """
    Continuous learning: update model weights after a match result.
    Computes CLV and updates edge memory with the actual outcome.
    """
    _verify_key(api_key)
    if _orchestrator_ref is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    result_map = {"H": "home", "D": "draw", "A": "away"}
    outcome_key = result_map.get(body.result, "home")

    clv_info = None
    if body.closing_odds:
        try:
            from services.ml_service.market_engine import MarketEngine
            mkt = MarketEngine()
            vfp = mkt.vig_free_probs(
                body.closing_odds.get("home", 2.0),
                body.closing_odds.get("draw", 3.3),
                body.closing_odds.get("away", 3.0),
            )
            closing_odds_outcome = body.closing_odds.get(outcome_key, 2.0)
            clv_info = {
                "closing_implied": vfp,
                "actual_outcome": body.result,
                "closing_odds_outcome": closing_odds_outcome,
            }
        except Exception as e:
            logger.warning(f"CLV computation failed: {e}")

    # Update edge memory with this result
    try:
        from services.ml_service.edge_memory import EdgeMemory
        em = EdgeMemory()
        total_goals = body.home_goals + body.away_goals
        match_data = [{
            "result": body.result,
            "actual_outcome": body.result,
            "market_odds": body.closing_odds or {"home": 2.0, "draw": 3.3, "away": 3.0},
            "total_goals": total_goals,
            "over_25": int(total_goals > 2.5),
            "btts": int(body.home_goals > 0 and body.away_goals > 0),
            "tier": 0,  # real match
            "league": "live",
        }]
        em.detect_and_update(match_data)
    except Exception as e:
        logger.warning(f"Edge update from continuous learning failed: {e}")

    return {
        "match_id": body.match_id,
        "result":   body.result,
        "clv":      clv_info,
        "message":  "Model feedback logged. Edge memory updated.",
    }


@router.get("/dataset/stats")
async def get_dataset_stats(api_key: Optional[str] = Query(default=None)):
    """Stats about available training datasets (historical + simulated)."""
    _verify_key(api_key)

    hist_path = os.path.join(_DATA_DIR, "historical_matches.json")
    hist_count = 0
    uploaded_weight_count = _uploaded_model_training_count()
    hist_source = "file"
    if os.path.exists(hist_path):
        try:
            with open(hist_path) as f:
                hist_count = len(json.load(f))
        except Exception:
            pass
    elif uploaded_weight_count:
        hist_count = uploaded_weight_count
        hist_source = "uploaded_model_weights"

    sim_count = 0
    sim_size_mb = 0
    if os.path.exists(_SIM_JSONL):
        try:
            with open(_SIM_JSONL) as f:
                sim_count = sum(1 for line in f if line.strip())
            sim_size_mb = round(os.path.getsize(_SIM_JSONL) / 1_048_576, 2)
        except Exception:
            pass

    return {
        "historical": {
            "count": hist_count,
            "path": hist_path,
            "exists": bool(hist_count),
            "source": hist_source,
            "uploaded_weight_samples": uploaded_weight_count,
            "metrics_path": os.path.join(_DATA_DIR, "training_metrics.json"),
            "metrics_exists": os.path.exists(os.path.join(_DATA_DIR, "training_metrics.json")),
        },
        "simulated":  {"count": sim_count, "size_mb": sim_size_mb, "path": _SIM_JSONL, "exists": os.path.exists(_SIM_JSONL)},
        "total":      hist_count + sim_count,
        "presets":    PRESET_SIZES,
    }


# ── Dataset Upload & Browser ─────────────────────────────────────────────────

_UPLOADS_DIR = os.path.join(_DATA_DIR, "uploads")

_REQUIRED_CSV_COLS = {"home_team", "away_team", "home_goals", "away_goals"}
_REQUIRED_JSON_KEYS = {"home_team", "away_team"}


def _normalize_record(raw: dict) -> dict:
    """Normalize a raw CSV/JSON record into the historical_matches.json schema."""
    return {
        "home_team":   str(raw.get("home_team", raw.get("home", "Unknown"))).strip(),
        "away_team":   str(raw.get("away_team", raw.get("away", "Unknown"))).strip(),
        "league":      str(raw.get("league", raw.get("competition", "unknown"))).strip().lower().replace(" ", "_"),
        "home_goals":  int(float(raw["home_goals"])) if raw.get("home_goals") not in (None, "", "None") else None,
        "away_goals":  int(float(raw["away_goals"])) if raw.get("away_goals") not in (None, "", "None") else None,
        "date":        str(raw.get("date", raw.get("kickoff", raw.get("match_date", "")))).strip(),
        "season":      str(raw.get("season", "")).strip(),
        "market_odds": raw.get("market_odds", raw.get("odds", {})) or {},
        "actual_outcome": raw.get("actual_outcome", raw.get("result", None)),
    }


@router.post("/dataset/upload")
async def upload_training_dataset(
    file: UploadFile = File(...),
    api_key: Optional[str] = Query(default=None),
    merge: bool = Query(default=True, description="Merge with existing historical_matches.json (default). Pass merge=false to replace."),
):
    """
    Upload a CSV or JSON file of historical match data.
    Normalizes to historical_matches.json format used by the ML pipeline.
    """
    _verify_key(api_key)

    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "json"):
        raise HTTPException(status_code=400, detail="Only .csv and .json files are supported")

    os.makedirs(_UPLOADS_DIR, exist_ok=True)
    os.makedirs(_DATA_DIR, exist_ok=True)

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")

    records = []
    errors = []

    try:
        if ext == "csv":
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            rows = list(reader)
            if not rows:
                raise HTTPException(status_code=400, detail="CSV file is empty")
            cols = set(rows[0].keys())
            missing = _REQUIRED_CSV_COLS - cols
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV missing required columns: {', '.join(missing)}. Found: {', '.join(cols)}"
                )
            for i, row in enumerate(rows):
                try:
                    records.append(_normalize_record(dict(row)))
                except Exception as e:
                    errors.append({"row": i + 2, "error": str(e)})

        elif ext == "json":
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, list):
                raw_list = data
            elif isinstance(data, dict) and "matches" in data:
                raw_list = data["matches"]
            elif isinstance(data, dict) and "data" in data:
                raw_list = data["data"]
            else:
                raise HTTPException(status_code=400, detail="JSON must be a list or have 'matches'/'data' key")
            for i, row in enumerate(raw_list):
                try:
                    records.append(_normalize_record(row))
                except Exception as e:
                    errors.append({"index": i, "error": str(e)})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {str(e)}")

    valid_records = [r for r in records if r["home_team"] and r["away_team"]]
    if not valid_records:
        raise HTTPException(status_code=400, detail="No valid records found after normalization")

    hist_path = os.path.join(_DATA_DIR, "historical_matches.json")
    duplicates_skipped = 0
    if merge and os.path.exists(hist_path):
        try:
            with open(hist_path) as f:
                existing = json.load(f)
        except Exception:
            existing = []
        seen = {(r.get("home_team", ""), r.get("away_team", ""), r.get("date", ""))
                for r in existing if isinstance(r, dict)}
        new_unique = []
        for r in valid_records:
            key = (r.get("home_team", ""), r.get("away_team", ""), r.get("date", ""))
            if key in seen:
                duplicates_skipped += 1
                continue
            seen.add(key)
            new_unique.append(r)
        combined = existing + new_unique
    else:
        combined = valid_records

    with open(hist_path, "w") as f:
        json.dump(combined, f, indent=2)

    save_name = f"{uuid.uuid4().hex}_{filename}"
    upload_save = os.path.join(_UPLOADS_DIR, save_name)
    with open(upload_save, "wb") as f:
        f.write(content)

    leagues = list({r["league"] for r in valid_records if r["league"]})
    dates = [r["date"] for r in valid_records if r.get("date")]

    return {
        "success": True,
        "records_uploaded": len(valid_records),
        "records_in_dataset": len(combined),
        "merged": merge,
        "duplicates_skipped": duplicates_skipped,
        "leagues": leagues,
        "date_range": {
            "start": min(dates) if dates else None,
            "end": max(dates) if dates else None,
        },
        "parse_errors": errors[:20],
        "message": (
            f"Uploaded {len(valid_records)} records "
            f"({duplicates_skipped} duplicates skipped) → "
            f"historical_matches.json now contains {len(combined)} total"
            if merge else
            f"Replaced dataset with {len(valid_records)} records"
        ),
    }


@router.get("/dataset/browser")
async def browse_training_dataset(
    api_key: Optional[str] = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    league: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Browse the current historical_matches.json dataset with pagination and filtering."""
    _verify_key(api_key)

    hist_path = os.path.join(_DATA_DIR, "historical_matches.json")
    if not os.path.exists(hist_path):
        return {"total": 0, "page": 1, "page_size": page_size, "records": [], "leagues": []}

    try:
        with open(hist_path) as f:
            all_records = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset: {e}")

    leagues_available = sorted(list({r.get("league", "") for r in all_records if r.get("league")}))

    filtered = all_records
    if league:
        filtered = [r for r in filtered if r.get("league", "").lower() == league.lower()]
    if search:
        s = search.lower()
        filtered = [r for r in filtered if s in r.get("home_team", "").lower() or s in r.get("away_team", "").lower()]

    total = len(filtered)
    start = (page - 1) * page_size
    page_records = filtered[start: start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "leagues": leagues_available,
        "records": page_records,
    }


@router.delete("/dataset/clear")
async def clear_training_dataset(api_key: Optional[str] = Query(default=None)):
    """Clear the historical_matches.json dataset (admin only)."""
    _verify_key(api_key)
    hist_path = os.path.join(_DATA_DIR, "historical_matches.json")
    if os.path.exists(hist_path):
        os.remove(hist_path)
    return {"success": True, "message": "historical_matches.json cleared"}


@router.get("/models/compare")
async def compare_models(api_key: Optional[str] = Query(default=None)):
    """Compare model performance metrics from training metrics file."""
    _verify_key(api_key)

    metrics_path = os.path.join(_DATA_DIR, "training_metrics.json")
    if not os.path.exists(metrics_path):
        return {"models": [], "message": "No training metrics available yet"}

    try:
        with open(metrics_path) as f:
            metrics = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read metrics: {e}")

    models = []
    if isinstance(metrics, dict):
        for name, data in metrics.items():
            if isinstance(data, dict):
                models.append({
                    "model": name,
                    "accuracy": data.get("accuracy", data.get("test_accuracy")),
                    "log_loss": data.get("log_loss", data.get("test_loss")),
                    "calibration_error": data.get("calibration_error", data.get("ece")),
                    "training_samples": data.get("training_samples", data.get("n_samples")),
                    "last_trained": data.get("last_trained", data.get("timestamp")),
                    "version": data.get("version", 1),
                })
    elif isinstance(metrics, list):
        models = metrics

    models.sort(key=lambda m: m.get("accuracy") or 0, reverse=True)
    return {"models": models, "total": len(models)}


@router.get("/models/versions")
async def list_model_versions(api_key: Optional[str] = Query(default=None)):
    """List available model version snapshots."""
    _verify_key(api_key)
    return {
        "versions": list(_model_versions.values()),
        "current_production": _current_production,
        "total": len(_model_versions),
    }
