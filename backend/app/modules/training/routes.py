"""Training Guide & Prompt Generator API routes — Module D."""

import csv
import io
import json
import logging
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.training.models import ModuleTrainingJob, ModuleTrainingGuideStep, TrainingJobStatus
from app.modules.training.quality import score_dataset, build_column_profile
from app.modules.training.prompt_generator import generate_training_prompt, build_guide_steps

router = APIRouter(prefix="/api/training", tags=["Training Guide"])
logger = logging.getLogger(__name__)

_VITCOIN_REWARD_GOOD = Decimal("10")
_VITCOIN_REWARD_EXCELLENT = Decimal("25")
_QUALITY_THRESHOLD_GOOD = 60
_QUALITY_THRESHOLD_EXCELLENT = 80


def _parse_csv(content: bytes) -> List[dict]:
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def _parse_json(content: bytes) -> List[dict]:
    data = json.loads(content.decode("utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("matches", "data", "records", "results"):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    raise ValueError("Unrecognised JSON structure")


# ── POST /upload ────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    job_id: str
    status: str
    row_count: int
    quality_score: float
    grade: str
    vitcoin_reward: float
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    league: str = Query("unknown"),
    team_filter: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV or JSON dataset, score it, and generate a training prompt."""
    content = await file.read()
    filename = file.filename or "upload"

    try:
        if filename.lower().endswith(".csv"):
            records = _parse_csv(content)
        elif filename.lower().endswith(".json"):
            records = _parse_json(content)
        else:
            raise HTTPException(400, "Only CSV and JSON files are supported")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Could not parse file: {exc}")

    if not records:
        raise HTTPException(400, "File is empty or contains no records")

    d_from: Optional[date] = None
    d_to: Optional[date] = None
    try:
        if date_from:
            d_from = date.fromisoformat(date_from)
        if date_to:
            d_to = date.fromisoformat(date_to)
    except ValueError:
        pass

    report = score_dataset(records, league=league, date_from=d_from, date_to=d_to)
    col_profile = build_column_profile(records)

    quality_score = float(report["score"])
    reward = Decimal("0")
    if quality_score >= _QUALITY_THRESHOLD_EXCELLENT:
        reward = _VITCOIN_REWARD_EXCELLENT
    elif quality_score >= _QUALITY_THRESHOLD_GOOD:
        reward = _VITCOIN_REWARD_GOOD

    prompt = generate_training_prompt(
        quality_report=report,
        league=league,
        row_count=len(records),
        date_from=date_from,
        date_to=date_to,
    )

    job = ModuleTrainingJob(
        user_id=current_user.id,
        status=TrainingJobStatus.COMPLETED.value,
        league=league,
        team_filter=team_filter,
        date_from=d_from,
        date_to=d_to,
        row_count=len(records),
        column_profile=col_profile,
        quality_score=Decimal(str(quality_score)),
        quality_breakdown=report.get("breakdown"),
        generated_prompt=prompt,
        vitcoin_reward=reward,
        vitcoin_earned=False,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    steps = build_guide_steps(report)
    for s in steps:
        db.add(ModuleTrainingGuideStep(
            job_id=job.id,
            step_number=s["step_number"],
            title=s["step_name"],
            description=s["description"],
        ))

    if reward > 0:
        try:
            from app.modules.wallet.models import Wallet
            wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
            wallet = wallet_res.scalar_one_or_none()
            if wallet:
                wallet.vitcoin_balance += reward
                job.vitcoin_earned = True
        except Exception as exc:
            logger.warning(f"Could not credit VITCoin reward: {exc}")

    await db.commit()
    await db.refresh(job)

    return UploadResponse(
        job_id=job.id,
        status=job.status,
        row_count=len(records),
        quality_score=quality_score,
        grade=report["grade"],
        vitcoin_reward=float(reward),
        message=(
            f"Dataset scored {quality_score:.1f}/100 (Grade {report['grade']}). "
            + (f"Earned {float(reward):.0f} VITCoin reward!" if reward > 0 else "")
        ),
    )


# ── GET /jobs ───────────────────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all training jobs for the current user."""
    result = await db.execute(
        select(ModuleTrainingJob)
        .where(ModuleTrainingJob.user_id == current_user.id)
        .order_by(ModuleTrainingJob.submitted_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    jobs = result.scalars().all()
    return [
        {
            "id": j.id,
            "status": j.status,
            "league": j.league,
            "row_count": j.row_count,
            "quality_score": float(j.quality_score) if j.quality_score else None,
            "vitcoin_reward": float(j.vitcoin_reward),
            "vitcoin_earned": j.vitcoin_earned,
            "submitted_at": j.submitted_at.isoformat(),
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]


# ── GET /jobs/{job_id} ─────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full detail of a training job including prompt and quality breakdown."""
    result = await db.execute(
        select(ModuleTrainingJob).where(
            ModuleTrainingJob.id == job_id,
            ModuleTrainingJob.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Training job not found")

    steps_result = await db.execute(
        select(ModuleTrainingGuideStep)
        .where(ModuleTrainingGuideStep.job_id == job_id)
        .order_by(ModuleTrainingGuideStep.step_number)
    )
    steps = steps_result.scalars().all()

    return {
        "id": job.id,
        "status": job.status,
        "league": job.league,
        "team_filter": job.team_filter,
        "date_from": str(job.date_from) if job.date_from else None,
        "date_to": str(job.date_to) if job.date_to else None,
        "row_count": job.row_count,
        "quality_score": float(job.quality_score) if job.quality_score else None,
        "quality_breakdown": job.quality_breakdown,
        "column_profile": job.column_profile,
        "generated_prompt": job.generated_prompt,
        "vitcoin_reward": float(job.vitcoin_reward),
        "vitcoin_earned": job.vitcoin_earned,
        "model_accuracy": float(job.model_accuracy) if job.model_accuracy else None,
        "improvement_suggestion": job.improvement_suggestion,
        "submitted_at": job.submitted_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "guide_steps": [
            {
                "step_number": s.step_number,
                "title": s.title,
                "description": s.description,
            }
            for s in steps
        ],
    }


# ── POST /score ─────────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    records: List[dict]
    league: str = "unknown"
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@router.post("/score")
async def score_records(body: ScoreRequest):
    """Score a dataset passed as JSON (no persistence — quick preview)."""
    d_from = date.fromisoformat(body.date_from) if body.date_from else None
    d_to = date.fromisoformat(body.date_to) if body.date_to else None
    report = score_dataset(body.records, league=body.league, date_from=d_from, date_to=d_to)
    return report


# ── GET /prompt/{job_id} ───────────────────────────────────────────────

@router.get("/prompt/{job_id}")
async def get_prompt(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the generated AI training prompt for a job."""
    result = await db.execute(
        select(ModuleTrainingJob).where(
            ModuleTrainingJob.id == job_id,
            ModuleTrainingJob.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.generated_prompt:
        raise HTTPException(404, "No prompt generated yet for this job")
    return {
        "job_id": job_id,
        "prompt": job.generated_prompt,
        "quality_score": float(job.quality_score) if job.quality_score else None,
        "league": job.league,
        "row_count": job.row_count,
    }
