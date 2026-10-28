"""Fail-closed API for durable, dry-run GitHub Actions job records."""
from __future__ import annotations

import hmac
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_env
from app.db.database import get_db
from app.services.scheduled_job_runs import (
    InvalidScheduledRun,
    ScheduledRunConflict,
    ScheduledRunNotFound,
    claim_run,
    claim_next_run,
    enqueue_daily_service_health,
    finish_run,
    get_run,
)

router = APIRouter(prefix="/api/v1/scheduled-jobs", tags=["Scheduled Jobs"])


def _require_scheduler_token(
    x_github_scheduler_token: str | None = Header(None, alias="X-GitHub-Scheduler-Token"),
) -> None:
    environment = get_env("ENVIRONMENT", "development").strip().lower()
    if environment not in {"testing", "staging"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduled job API is restricted to testing and staging",
        )
    expected = get_env("GITHUB_SCHEDULER_TOKEN", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduled job API is not configured",
        )
    if not x_github_scheduler_token or not hmac.compare_digest(x_github_scheduler_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid scheduler credentials")


class EnqueueRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schedule_key: str = Field(..., min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    dry_run: bool = True


class ClaimRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runner_id: str = Field(..., min_length=1, max_length=100)
    claim_token: str = Field(..., min_length=32, max_length=100)


class FinishRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_token: str = Field(..., min_length=32, max_length=100)
    outcome: Literal["succeeded", "failed"]
    result: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = Field(None, max_length=80)


def _translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ScheduledRunNotFound):
        return HTTPException(status_code=404, detail="Scheduled run not found")
    if isinstance(exc, ScheduledRunConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, InvalidScheduledRun):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Scheduled run operation failed")


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(_require_scheduler_token)])
async def enqueue_run(
    body: EnqueueRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not body.dry_run:
        raise HTTPException(status_code=422, detail="Only dry-run jobs are enabled")
    try:
        run, created = await enqueue_daily_service_health(db, body.schedule_key)
    except Exception as exc:
        raise _translate_error(exc) from exc
    details = await get_run(db, run.id)
    return {"created": created, **details}


@router.post("/runs/{run_id}/claim", dependencies=[Depends(_require_scheduler_token)])
async def claim_scheduled_run(
    run_id: int,
    body: ClaimRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await claim_run(db, run_id, body.runner_id, body.claim_token)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.post("/runs/claim-next", dependencies=[Depends(_require_scheduler_token)])
async def claim_next_scheduled_run(
    body: ClaimRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await claim_next_run(db, body.runner_id, body.claim_token)
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.post("/runs/{run_id}/finish", dependencies=[Depends(_require_scheduler_token)])
async def finish_scheduled_run(
    run_id: int,
    body: FinishRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await finish_run(
            db,
            run_id,
            body.claim_token,
            body.outcome,
            body.result,
            body.error_code,
        )
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.get("/runs/{run_id}", dependencies=[Depends(_require_scheduler_token)])
async def scheduled_run_status(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await get_run(db, run_id)
    except Exception as exc:
        raise _translate_error(exc) from exc