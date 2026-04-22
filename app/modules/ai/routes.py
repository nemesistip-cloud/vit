# app/modules/ai/routes.py
"""
Module E — API Routes

GET  /api/ai-engine/models               — list all registered models
GET  /api/ai-engine/models/{key}         — single model detail
PATCH /api/ai-engine/models/{key}/weight — manually set weight (admin)
POST /api/ai-engine/models/{key}/toggle  — activate / deactivate model (admin)
POST /api/ai-engine/upload/{key}         — upload a .pkl file for a model
GET  /api/ai-engine/audit                — recent audit log entries
GET  /api/ai-engine/audit/{match_id}     — audit entries for a specific match
GET  /api/ai-engine/performance          — model performance leaderboard
POST /api/ai-engine/weights/adjust       — trigger bulk weight adjustment (admin)
POST /api/ai-engine/weights/sync         — push DB weights → orchestrator (admin)
GET  /api/ai-engine/status               — registry + orchestrator health
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.dependencies import get_orchestrator
from app.modules.ai.models import AIPredictionAudit, ModelMetadata
from app.modules.ai.registry import (
    bootstrap_registry,
    get_registry,
    get_model_by_key,
    sync_weights_to_orchestrator,
    _row_to_dict,
)
from app.modules.ai.weight_adjuster import (
    run_bulk_weight_adjustment,
    get_model_performance_report,
)
from app.api.deps import get_current_admin
from app.db.models import User
from app.services.accuracy_enhancer import (
    fit_temperature_from_history,
    rolling_window_accuracy,
    TemperatureScaler,
    TEMPERATURE_PATH,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai-engine", tags=["ai-engine"])

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "models",
)
os.makedirs(MODELS_DIR, exist_ok=True)


# ── Schemas ───────────────────────────────────────────────────────────────────

class WeightUpdateRequest(BaseModel):
    weight: float = Field(..., ge=0.0, le=5.0, description="New ensemble weight (0.0 – 5.0)")


class BulkAdjustRequest(BaseModel):
    days_back: int = Field(7, ge=1, le=365)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/status")
async def ai_engine_status(db: AsyncSession = Depends(get_db)):
    """Registry + orchestrator health overview."""
    orch = get_orchestrator()
    registry = await get_registry(db)
    pkl_count = sum(1 for m in registry if m["pkl_loaded"])
    active_count = sum(1 for m in registry if m["is_active"])

    return {
        "status": "operational",
        "orchestrator_models_loaded": orch.num_models_ready() if orch else 0,
        "registry_total":   len(registry),
        "registry_active":  active_count,
        "pkl_loaded_count": pkl_count,
        "models_dir":       MODELS_DIR,
    }


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    """Return all registered models with weights, accuracy, and pkl status."""
    orch = get_orchestrator()
    if orch:
        await bootstrap_registry(db, orch)
    return {"models": await get_registry(db)}


@router.get("/models/{key}")
async def get_model(key: str, db: AsyncSession = Depends(get_db)):
    """Get a single model's full detail."""
    row = await get_model_by_key(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not found in registry")
    return _row_to_dict(row)


@router.patch("/models/{key}/weight")
async def set_model_weight(
    key: str,
    body: WeightUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Manually override a model's ensemble weight."""
    row = await get_model_by_key(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not found")

    old = row.weight
    row.weight = body.weight
    await db.commit()

    # Sync to live orchestrator immediately
    orch = get_orchestrator()
    if orch and key in orch.model_meta:
        orch.model_meta[key]["weight"] = body.weight

    return {
        "key":        key,
        "old_weight": old,
        "new_weight": body.weight,
        "synced_to_orchestrator": orch is not None,
    }


@router.post("/models/{key}/toggle")
async def toggle_model(key: str, db: AsyncSession = Depends(get_db)):
    """Activate or deactivate a model in the ensemble."""
    row = await get_model_by_key(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not found")

    row.is_active = not row.is_active
    await db.commit()
    return {"key": key, "is_active": row.is_active}


@router.post("/upload/{key}")
async def upload_pkl(
    key: str,
    file: UploadFile = File(...),
    auto_promote: bool = Query(False, description="If true, immediately promote this version to active. Default false — uploads are staged."),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a Colab-trained .pkl file for a specific model key.

    Versioning behaviour (Apr 2026):
    - Each upload is saved with a version-suffixed filename
      (e.g. `xgb_v1__v1.2.pkl`); the previously promoted file is NEVER
      overwritten.
    - The upload is appended to `model_metadata.version_history` as a
      staged version.
    - The active production model only changes when `auto_promote=true`
      is passed OR the operator calls `POST /models/{key}/promote/{version}`.

    Expected pkl format (joblib-serialised dict):
    {
        "model":            <sklearn estimator with predict_proba()>,
        "scaler":           <StandardScaler or None>,
        "feature_columns":  ["col1", "col2", ...],
        "version":          "v1.0",
        "training_samples": 5000,
        "metrics":          {"accuracy": 0.62, "brier_score": 0.21, ...}
    }
    """
    from datetime import datetime, timezone
    import re

    if not file.filename.endswith(".pkl"):
        raise HTTPException(status_code=400, detail="Only .pkl files are accepted")

    row = await get_model_by_key(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not in registry")

    # Stage the upload to a temp path first so we can validate before naming it
    staged_path = os.path.join(MODELS_DIR, f"_staging_{key}_{int(datetime.now(timezone.utc).timestamp())}.pkl")
    content = await file.read()
    with open(staged_path, "wb") as f:
        f.write(content)

    try:
        import joblib
        payload = joblib.load(staged_path)
        if not isinstance(payload, dict) or "model" not in payload:
            os.remove(staged_path)
            raise HTTPException(
                status_code=422,
                detail="pkl must be a dict with at least a 'model' key"
            )
        metrics = payload.get("metrics", {})
        samples = payload.get("training_samples", 0)
        version = str(payload.get("version", "?")).strip() or "?"
    except HTTPException:
        raise
    except Exception as exc:
        if os.path.exists(staged_path):
            os.remove(staged_path)
        raise HTTPException(status_code=422, detail=f"Failed to load pkl: {exc}")

    # Sanitise version for filename use
    safe_version = re.sub(r"[^a-zA-Z0-9._-]+", "_", version) or "unknown"
    dest_path = os.path.join(MODELS_DIR, f"{key}__{safe_version}.pkl")

    # Refuse to overwrite an existing version file — operator must bump the version
    if os.path.exists(dest_path):
        os.remove(staged_path)
        raise HTTPException(
            status_code=409,
            detail=f"Version '{version}' already exists for model '{key}'. "
                   f"Bump the version in the pkl payload before re-uploading."
        )
    os.replace(staged_path, dest_path)

    # Append to version_history (never replace existing entries)
    history = list(row.version_history or [])
    entry = {
        "version":          version,
        "pkl_path":         dest_path,
        "training_samples": samples,
        "metrics":          metrics,
        "uploaded_at":      datetime.now(timezone.utc).isoformat(),
        "promoted_at":      None,
        "filename":         file.filename,
        "size_bytes":       len(content),
    }
    history.append(entry)
    row.version_history = history

    promoted = False
    if auto_promote:
        promoted = await _promote_version_inplace(row, version, history)
    await db.commit()

    # Hot-reload only if we promoted
    reloaded = False
    if promoted:
        orch = get_orchestrator()
        if orch:
            try:
                orch.load_all_models()
                reloaded = True
                if key in orch.model_meta:
                    orch.model_meta[key]["weight"] = row.weight
            except Exception as exc:
                logger.warning(f"Orchestrator reload failed after promote: {exc}")

    return {
        "key":              key,
        "filename":         file.filename,
        "size_bytes":       len(content),
        "training_samples": samples,
        "version":          version,
        "metrics":          metrics,
        "promoted":         promoted,
        "active_version":   row.active_version,
        "version_count":    len(history),
        "orchestrator_reloaded": reloaded,
        "message":          ("Staged. Call POST /models/{key}/promote/{version} to activate."
                             if not promoted
                             else f"Version {version} promoted to active."),
    }


async def _promote_version_inplace(row, version: str, history: list) -> bool:
    """
    Mark the named version as active on the row + history. Returns True on success.
    Caller is responsible for db.commit().
    """
    from datetime import datetime, timezone
    target = next((h for h in history if h.get("version") == version), None)
    if target is None:
        return False
    target["promoted_at"] = datetime.now(timezone.utc).isoformat()
    row.active_version   = version
    row.version          = version
    row.pkl_loaded       = True
    row.pkl_path         = target.get("pkl_path")
    row.training_samples = target.get("training_samples", 0)
    metrics = target.get("metrics") or {}
    if metrics.get("accuracy") is not None:
        row.accuracy     = metrics["accuracy"]
        row.accuracy_1x2 = metrics.get("accuracy", row.accuracy_1x2)
    if metrics.get("brier_score") is not None:
        row.brier_score  = metrics["brier_score"]
    if metrics.get("log_loss") is not None:
        row.log_loss     = metrics["log_loss"]
    if (row.weight or 0) < 2.0:
        row.weight = 2.0
    # Reassign to trigger ORM mutation tracking on JSON column
    row.version_history = list(history)
    return True


@router.get("/models/{key}/versions")
async def list_versions(key: str, db: AsyncSession = Depends(get_db)):
    """List all uploaded versions for a model key, with the active one flagged."""
    row = await get_model_by_key(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not in registry")
    history = list(row.version_history or [])
    return {
        "key":            key,
        "active_version": row.active_version,
        "version_count":  len(history),
        "versions":       history,
    }


@router.post("/models/{key}/promote/{version}")
async def promote_version(
    key: str,
    version: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Promote a previously-uploaded version to active production.

    The previous active version is preserved on disk and in version_history;
    promotion never deletes or overwrites historical artifacts.
    """
    row = await get_model_by_key(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not in registry")

    history = list(row.version_history or [])
    if not history:
        raise HTTPException(status_code=404, detail=f"No uploaded versions for '{key}'")

    target = next((h for h in history if h.get("version") == version), None)
    if target is None:
        available = [h.get("version") for h in history]
        raise HTTPException(
            status_code=404,
            detail=f"Version '{version}' not found for '{key}'. Available: {available}"
        )

    pkl_path = target.get("pkl_path")
    if not pkl_path or not os.path.exists(pkl_path):
        raise HTTPException(
            status_code=410,
            detail=f"Artifact for version '{version}' is missing on disk: {pkl_path}"
        )

    previous_version = row.active_version
    promoted = await _promote_version_inplace(row, version, history)
    if not promoted:
        raise HTTPException(status_code=500, detail="Promotion failed")
    await db.commit()

    # Hot-reload orchestrator
    reloaded = False
    orch = get_orchestrator()
    if orch:
        try:
            orch.load_all_models()
            reloaded = True
        except Exception as exc:
            logger.warning(f"Orchestrator reload failed after promote: {exc}")

    return {
        "key":              key,
        "previous_version": previous_version,
        "active_version":   row.active_version,
        "pkl_path":         row.pkl_path,
        "version_count":    len(history),
        "orchestrator_reloaded": reloaded,
    }


@router.get("/audit")
async def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Recent AI audit log entries (newest first)."""
    result = await db.execute(
        select(AIPredictionAudit)
        .order_by(desc(AIPredictionAudit.created_at))
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()

    return {
        "total": len(rows),
        "offset": offset,
        "entries": [_audit_to_dict(r) for r in rows],
    }


@router.get("/audit/{match_id}")
async def get_audit_for_match(match_id: str, db: AsyncSession = Depends(get_db)):
    """All audit entries for a specific match (most recent first)."""
    result = await db.execute(
        select(AIPredictionAudit)
        .where(AIPredictionAudit.match_id == match_id)
        .order_by(desc(AIPredictionAudit.created_at))
    )
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No audit records for match '{match_id}'")

    return {
        "match_id": match_id,
        "count": len(rows),
        "entries": [_audit_to_dict(r) for r in rows],
    }


@router.get("/performance")
async def model_performance_leaderboard(db: AsyncSession = Depends(get_db)):
    """Model performance ranked by current weight (proxy for cumulative accuracy)."""
    report = await get_model_performance_report(db)
    return {"models": report}


@router.post("/weights/adjust")
async def trigger_bulk_adjustment(
    body: BulkAdjustRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger bulk weight adjustment for all matches settled in the last N days.
    Only useful once real match results have been stored.
    """
    orch = get_orchestrator()
    if orch is None:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    result = await run_bulk_weight_adjustment(db, orch, days_back=body.days_back)
    return result


@router.post("/weights/sync")
async def sync_weights(db: AsyncSession = Depends(get_db)):
    """Push current DB weights into the live orchestrator (no restart needed)."""
    orch = get_orchestrator()
    if orch is None:
        raise HTTPException(status_code=503, detail="Orchestrator not available")

    synced = await sync_weights_to_orchestrator(db, orch)
    return {"synced_models": len(synced), "weights": synced}


# ── Calibration / Accuracy enhancement ───────────────────────────────────────

@router.get("/accuracy/report")
async def get_accuracy_report(
    window: int = Query(50, ge=10, le=500),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Per-model rolling-window calibration metrics (acc, log-loss, Brier).

    Lower log-loss is better — it's a strictly proper score, so this is
    the most honest measure of probability quality. Sorted best→worst.
    """
    metrics = await rolling_window_accuracy(db, window=window)
    current_T = TemperatureScaler.load().temperature
    return {
        "window": window,
        "models": [m.__dict__ for m in metrics],
        "current_temperature": current_T,
        "temperature_file": str(TEMPERATURE_PATH),
    }


@router.post("/accuracy/enhance")
async def enhance_accuracy(
    min_samples: int = Query(100, ge=20, le=10000),
    window: int = Query(50, ge=10, le=500),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Re-fit the global temperature on settled history + return latest report.

    This is safe to run at any time — it only refits a single scalar,
    persists it to disk, and is consumed lazily by the orchestrator on
    its next prediction cycle.
    """
    fit = await fit_temperature_from_history(db, min_samples=min_samples)
    metrics = await rolling_window_accuracy(db, window=window)
    return {
        "temperature_fit": fit,
        "rolling_window": {
            "window": window,
            "models": [m.__dict__ for m in metrics],
        },
        "current_temperature": TemperatureScaler.load().temperature,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _audit_to_dict(r: AIPredictionAudit) -> dict:
    return {
        "id":                r.id,
        "match_id":          r.match_id,
        "home_team":         r.home_team,
        "away_team":         r.away_team,
        "home_prob":         r.home_prob,
        "draw_prob":         r.draw_prob,
        "away_prob":         r.away_prob,
        "over_25_prob":      r.over_25_prob,
        "btts_prob":         r.btts_prob,
        "confidence":        r.confidence,
        "risk_score":        r.risk_score,
        "model_agreement":   r.model_agreement,
        "pkl_models_active": r.pkl_models_active,
        "triggered_by":      r.triggered_by,
        "created_at":        r.created_at.isoformat() if r.created_at else None,
        "individual_count":  len(r.individual_results) if r.individual_results else 0,
    }
