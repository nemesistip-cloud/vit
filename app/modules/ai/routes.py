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
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a Colab-trained .pkl file for a specific model key.

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
    if not file.filename.endswith(".pkl"):
        raise HTTPException(status_code=400, detail="Only .pkl files are accepted")

    row = await get_model_by_key(db, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not in registry")

    dest_path = os.path.join(MODELS_DIR, f"{key}.pkl")
    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    # Attempt to validate the pkl immediately
    try:
        import joblib
        payload = joblib.load(dest_path)
        if not isinstance(payload, dict) or "model" not in payload:
            os.remove(dest_path)
            raise HTTPException(
                status_code=422,
                detail="pkl must be a dict with at least a 'model' key"
            )
        metrics = payload.get("metrics", {})
        samples = payload.get("training_samples", 0)
        version = payload.get("version", "?")
    except HTTPException:
        raise
    except Exception as exc:
        os.remove(dest_path)
        raise HTTPException(status_code=422, detail=f"Failed to load pkl: {exc}")

    # Update registry
    row.pkl_loaded = True
    row.pkl_path = dest_path
    row.training_samples = samples
    row.version = version
    if metrics.get("accuracy"):
        row.accuracy = metrics["accuracy"]
        row.accuracy_1x2 = metrics.get("accuracy", row.accuracy_1x2)
    if metrics.get("brier_score"):
        row.brier_score = metrics["brier_score"]
    if metrics.get("log_loss"):
        row.log_loss = metrics["log_loss"]

    # Boost weight to 2× if it was at default
    if row.weight < 2.0:
        row.weight = 2.0

    await db.commit()

    # Hot-reload in live orchestrator
    reloaded = False
    orch = get_orchestrator()
    if orch:
        try:
            orch.load_all_models()
            reloaded = True
            # Sync the new weight to orchestrator model_meta
            orch.model_meta[key]["weight"] = row.weight
        except Exception as exc:
            logger.warning(f"Orchestrator reload failed after pkl upload: {exc}")

    return {
        "key":              key,
        "filename":         file.filename,
        "size_bytes":       len(content),
        "training_samples": samples,
        "version":          version,
        "metrics":          metrics,
        "new_weight":       row.weight,
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
