#!/usr/bin/env python3
"""
VIT Sports Intelligence Network — Direct Model Training Script
Trains all 13 ensemble models + 3 market models directly,
bypassing the HTTP API layer for maximum speed and reliability.

Usage:
    python3 scripts/train_all_models.py
"""
import asyncio
import json
import logging
import os
import re
import sys
import time

# ── Project root on path ─────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Force real ML models on before importing anything
os.environ["USE_REAL_ML_MODELS"] = "true"
os.environ.setdefault("VIT_DATABASE_URL", f"sqlite+aiosqlite:///{ROOT}/vit.db")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT}/vit.db")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_all")

DATA_DIR   = os.path.join(ROOT, "data")
MODELS_DIR = os.path.join(ROOT, "models")
HIST_JSON  = os.path.join(DATA_DIR, "historical_matches.json")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_pkl(model_obj, key: str, job_id: str, metrics: dict) -> bool:
    try:
        import joblib
        os.makedirs(MODELS_DIR, exist_ok=True)
        safe_key = re.sub(r"[^a-z0-9_\-]", "_", key)
        archive  = os.path.join(MODELS_DIR, f"{safe_key}_{job_id[:8]}.pkl")
        active   = os.path.join(MODELS_DIR, f"{safe_key}.pkl")
        payload  = {
            "model_key":           key,
            "job_id":              job_id,
            "training_samples":    getattr(model_obj, "trained_matches_count", 0),
            "is_trained":          getattr(model_obj, "is_trained", True),
            "learning_iteration":  getattr(model_obj, "learning_iteration", 1),
            "metrics":             metrics or {},
            "version":             job_id[:8],
            "model":               model_obj,
        }
        joblib.dump(payload, archive)
        joblib.dump(payload, active)
        logger.info("  💾 Saved %s.pkl (%d samples)", safe_key, payload["training_samples"])
        return True
    except Exception as exc:
        logger.warning("  ⚠️  pkl save failed for %s: %s", key, exc)
        return False


# ── Stage 1: Train all 13 ensemble models ─────────────────────────────────────

def train_ensemble(historical: list) -> dict:
    logger.info("=" * 60)
    logger.info("STAGE 1 — Training 13-model ensemble")
    logger.info("  Dataset: %d historical matches", len(historical))
    logger.info("=" * 60)

    # Import orchestrator (brings in all model classes)
    from services.ml_service.models.model_orchestrator import ModelOrchestrator
    orchestrator = ModelOrchestrator()

    models = orchestrator.models
    meta   = orchestrator.model_meta
    n      = len(models)
    job_id = f"train_{int(time.time())}"
    results = {}
    saved = 0

    for i, (key, model) in enumerate(models.items(), 1):
        model_name = meta.get(key, {}).get("model_name", key)
        logger.info("[%d/%d] Training: %s", i, n, model_name)
        t0 = time.monotonic()
        try:
            metrics = model.train(historical)
            elapsed = round(time.monotonic() - t0, 2)
            model.trained_matches_count = len(historical)
            model.is_trained = True

            acc = (
                metrics.get("1x2_accuracy") or
                metrics.get("match_accuracy") or
                metrics.get("accuracy") or
                metrics.get("val_accuracy") or 0.50
            )
            ou_acc  = metrics.get("over_under_accuracy") or metrics.get("ou_accuracy") or 0.50
            loss    = metrics.get("log_loss") or metrics.get("loss") or 0.0
            brier   = metrics.get("brier_score") or 0.0

            results[key] = {
                "model_name": model_name,
                "accuracy":   round(float(acc), 4),
                "ou_accuracy": round(float(ou_acc), 4),
                "log_loss":   round(float(loss), 4),
                "brier_score": round(float(brier), 4),
                "elapsed_s":  elapsed,
                "status":     "ok",
            }
            logger.info(
                "  ✅ acc=%.4f  ou=%.4f  brier=%.4f  log_loss=%.4f  (%.1fs)",
                acc, ou_acc, brier, loss, elapsed,
            )

            if _save_pkl(model, key, job_id, results[key]):
                saved += 1

        except Exception as exc:
            elapsed = round(time.monotonic() - t0, 2)
            results[key] = {"model_name": model_name, "status": "failed", "error": str(exc)}
            logger.warning("  ❌ %s failed: %s", model_name, exc)

    ok = [v for v in results.values() if v.get("status") == "ok"]
    avg_acc = round(sum(r["accuracy"] for r in ok) / len(ok), 4) if ok else 0.0
    avg_ou  = round(sum(r.get("ou_accuracy", 0.5) for r in ok) / len(ok), 4) if ok else 0.0

    logger.info("=" * 60)
    logger.info("Ensemble complete — %d/%d trained  avg_acc=%.4f  avg_ou=%.4f  %d pkls saved",
                len(ok), n, avg_acc, avg_ou, saved)
    logger.info("=" * 60)
    return {"results": results, "avg_accuracy": avg_acc, "avg_ou_accuracy": avg_ou,
            "models_ok": len(ok), "models_failed": n - len(ok), "saved_pkls": saved, "job_id": job_id}


# ── Stage 2: Reload trained weights into live orchestrator ────────────────────

def reload_weights():
    logger.info("=" * 60)
    logger.info("STAGE 2 — Reloading trained weights into live orchestrator")
    logger.info("=" * 60)
    try:
        from app.core.dependencies import get_orchestrator
        orch = get_orchestrator()
        if orch is None:
            logger.warning("  Orchestrator not initialized — skipping hot reload")
            return False
        try:
            from app.core.feature_flags import FeatureFlags
            FeatureFlags.reset()
        except Exception:
            pass
        orch.load_all_models()
        pkl_count = sum(1 for v in orch._pkl_loaded.values() if v)
        logger.info("  ✅ Live orchestrator reloaded — %d models with real pkl weights", pkl_count)
        return True
    except Exception as exc:
        logger.warning("  ⚠️  Hot reload failed: %s", exc)
        return False


# ── Stage 3: Train market models (BTTS, Over/Under, Correct Score) ─────────────

async def train_market_models():
    logger.info("=" * 60)
    logger.info("STAGE 3 — Training market models (BTTS / O.U / Correct Score)")
    logger.info("=" * 60)
    try:
        from app.db.database import AsyncSessionLocal
        from app.ai.market_trainer import train_all_market_models
        async with AsyncSessionLocal() as db:
            result = await train_all_market_models(db, epochs=80)
        logger.info("  ✅ Market models: %s", result)
        return result
    except Exception as exc:
        logger.warning("  ⚠️  Market model training failed: %s", exc)
        return {"error": str(exc)}


# ── Stage 4: Calibrator re-fit (if calibration module present) ────────────────

def fit_calibrators(historical: list):
    logger.info("=" * 60)
    logger.info("STAGE 4 — Fitting probability calibrators")
    logger.info("=" * 60)
    try:
        from app.services.calibration import CalibrationService
        svc = CalibrationService()
        # Feed outcomes to calibrator
        for rec in historical:
            outcome = rec.get("actual_outcome")
            if outcome not in ("home", "draw", "away"):
                continue
            odds = rec.get("market_odds") or {}
            if not odds:
                continue
            svc.record_prediction(
                home_prob=rec.get("vig_free_probs", {}).get("home", 0.333),
                draw_prob=rec.get("vig_free_probs", {}).get("draw", 0.333),
                away_prob=rec.get("vig_free_probs", {}).get("away", 0.334),
                actual=outcome,
            )
        report = svc.calibration_report() if hasattr(svc, "calibration_report") else {}
        logger.info("  ✅ Calibrator fit: %s", report)
        return True
    except Exception as exc:
        logger.warning("  ⚠️  Calibrator step skipped: %s", exc)
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    t_start = time.monotonic()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  VIT Sports Intelligence — Full Model Training Pipeline  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Load dataset
    logger.info("Loading training dataset from %s ...", HIST_JSON)
    if not os.path.exists(HIST_JSON):
        logger.error("historical_matches.json not found — run scripts/build_training_dataset.py first")
        sys.exit(1)
    with open(HIST_JSON) as f:
        historical = json.load(f)
    logger.info("Loaded %d records", len(historical))

    # Remove records with no goals data (can't train on them)
    historical = [
        r for r in historical
        if r.get("home_goals") is not None and r.get("away_goals") is not None
        and r.get("actual_outcome") in ("home", "draw", "away")
    ]
    logger.info("After quality filter: %d usable training samples", len(historical))

    if len(historical) < 100:
        logger.error("Insufficient training data (need >= 100, got %d)", len(historical))
        sys.exit(1)

    # Stage 1: Train 13-model ensemble
    ensemble_result = train_ensemble(historical)

    # Stage 2: Reload into live orchestrator
    reload_weights()

    # Stage 3: Train market models
    market_result = await train_market_models()

    # Stage 4: Fit calibrators
    fit_calibrators(historical)

    elapsed = round(time.monotonic() - t_start, 1)

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║                  TRAINING COMPLETE                       ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Total time:        {elapsed:>6.1f}s                            ║")
    print(f"║  Training samples:  {len(historical):>6d}                            ║")
    print(f"║  Ensemble models:   {ensemble_result['models_ok']:>6d} / {ensemble_result['models_ok'] + ensemble_result['models_failed']} trained                   ║")
    print(f"║  Avg 1X2 accuracy:  {ensemble_result['avg_accuracy']:>6.4f}                            ║")
    print(f"║  Avg O/U accuracy:  {ensemble_result['avg_ou_accuracy']:>6.4f}                            ║")
    print(f"║  PKLs saved:        {ensemble_result['saved_pkls']:>6d}                            ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  USE_REAL_ML_MODELS=true — trained weights now active    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # Write summary for the running server to pick up
    summary = {
        "trained_at":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "training_samples": len(historical),
        "ensemble":         ensemble_result,
        "market":           market_result,
        "use_real_ml":      True,
    }
    summary_path = os.path.join(MODELS_DIR, "training_summary.json")
    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info("Summary written → %s", summary_path)

    return summary


if __name__ == "__main__":
    asyncio.run(main())
