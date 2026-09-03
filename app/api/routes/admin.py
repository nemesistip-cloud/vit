"""app/api/routes/admin.py — VIT Admin API v5.5.0 (full rebuild)

All routes: prefix /admin (registered as /api/admin/* via main.py include_router with prefix=/api).
Auth: Depends(require_admin) on every route. Depends(require_super_admin) on destructive routes.
Every mutation calls await write_audit(...).
"""
import csv
import io
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import psutil
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.admin import require_admin, require_super_admin
from app.config import get_env, APP_VERSION
from app.core.errors import AppError
from app.db.database import get_db
from app.db.models import User, AuditLog, Match, Prediction, TrainingJob
from app.modules.ai.models import ModelMetadata
from app.modules.wallet.models import (
    Wallet, WalletTransaction, PlatformConfig,
    VITCoinPriceHistory, WithdrawalRequest,
)
from app.services.audit import write_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_user(u: User, wallet_balance: float = 0.0, prediction_count: int = 0) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "role": u.role,
        "admin_role": getattr(u, "admin_role", None),
        "subscription_tier": getattr(u, "subscription_tier", "free"),
        "is_active": u.is_active,
        "is_flagged": getattr(u, "is_flagged", False),
        "withdrawals_frozen": getattr(u, "withdrawals_frozen", False),
        "kyc_status": getattr(u, "kyc_status", "unverified"),
        "wallet_balance": wallet_balance,
        "prediction_count": prediction_count,
        "created_at": u.created_at.isoformat() if hasattr(u, "created_at") and u.created_at else None,
    }


# ── User Management ────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    role: Optional[str] = None,
    subscription_tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(User)
    if search:
        q = q.where(or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    if role:
        q = q.where(User.role == role)
    if subscription_tier:
        q = q.where(User.subscription_tier == subscription_tier)
    if is_active is not None:
        q = q.where(User.is_active == is_active)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()

    q = q.order_by(desc(User.id)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    users = result.scalars().all()

    rows = []
    for u in users:
        wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == u.id))
        w = wallet_res.scalar_one_or_none()
        bal = float(w.vitcoin_balance or 0) if w else 0.0
        pred_res = await db.execute(select(func.count(Prediction.id)).where(Prediction.user_id == u.id))
        pc = pred_res.scalar_one() or 0
        rows.append(_fmt_user(u, bal, pc))

    return {"total": total, "page": page, "limit": limit, "users": rows}


@router.get("/users/export")
async def export_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    subscription_tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(User)
    if search:
        q = q.where(or_(User.username.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    if role:
        q = q.where(User.role == role)
    if subscription_tier:
        q = q.where(User.subscription_tier == subscription_tier)
    if is_active is not None:
        q = q.where(User.is_active == is_active)
    result = await db.execute(q.order_by(desc(User.id)))
    users = result.scalars().all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "username", "email", "role", "subscription_tier", "is_active", "kyc_status", "created_at"])
    writer.writeheader()
    for u in users:
        writer.writerow({
            "id": u.id, "username": u.username, "email": u.email,
            "role": u.role, "subscription_tier": getattr(u, "subscription_tier", "free"),
            "is_active": u.is_active, "kyc_status": getattr(u, "kyc_status", "unverified"),
            "created_at": u.created_at.isoformat() if hasattr(u, "created_at") and u.created_at else "",
        })
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"},
    )


@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise AppError("User not found", status_code=404, code="not_found")

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    w = wallet_res.scalar_one_or_none()
    bal = float(w.vitcoin_balance or 0) if w else 0.0

    pred_res = await db.execute(select(func.count(Prediction.id)).where(Prediction.user_id == user_id))
    pc = pred_res.scalar_one() or 0

    data = _fmt_user(u, bal, pc)
    data["validator_status"] = None
    data["referral_count"] = 0
    data["clv_score"] = None
    return data


class UpdateUserBody(BaseModel):
    role: Optional[str] = None
    subscription_tier: Optional[str] = None
    is_active: Optional[bool] = None
    withdrawals_frozen: Optional[bool] = None
    is_flagged: Optional[bool] = None


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UpdateUserBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise AppError("User not found", status_code=404, code="not_found")

    before = _fmt_user(u)
    if body.role is not None:
        u.role = body.role
    if body.subscription_tier is not None:
        u.subscription_tier = body.subscription_tier
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.withdrawals_frozen is not None:
        u.withdrawals_frozen = body.withdrawals_frozen
    if body.is_flagged is not None:
        u.is_flagged = body.is_flagged

    await db.commit()
    await db.refresh(u)
    after = _fmt_user(u)
    await write_audit(db, admin.id, "user.update", "user", user_id, before, after, request)
    return after


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise AppError("User not found", status_code=404, code="not_found")
    await write_audit(db, admin.id, "user.reset_password", "user", user_id, request=request)
    return {"ok": True, "message": f"Password reset initiated for {u.email}"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise AppError("User not found", status_code=404, code="not_found")
    if u.id == admin.id:
        raise AppError("Cannot delete your own account", status_code=400, code="invalid_operation")
    before = _fmt_user(u)
    u.is_active = False
    await db.commit()
    await write_audit(db, admin.id, "user.soft_delete", "user", user_id, before, {"is_active": False}, request)
    return {"ok": True, "message": "User deactivated"}


# ── Match & Prediction Management ──────────────────────────────────────────────

@router.get("/matches")
async def list_matches(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    league: Optional[str] = None,
    sport: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(Match)
    if status:
        q = q.where(Match.status == status)
    if league:
        q = q.where(Match.league == league)
    if sport:
        q = q.where(Match.sport == sport)
    if date_from:
        q = q.where(Match.kickoff_time >= datetime.fromisoformat(date_from.replace("Z", "+00:00")).replace(tzinfo=None))
    if date_to:
        q = q.where(Match.kickoff_time <= datetime.fromisoformat(date_to.replace("Z", "+00:00")).replace(tzinfo=None))

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()

    q = q.order_by(desc(Match.kickoff_time)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    matches = result.scalars().all()

    def fmt(m: Match) -> dict:
        return {
            "id": m.id, "home_team": m.home_team, "away_team": m.away_team,
            "league": getattr(m, "league", None), "sport": getattr(m, "sport", "football"),
            "match_date": m.kickoff_time.isoformat() if m.kickoff_time else None,
            "status": m.status,
            "actual_outcome": getattr(m, "actual_outcome", None),
            "home_goals": getattr(m, "home_goals", None),
            "away_goals": getattr(m, "away_goals", None),
        }

    return {"total": total, "page": page, "limit": limit, "matches": [fmt(m) for m in matches]}


class SetResultBody(BaseModel):
    actual_outcome: str
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None


@router.patch("/matches/{match_id}/result")
async def set_match_result(
    match_id: str,
    body: SetResultBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    m = result.scalar_one_or_none()
    if not m:
        raise AppError("Match not found", status_code=404, code="not_found")

    before = {"actual_outcome": getattr(m, "actual_outcome", None), "status": m.status}
    m.actual_outcome = body.actual_outcome
    if body.home_goals is not None:
        m.home_goals = body.home_goals
    if body.away_goals is not None:
        m.away_goals = body.away_goals
    m.status = "settled"
    await db.commit()
    after = {"actual_outcome": m.actual_outcome, "status": m.status}
    await write_audit(db, admin.id, "match.set_result", "match", match_id, before, after, request)
    return {"ok": True, "match_id": match_id, "outcome": body.actual_outcome}


@router.delete("/matches/{match_id}")
async def delete_match(
    match_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    result = await db.execute(select(Match).where(Match.id == match_id))
    m = result.scalar_one_or_none()
    if not m:
        raise AppError("Match not found", status_code=404, code="not_found")
    before = {"status": m.status}
    m.status = "deleted"
    await db.commit()
    await write_audit(db, admin.id, "match.delete", "match", match_id, before, {"status": "deleted"}, request)
    return {"ok": True}


@router.get("/predictions")
async def list_predictions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = None,
    match_id: Optional[str] = None,
    was_correct: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(Prediction)
    if user_id:
        q = q.where(Prediction.user_id == user_id)
    if match_id:
        q = q.where(Prediction.match_id == match_id)
    if was_correct is not None:
        q = q.where(Prediction.was_correct == was_correct)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()

    q = q.order_by(desc(Prediction.created_at)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    preds = result.scalars().all()

    def fmt(p: Prediction) -> dict:
        return {
            "id": p.id, "user_id": p.user_id, "match_id": p.match_id,
            "market": getattr(p, "market", None), "selection": getattr(p, "selection", None),
            "was_correct": getattr(p, "was_correct", None),
            "clv": getattr(p, "clv", None),
            "created_at": p.created_at.isoformat() if hasattr(p, "created_at") and p.created_at else None,
        }

    return {"total": total, "page": page, "limit": limit, "predictions": [fmt(p) for p in preds]}


@router.post("/predictions/recalculate-clv")
async def recalculate_clv(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await write_audit(db, admin.id, "predictions.recalculate_clv", request=request)
    return {"ok": True, "message": "CLV recalculation queued"}


# ── Platform Config ────────────────────────────────────────────────────────────

@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(PlatformConfig).order_by(PlatformConfig.key))
    rows = result.scalars().all()
    return [
        {
            "id": r.id, "key": r.key, "value": r.value,
            "description": r.description,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


class ConfigUpdateBody(BaseModel):
    value: object


@router.put("/config/{key}")
async def update_config(
    key: str,
    body: ConfigUpdateBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == key))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise AppError("Config key not found", status_code=404, code="not_found")
    before = {"value": cfg.value}
    cfg.value = body.value
    cfg.updated_at = datetime.now(timezone.utc)
    cfg.updated_by = admin.id
    await db.commit()
    await write_audit(db, admin.id, "config.update", "platform_config", key, before, {"value": body.value}, request)
    return {"ok": True, "key": key, "value": body.value}


class ConfigCreateBody(BaseModel):
    key: str
    value: object
    description: Optional[str] = None


@router.post("/config")
async def create_config(
    body: ConfigCreateBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    existing = await db.execute(select(PlatformConfig).where(PlatformConfig.key == body.key))
    if existing.scalar_one_or_none():
        raise AppError("Config key already exists", status_code=409, code="conflict")
    import uuid
    cfg = PlatformConfig(
        id=str(uuid.uuid4()), key=body.key, value=body.value,
        description=body.description, updated_by=admin.id,
        updated_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc),
    )
    db.add(cfg)
    await db.commit()
    await write_audit(db, admin.id, "config.create", "platform_config", body.key, None, {"value": body.value}, request)
    return {"ok": True, "key": body.key}


@router.delete("/config/{key}")
async def delete_config(
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == key))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise AppError("Config key not found", status_code=404, code="not_found")
    before = {"key": key, "value": cfg.value}
    await db.delete(cfg)
    await db.commit()
    await write_audit(db, admin.id, "config.delete", "platform_config", key, before, None, request)
    return {"ok": True}


# ── AI Models & Training ───────────────────────────────────────────────────────

@router.get("/models")
async def list_models(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = await db.execute(select(ModelMetadata).order_by(ModelMetadata.key))
    models = result.scalars().all()
    return [
        {
            "id": m.id, "key": m.key, "name": m.name,
            "model_type": getattr(m, "model_type", None),
            "weight": float(m.weight or 0) if m.weight else 0,
            "accuracy": float(m.accuracy or 0) if m.accuracy else 0,
            "clv_score": float(m.clv_score or 0) if m.clv_score else 0,
            "is_active": m.is_active,
            "auto_demoted": getattr(m, "auto_demoted", False),
            "version": getattr(m, "version", None),
            "last_trained_at": getattr(m, "last_trained_at", None),
        }
        for m in models
    ]


def _format_admin_job(j_db: Optional[TrainingJob] = None, j_mem: Optional[dict] = None) -> dict:
    job_id = (j_mem.get("job_id") if j_mem else None) or (j_db.job_id if j_db else None) or (str(j_db.id) if j_db else None)
    db_id = j_db.id if j_db else None

    config = (j_mem.get("config") if j_mem else None) or (j_db.config if j_db else {}) or {}
    summary = (j_mem.get("summary") if j_mem else None) or (j_db.summary if j_db else {}) or {}
    results = (j_mem.get("results") if j_mem else None) or (j_db.results if j_db else {}) or {}
    events = (j_mem.get("events") if j_mem else None) or (j_db.events if j_db else []) or []

    status = (j_mem.get("status") if j_mem else None) or (j_db.status if j_db else "unknown")
    progress_pct = j_mem.get("progress_pct") if (j_mem and "progress_pct" in j_mem) else (j_db.progress_pct if j_db and j_db.progress_pct is not None else 0.0)
    current_model = (j_mem.get("current_model") if j_mem else None) or (j_db.current_model if j_db else None)
    total_models = (j_mem.get("total_models") if j_mem else None) or (j_db.total_models if j_db else 0)
    error_message = (j_mem.get("error_message") if j_mem else None) or (j_db.error_message if j_db else None)
    created_by = (j_mem.get("created_by") if j_mem else None) or (j_db.created_by if j_db else "system")

    target_keys = config.get("target_model_keys") or []
    model_key = target_keys[0] if target_keys else (summary.get("model_key") or current_model or "ensemble")

    created_at = (j_mem.get("created_at") if j_mem else None) or (j_db.created_at.isoformat() if j_db and j_db.created_at else None)
    started_at = (j_mem.get("started_at") if j_mem else None) or (j_db.started_at.isoformat() if j_db and j_db.started_at else None)
    completed_at = (j_mem.get("completed_at") if j_mem else None) or (j_db.completed_at.isoformat() if j_db and j_db.completed_at else None)

    return {
        "id": db_id or job_id,
        "job_id": job_id,
        "status": status,
        "model_key": model_key,
        "progress_pct": round(float(progress_pct or 0.0), 1),
        "current_model": current_model,
        "total_models": total_models,
        "events": events,
        "config": config,
        "summary": summary,
        "results": results,
        "error_message": error_message,
        "created_by": created_by,
        "created_at": created_at,
        "started_at": started_at,
        "completed_at": completed_at,
        "in_memory": j_mem is not None,
    }


@router.post("/models/{model_key}/retrain")
async def retrain_model(
    model_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.api.routes.training import start_admin_training_request, TrainingConfig
    result = await db.execute(select(ModelMetadata).where(ModelMetadata.key == model_key))
    m = result.scalar_one_or_none()
    if not m:
        raise AppError("Model not found", status_code=404, code="not_found")

    config = TrainingConfig(target_model_keys=[model_key])
    created_by = getattr(admin, "email", None) or str(getattr(admin, "id", "admin"))
    res = await start_admin_training_request(config, created_by=created_by)
    await write_audit(db, admin.id, "model.retrain", "model", model_key, request=request)
    return {
        "ok": True,
        "job_id": res["job_id"],
        "status": res["status"],
        "model_key": model_key,
        "message": f"Retrain job {res['job_id']} queued for model {model_key}",
    }


@router.post("/models/retrain-all")
async def retrain_all_models(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.api.routes.training import start_admin_training_request, TrainingConfig
    config = TrainingConfig()
    created_by = getattr(admin, "email", None) or str(getattr(admin, "id", "admin"))
    res = await start_admin_training_request(config, created_by=created_by)
    await write_audit(db, admin.id, "model.retrain_all", request=request)
    return {
        "ok": True,
        "job_id": res["job_id"],
        "status": res["status"],
        "message": f"Full ensemble retrain job {res['job_id']} queued",
    }


@router.post("/training-jobs/trigger")
@router.post("/training-jobs")
async def trigger_training_job(
    request: Request,
    body: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.api.routes.training import start_admin_training_request, TrainingConfig
    cfg = TrainingConfig(**(body or {}))
    created_by = getattr(admin, "email", None) or str(getattr(admin, "id", "admin"))
    res = await start_admin_training_request(cfg, created_by=created_by)
    await write_audit(db, admin.id, "training_job.trigger", "training_job", res["job_id"], request=request)
    return {
        "ok": True,
        "job_id": res["job_id"],
        "status": res["status"],
        "message": res["message"],
    }


@router.get("/training-jobs")
async def list_training_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.api.routes.training import _training_jobs

    q = select(TrainingJob)
    if status:
        q = q.where(TrainingJob.status == status)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total_db = total_res.scalar_one()

    q = q.order_by(desc(TrainingJob.created_at)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    db_jobs = result.scalars().all()

    job_map = {}
    for j_db in db_jobs:
        j_mem = _training_jobs.get(j_db.job_id)
        payload = _format_admin_job(j_db=j_db, j_mem=j_mem)
        job_map[payload["job_id"]] = payload

    for mem_id, j_mem in _training_jobs.items():
        if mem_id not in job_map:
            mem_status = j_mem.get("status", "unknown")
            if status and mem_status != status:
                continue
            payload = _format_admin_job(j_db=None, j_mem=j_mem)
            job_map[mem_id] = payload

    formatted_jobs = list(job_map.values())
    total = max(total_db, len(job_map))

    return {"total": total, "page": page, "limit": limit, "jobs": formatted_jobs}


@router.get("/training-jobs/{job_id}")
async def get_training_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.api.routes.training import _training_jobs

    j_mem = _training_jobs.get(job_id)

    conditions = [TrainingJob.job_id == job_id]
    if job_id.isdigit():
        conditions.append(TrainingJob.id == int(job_id))

    result = await db.execute(select(TrainingJob).where(or_(*conditions)))
    j_db = result.scalars().first()

    if not j_mem and not j_db:
        raise AppError("Training job not found", status_code=404, code="not_found")

    return _format_admin_job(j_db=j_db, j_mem=j_mem)


@router.post("/training-jobs/{job_id}/cancel")
async def cancel_training_job(
    job_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.api.routes.training import _training_jobs, _training_tasks, _db_update_job

    j_mem = _training_jobs.get(job_id)
    conditions = [TrainingJob.job_id == job_id]
    if job_id.isdigit():
        conditions.append(TrainingJob.id == int(job_id))

    result = await db.execute(select(TrainingJob).where(or_(*conditions)))
    j_db = result.scalars().first()

    if not j_mem and not j_db:
        raise AppError("Training job not found", status_code=404, code="not_found")

    current_status = (j_mem.get("status") if j_mem else None) or (j_db.status if j_db else "unknown")
    if current_status in ("completed", "failed", "cancelled"):
        raise AppError(f"Cannot cancel job in '{current_status}' state", status_code=400, code="bad_request")

    real_job_id = (j_mem.get("job_id") if j_mem else None) or (j_db.job_id if j_db else job_id)

    task = _training_tasks.get(real_job_id) or _training_tasks.get(job_id)
    if task and not task.done():
        task.cancel()

    completed_at = datetime.now(timezone.utc)
    if j_mem:
        j_mem["status"] = "cancelled"
        j_mem["completed_at"] = completed_at.isoformat()
        if "events" in j_mem and isinstance(j_mem["events"], list):
            j_mem["events"].append({"type": "cancelled", "message": "Cancelled by admin", "ts": time.time()})

    if j_db:
        j_db.status = "cancelled"
        j_db.completed_at = completed_at
        if j_db.events is None:
            j_db.events = []
        if isinstance(j_db.events, list):
            j_db.events.append({"type": "cancelled", "message": "Cancelled by admin", "ts": time.time()})
        await db.commit()

    await _db_update_job(real_job_id, status="cancelled", completed_at=completed_at)
    await write_audit(db, admin.id, "training_job.cancel", "training_job", real_job_id, request=request)

    return {
        "ok": True,
        "job_id": real_job_id,
        "status": "cancelled",
        "message": f"Training job {real_job_id} cancelled",
    }


@router.delete("/training-jobs/{job_id}")
async def delete_training_job(
    job_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    from app.api.routes.training import _training_jobs

    j_mem = _training_jobs.get(job_id)
    conditions = [TrainingJob.job_id == job_id]
    if job_id.isdigit():
        conditions.append(TrainingJob.id == int(job_id))

    result = await db.execute(select(TrainingJob).where(or_(*conditions)))
    j_db = result.scalars().first()

    if not j_mem and not j_db:
        raise AppError("Training job not found", status_code=404, code="not_found")

    current_status = (j_mem.get("status") if j_mem else None) or (j_db.status if j_db else "unknown")
    if current_status in ("queued", "running"):
        raise AppError("Cannot delete an actively running or queued job. Cancel it first.", status_code=400, code="bad_request")

    real_job_id = (j_mem.get("job_id") if j_mem else None) or (j_db.job_id if j_db else job_id)

    if real_job_id in _training_jobs:
        del _training_jobs[real_job_id]
    if job_id in _training_jobs:
        del _training_jobs[job_id]

    if j_db:
        await db.delete(j_db)
        await db.commit()

    await write_audit(db, admin.id, "training_job.delete", "training_job", real_job_id, request=request)

    return {
        "ok": True,
        "job_id": real_job_id,
        "message": f"Training job record {real_job_id} deleted",
    }


# ── Audit Log ──────────────────────────────────────────────────────────────────

@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin_id: Optional[int] = None,
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(AuditLog)
    if admin_id:
        q = q.where(AuditLog.actor == str(admin_id))
    if action:
        q = q.where(AuditLog.action.ilike(f"%{action}%"))
    if target_type:
        q = q.where(AuditLog.resource == target_type)
    if date_from:
        q = q.where(AuditLog.timestamp >= date_from)
    if date_to:
        q = q.where(AuditLog.timestamp <= date_to)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()

    q = q.order_by(desc(AuditLog.timestamp)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(q)
    logs = result.scalars().all()

    def fmt(l: AuditLog) -> dict:
        details = l.details or {}
        return {
            "id": l.id,
            "admin_id": l.actor,
            "action": l.action,
            "target_type": l.resource,
            "target_id": l.resource_id,
            "before": details.get("before"),
            "after": details.get("after"),
            "ip_address": l.ip_address,
            "created_at": l.timestamp.isoformat() if l.timestamp else None,
        }

    return {"total": total, "page": page, "limit": limit, "logs": [fmt(l) for l in logs]}


# ── System ─────────────────────────────────────────────────────────────────────

@router.get("/system/health")
async def system_health(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        if r:
            await r.ping()
            redis_ok = True
    except Exception:
        pass

    try:
        from app.core.dependencies import get_orchestrator
        orch = get_orchestrator()
        models_ready = orch.num_models_ready() if orch else 0
    except Exception:
        models_ready = 0

    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    pred_count_res = await db.execute(select(func.count(Prediction.id)))
    pred_count = pred_count_res.scalar_one() or 0

    user_count_res = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    user_count = user_count_res.scalar_one() or 0

    return {
        "status": "ok" if db_ok else "degraded",
        "version": APP_VERSION,
        "database": {"status": "connected" if db_ok else "error"},
        "redis": {"status": "connected" if redis_ok else "unavailable"},
        "models_ready": models_ready,
        "active_users": user_count,
        "total_predictions": pred_count,
        "tachyon_nodes": 0,
        "resources": {
            "cpu_pct": cpu,
            "ram_used_gb": round(mem.used / 1e9, 2),
            "ram_total_gb": round(mem.total / 1e9, 2),
            "disk_used_gb": round(disk.used / 1e9, 2),
            "disk_total_gb": round(disk.total / 1e9, 2),
        },
    }


@router.get("/system/metrics")
async def system_metrics(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        requests_24h = int(await r.get("metrics:requests:24h") or 0) if r else 0
        errors_24h = int(await r.get("metrics:errors:24h") or 0) if r else 0
        avg_ms = float(await r.get("metrics:avg_response_ms") or 0) if r else 0
    except Exception:
        requests_24h = errors_24h = 0
        avg_ms = 0.0

    error_rate = round(errors_24h / requests_24h * 100, 2) if requests_24h > 0 else 0.0

    return {
        "requests_24h": requests_24h,
        "errors_24h": errors_24h,
        "error_rate_pct": error_rate,
        "avg_response_ms": avg_ms,
    }


@router.post("/system/cache/flush")
async def flush_cache(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    flushed = 0
    try:
        from app.core.redis import get_redis
        r = await get_redis()
        if r:
            admin_keys = await r.keys("admin:*")
            pred_keys = await r.keys("predictions:*")
            keys = admin_keys + pred_keys
            if keys:
                flushed = await r.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache flush partial error: {e}")

    await write_audit(db, admin.id, "system.cache_flush", request=request)
    return {"ok": True, "keys_flushed": flushed}


# ── Validators (admin view) ─────────────────────────────────────────────────────

@router.get("/validators")
async def list_validators(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        from app.modules.blockchain.models import ValidatorProfile
        result = await db.execute(select(ValidatorProfile).order_by(desc(ValidatorProfile.id)))
        validators = result.scalars().all()
        return [
            {
                "id": v.id, "user_id": v.user_id,
                "status": str(v.status.value) if hasattr(v.status, "value") else str(v.status),
                "stake_amount": float(v.stake_amount or 0),
                "trust_score": float(v.trust_score or 0) if hasattr(v, "trust_score") else 0,
                "accurate_predictions": getattr(v, "accurate_predictions", 0),
                "total_predictions": getattr(v, "total_predictions", 0),
                "created_at": v.created_at.isoformat() if hasattr(v, "created_at") and v.created_at else None,
            }
            for v in validators
        ]
    except Exception as e:
        logger.error(f"Error listing validators: {e}")
        return []


class SlashBody(BaseModel):
    amount: float
    reason: str


@router.post("/validators/{validator_id}/slash")
async def slash_validator(
    validator_id: int,
    body: SlashBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    try:
        from app.modules.blockchain.models import ValidatorProfile, ValidatorSlashEvent
        result = await db.execute(select(ValidatorProfile).where(ValidatorProfile.id == validator_id))
        v = result.scalar_one_or_none()
        if not v:
            raise AppError("Validator not found", status_code=404, code="not_found")

        before_stake = float(v.stake_amount or 0)
        v.stake_amount = max(0, before_stake - body.amount)

        slash = ValidatorSlashEvent(
            validator_id=validator_id,
            amount=body.amount,
            reason=body.reason,
            admin_id=admin.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(slash)
        await db.commit()
        await write_audit(
            db, admin.id, "validator.slash", "validator", validator_id,
            {"stake": before_stake}, {"stake": float(v.stake_amount), "reason": body.reason},
            request,
        )
        return {"ok": True}
    except AppError:
        raise
    except Exception as e:
        logger.error(f"Slash error: {e}")
        raise AppError("Failed to slash validator", status_code=500, code="server_error")


@router.post("/validators/{validator_id}/reinstate")
async def reinstate_validator(
    validator_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    try:
        from app.modules.blockchain.models import ValidatorProfile, ValidatorStatus
        result = await db.execute(select(ValidatorProfile).where(ValidatorProfile.id == validator_id))
        v = result.scalar_one_or_none()
        if not v:
            raise AppError("Validator not found", status_code=404, code="not_found")
        before = str(v.status)
        v.status = ValidatorStatus.active
        await db.commit()
        await write_audit(db, admin.id, "validator.reinstate", "validator", validator_id,
                          {"status": before}, {"status": "active"}, request)
        return {"ok": True}
    except AppError:
        raise
    except Exception as e:
        raise AppError("Failed to reinstate validator", status_code=500, code="server_error")


@router.get("/validators/appeals")
async def list_validator_appeals(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        from app.modules.blockchain.models import ValidatorAppeal
        result = await db.execute(
            select(ValidatorAppeal).where(ValidatorAppeal.status == "pending").order_by(desc(ValidatorAppeal.created_at))
        )
        appeals = result.scalars().all()
        return [
            {
                "id": a.id, "validator_id": a.validator_id,
                "reason": getattr(a, "reason", None),
                "evidence": getattr(a, "evidence", None),
                "status": getattr(a, "status", "pending"),
                "created_at": a.created_at.isoformat() if hasattr(a, "created_at") and a.created_at else None,
            }
            for a in appeals
        ]
    except Exception as e:
        logger.error(f"Appeals error: {e}")
        return []


class AppealDecisionBody(BaseModel):
    decision: str
    admin_note: Optional[str] = None


@router.patch("/validators/appeals/{appeal_id}")
async def decide_appeal(
    appeal_id: str,
    body: AppealDecisionBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if body.decision not in ("approved", "rejected"):
        raise AppError("decision must be 'approved' or 'rejected'", status_code=400, code="invalid_input")
    try:
        from app.modules.blockchain.models import ValidatorAppeal
        result = await db.execute(select(ValidatorAppeal).where(ValidatorAppeal.id == appeal_id))
        a = result.scalar_one_or_none()
        if not a:
            raise AppError("Appeal not found", status_code=404, code="not_found")
        before = {"status": a.status}
        a.status = body.decision
        if body.admin_note:
            a.admin_note = body.admin_note
        await db.commit()
        await write_audit(db, admin.id, f"appeal.{body.decision}", "validator_appeal", appeal_id,
                          before, {"status": body.decision}, request)
        return {"ok": True, "decision": body.decision}
    except AppError:
        raise
    except Exception as e:
        raise AppError("Failed to update appeal", status_code=500, code="server_error")


# ── Marketplace Admin ──────────────────────────────────────────────────────────

@router.get("/marketplace/listings")
async def list_marketplace_listings(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        from app.modules.marketplace.models import AIModelListing
        q = select(AIModelListing)
        if status == "active":
            q = q.where(AIModelListing.is_active == True)
        elif status == "pending":
            q = q.where(AIModelListing.is_active == False)
        result = await db.execute(q.order_by(desc(AIModelListing.id)))
        listings = result.scalars().all()
        return [
            {
                "id": l.id, "name": l.name, "slug": getattr(l, "slug", None),
                "description": getattr(l, "description", None),
                "category": getattr(l, "category", None),
                "price_per_call": str(l.price_per_call),
                "model_key": getattr(l, "model_key", None),
                "gcs_uri": getattr(l, "gcs_uri", None),
                "is_active": l.is_active,
            }
            for l in listings
        ]
    except Exception as e:
        logger.error(f"Error listing marketplace: {e}")
        return []


@router.post("/marketplace/listings/{listing_id}/approve")
async def approve_marketplace_listing(
    listing_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        from app.modules.marketplace.models import AIModelListing
        result = await db.execute(select(AIModelListing).where(AIModelListing.id == listing_id))
        l = result.scalar_one_or_none()
        if not l:
            raise AppError("Listing not found", status_code=404, code="not_found")
        before = {"is_active": l.is_active}
        l.is_active = True
        await db.commit()
        await write_audit(db, admin.id, "marketplace.approve", "ai_model_listing", listing_id,
                          before, {"is_active": True}, request)
        return {"ok": True}
    except AppError:
        raise
    except Exception as e:
        raise AppError("Failed to approve listing", status_code=500, code="server_error")


class RejectListingBody(BaseModel):
    approval_note: Optional[str] = None


@router.post("/marketplace/listings/{listing_id}/reject")
async def reject_marketplace_listing(
    listing_id: str,
    body: RejectListingBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        from app.modules.marketplace.models import AIModelListing
        result = await db.execute(select(AIModelListing).where(AIModelListing.id == listing_id))
        l = result.scalar_one_or_none()
        if not l:
            raise AppError("Listing not found", status_code=404, code="not_found")
        before = {"is_active": l.is_active}
        l.is_active = False
        await db.commit()
        await write_audit(db, admin.id, "marketplace.reject", "ai_model_listing", listing_id,
                          before, {"is_active": False, "note": body.approval_note}, request)
        return {"ok": True}
    except AppError:
        raise
    except Exception as e:
        raise AppError("Failed to reject listing", status_code=500, code="server_error")


@router.delete("/marketplace/listings/{listing_id}")
async def delete_marketplace_listing(
    listing_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    try:
        from app.modules.marketplace.models import AIModelListing
        result = await db.execute(select(AIModelListing).where(AIModelListing.id == listing_id))
        l = result.scalar_one_or_none()
        if not l:
            raise AppError("Listing not found", status_code=404, code="not_found")
        before = {"name": l.name, "is_active": l.is_active}
        await db.delete(l)
        await db.commit()
        await write_audit(db, admin.id, "marketplace.delete", "ai_model_listing", listing_id,
                          before, None, request)
        return {"ok": True}
    except AppError:
        raise
    except Exception as e:
        raise AppError("Failed to delete listing", status_code=500, code="server_error")

# ── CSV Operations ────────────────────────────────────────────────────────────

@router.post("/upload/csv")
async def upload_users_csv(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Bulk upload/update users via CSV.
    Expected columns: username, email, role, password (optional)
    """
    try:
        body = await request.body()
        stream = io.StringIO(body.decode("utf-8"))
        reader = csv.DictReader(stream)

        count = 0
        for row in reader:
            email = row.get("email")
            if not email:
                continue

            # Check if user exists
            res = await db.execute(select(User).where(User.email == email))
            user = res.scalar_one_or_none()

            if not user:
                # Create new user
                from app.auth.pwd_utils import get_password_hash
                pwd = row.get("password", "Temporary123!")
                user = User(
                    email=email,
                    username=row.get("username", email.split("@")[0]),
                    hashed_password=get_password_hash(pwd),
                    role=row.get("role", "user"),
                    is_active=True,
                )
                db.add(user)
            else:
                # Update existing
                if "role" in row:
                    user.role = row["role"]
                if "username" in row:
                    user.username = row["username"]

            count += 1

        await db.commit()
        await write_audit(db, admin.id, "users.bulk_upload", "user", None, None, {"count": count}, request)
        return {"ok": True, "processed": count}
    except Exception as e:
        logger.error(f"CSV upload error: {e}")
        raise AppError(f"Failed to process CSV: {str(e)}", status_code=400, code="invalid_input")


# ── API Key Administration ─────────────────────────────────────────────────────

@router.get("/api-keys")
async def list_all_api_keys(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all developer API keys across all users."""
    from app.modules.developer.models import APIKey
    q = select(APIKey)
    if user_id:
        q = q.where(APIKey.user_id == user_id)
    if is_active is not None:
        q = q.where(APIKey.is_active == is_active)

    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar_one()

    q = q.order_by(desc(APIKey.created_at)).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "keys": [
            {
                "id":              k.id,
                "user_id":         k.user_id,
                "name":            k.name,
                "key_prefix":      k.key_prefix,
                "plan":            k.plan,
                "rate_limit_rpm":  k.rate_limit_rpm,
                "rate_limit_rpd":  k.rate_limit_rpd,
                "is_active":       k.is_active,
                "total_requests":  k.total_requests,
                "last_used_at":    k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at":      k.created_at.isoformat() if k.created_at else None,
                "expires_at":      k.expires_at.isoformat() if k.expires_at else None,
            }
            for k in rows
        ],
    }


@router.patch("/api-keys/{key_id}")
async def admin_update_api_key(
    key_id: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Update plan, rate limits, or active status of any API key."""
    from app.modules.developer.models import APIKey
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise AppError("API key not found", status_code=404, code="not_found")

    ALLOWED_PLANS = {"free", "starter", "pro", "enterprise"}
    before = {"plan": key.plan, "is_active": key.is_active, "rate_limit_rpm": key.rate_limit_rpm}

    if "plan" in body:
        if body["plan"] not in ALLOWED_PLANS:
            raise AppError(f"Invalid plan. Must be one of: {', '.join(sorted(ALLOWED_PLANS))}", status_code=400, code="invalid_plan")
        key.plan = body["plan"]
    if "is_active" in body:
        key.is_active = bool(body["is_active"])
    if "rate_limit_rpm" in body:
        key.rate_limit_rpm = int(body["rate_limit_rpm"])
    if "rate_limit_rpd" in body:
        key.rate_limit_rpd = int(body["rate_limit_rpd"])
    if "expires_at" in body:
        from datetime import datetime
        key.expires_at = datetime.fromisoformat(body["expires_at"]) if body["expires_at"] else None

    await db.commit()
    after = {"plan": key.plan, "is_active": key.is_active, "rate_limit_rpm": key.rate_limit_rpm}
    await write_audit(db, admin.id, "api_key.update", "api_key", key_id, before, after, request)
    return {"ok": True, "key_id": key_id, "changes": after}


@router.delete("/api-keys/{key_id}")
async def admin_revoke_api_key(
    key_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """Permanently revoke (disable) any API key."""
    from app.modules.developer.models import APIKey
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise AppError("API key not found", status_code=404, code="not_found")

    key.is_active = False
    await db.commit()
    await write_audit(db, admin.id, "api_key.revoke", "api_key", key_id, {"is_active": True}, {"is_active": False}, request)
    return {"ok": True, "revoked": key_id}


@router.get("/api-keys/usage-stats")
async def api_key_usage_stats(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Aggregate API key usage: top consumers, total calls, error rates."""
    from app.modules.developer.models import APIKey, APIUsageLog
    from datetime import datetime, timezone, timedelta

    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (await db.execute(
        select(
            APIKey.id,
            APIKey.user_id,
            APIKey.name,
            APIKey.plan,
            func.count(APIUsageLog.id).label("total_calls"),
            func.sum(
                func.cast(func.case((APIUsageLog.status_code >= 500, 1), else_=0), Integer)
            ).label("errors_5xx"),
            func.avg(APIUsageLog.latency_ms).label("avg_latency_ms"),
        ).join(APIUsageLog, APIKey.id == APIUsageLog.api_key_id, isouter=True)
        .where(APIUsageLog.called_at >= since)
        .group_by(APIKey.id, APIKey.user_id, APIKey.name, APIKey.plan)
        .order_by(desc("total_calls"))
        .limit(50)
    )).all()

    return {
        "days": days,
        "top_consumers": [
            {
                "key_id":        r.id,
                "user_id":       r.user_id,
                "name":          r.name,
                "plan":          r.plan,
                "total_calls":   r.total_calls or 0,
                "errors_5xx":    int(r.errors_5xx or 0),
                "avg_latency_ms": round(float(r.avg_latency_ms or 0), 1),
            }
            for r in rows
        ],
    }
