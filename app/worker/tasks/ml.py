"""app/worker/tasks/ml.py — ML model maintenance Celery tasks.

Tasks:
  ml.evict_stale_models    — evict LRU models when RSS exceeds budget
  ml.retrain_from_settled  — daily retrain on settled match outcomes
  ml.evaluate_models       — compute accuracy metrics and push to Redis
"""
from __future__ import annotations

import asyncio, gc, json, logging, os, time
from typing import Any, Dict, List

from celery.utils.log import get_task_logger
from app.worker.celery_app import celery

logger = get_task_logger(__name__)


def _redis():
    import redis as _r
    return _r.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                       socket_connect_timeout=3)


@celery.task(name="ml.evict_stale_models", max_retries=2, default_retry_delay=60)
def evict_stale_models():
    """Evict unused models from memory when RSS exceeds MAX_PROCESS_RAM_MB."""
    try:
        import psutil
        proc  = psutil.Process(os.getpid())
        rss   = proc.memory_info().rss / 1_048_576
        budget = int(os.environ.get("MAX_PROCESS_RAM_MB", "400"))
        logger.info("[ml.evict] RSS=%.1fMB budget=%dMB", rss, budget)

        if rss < budget * 0.85:
            return {"action": "noop", "rss_mb": round(rss, 1)}

        gc_collected = gc.collect()
        evicted: List[str] = []
        try:
            from app.core.model_registry import ModelRegistry
            evicted = ModelRegistry.get().evict_lru(max_models=2)
        except Exception as exc:
            logger.warning("[ml.evict] registry evict failed: %s", exc)

        gc.collect()
        rss_after = psutil.Process(os.getpid()).memory_info().rss / 1_048_576
        return {
            "action": "evicted", "models_evicted": evicted,
            "rss_before_mb": round(rss, 1), "rss_after_mb": round(rss_after, 1),
            "gc_collected": gc_collected,
        }
    except Exception as exc:
        logger.error("[ml.evict] %s", exc, exc_info=True); raise


@celery.task(name="ml.retrain_from_settled", max_retries=1, default_retry_delay=300,
             soft_time_limit=1800, time_limit=2100)
def retrain_from_settled():
    """Retrain sklearn layers using settled match outcomes (last 90 days)."""
    run_id = f"retrain_{int(time.time())}"
    logger.info("[ml.retrain] run=%s start", run_id)
    _pub_status(run_id, "running")

    result: Dict[str, Any] = {
        "run_id": run_id, "models_retrained": [],
        "matches_used": 0, "errors": [], "status": "ok",
    }
    try:
        matches = asyncio.run(_fetch_settled_matches())
        result["matches_used"] = len(matches)

        if len(matches) < 10:
            result["status"] = "skipped"
            result["reason"] = f"only {len(matches)} settled rows (need ≥10)"
            return result

        X, y = _build_matrix(matches)

        try:
            from app.core.model_registry import ModelRegistry
            reg = ModelRegistry.get()
            for key in list(reg.keys()):
                try:
                    obj = reg.load(key)
                    sk  = getattr(obj, "_sklearn_model",  None)
                    scl = getattr(obj, "_sklearn_scaler", None)
                    if sk is None: continue
                    Xs = scl.transform(X) if scl is not None else X
                    sk.fit(Xs, y)
                    result["models_retrained"].append(key)
                except Exception as exc:
                    result["errors"].append({"model": key, "error": str(exc)})
        except ImportError:
            logger.warning("[ml.retrain] ModelRegistry not available")

        result["completed_at"] = time.time()
        _pub_status(run_id, "ok", result)

    except Exception as exc:
        result.update({"status": "error", "error": str(exc)})
        logger.error("[ml.retrain] run=%s %s", run_id, exc, exc_info=True)

    return result


async def _fetch_settled_matches() -> List[Dict]:
    from datetime import datetime, timezone, timedelta
    from app.db.database import AsyncSessionLocal
    from app.db.models import Match, Prediction
    from sqlalchemy import select, and_

    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).replace(tzinfo=None)
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Match.actual_outcome, Match.home_goals, Match.away_goals,
                   Prediction.home_prob, Prediction.draw_prob, Prediction.away_prob,
                   Prediction.over_25_prob, Prediction.btts_prob)
            .join(Prediction, Prediction.match_id == Match.id)
            .where(and_(Match.actual_outcome.isnot(None),
                        Match.kickoff_time >= cutoff))
            .limit(5000)
        )).all()

    return [
        {"actual_outcome": r[0], "home_goals": r[1] or 0, "away_goals": r[2] or 0,
         "home_prob": float(r[3] or 0), "draw_prob": float(r[4] or 0),
         "away_prob": float(r[5] or 0), "over_25_prob": float(r[6] or 0.5),
         "btts_prob": float(r[7] or 0.5)}
        for r in rows if r[0]
    ]


def _build_matrix(matches: List[Dict]):
    import numpy as np
    outcome_map = {"home": 0, "draw": 1, "away": 2}
    X, y = [], []
    for m in matches:
        hp, dp, ap = m["home_prob"], m["draw_prob"], m["away_prob"]
        X.append([hp, dp, ap, m["over_25_prob"], m["btts_prob"],
                  hp - ap, hp / max(0.01, ap),
                  hp + dp + ap, 1 / max(0.01, hp), 1 / max(0.01, ap)])
        y.append(outcome_map.get(m["actual_outcome"], 1))
    return np.array(X, dtype=float), np.array(y, dtype=int)


@celery.task(name="ml.evaluate_models", max_retries=1, default_retry_delay=120)
def evaluate_models():
    """Compute accuracy on settled matches; push metrics to Redis."""
    try:
        matches = asyncio.run(_fetch_settled_matches())
        if not matches:
            return {"status": "no_data"}
        total   = len(matches)
        correct = sum(1 for m in matches
                      if max(("home",m["home_prob"]),("draw",m["draw_prob"]),
                             ("away",m["away_prob"]),key=lambda x:x[1])[0]
                         == m["actual_outcome"])
        acc = round(correct / total, 4)
        result = {"accuracy": acc, "correct": correct,
                  "total": total, "evaluated_at": time.time()}
        try:
            r = _redis()
            r.setex("ml:accuracy:overall", 86400, json.dumps(result))
            r.close()
        except Exception: pass
        logger.info("[ml.eval] acc=%.2f%% n=%d", acc * 100, total)
        return result
    except Exception as exc:
        logger.error("[ml.eval] %s", exc, exc_info=True); raise


def _pub_status(run_id: str, status: str, detail: dict = None) -> None:
    try:
        r = _redis()
        r.setex("ml:retrain:status", 3600, json.dumps(
            {"run_id": run_id, "status": status, "ts": time.time(), **(detail or {})}))
        r.close()
    except Exception: pass
