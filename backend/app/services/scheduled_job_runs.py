"""Durable, idempotent run ledger for GitHub Actions scheduled jobs."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ScheduledJobAttempt, ScheduledJobRun

JOB_DAILY_SERVICE_HEALTH = "daily_service_health"
MAX_ATTEMPTS = 3
LEASE_DURATION = timedelta(minutes=15)
MAX_RESULT_BYTES = 8192
_DAY_KEY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ERROR_CODE = re.compile(r"^[a-z0-9_]{1,80}$")


class ScheduledRunError(Exception):
    """Base error for safe API translation."""


class ScheduledRunNotFound(ScheduledRunError):
    pass


class ScheduledRunConflict(ScheduledRunError):
    pass


class InvalidScheduledRun(ScheduledRunError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_after_utc(value: datetime | None, reference: datetime) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value > reference


def validate_schedule_key(schedule_key: str) -> str:
    if not _DAY_KEY.fullmatch(schedule_key):
        raise InvalidScheduledRun("schedule_key must use the UTC date format YYYY-MM-DD")
    try:
        datetime.strptime(schedule_key, "%Y-%m-%d")
    except ValueError as exc:
        raise InvalidScheduledRun("schedule_key is not a valid UTC date") from exc
    return schedule_key


def _serialize_result(result: dict[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(result, separators=(",", ":"), ensure_ascii=True)
    except (TypeError, ValueError) as exc:
        raise InvalidScheduledRun("result must contain JSON-compatible values") from exc
    if len(encoded.encode("utf-8")) > MAX_RESULT_BYTES:
        raise InvalidScheduledRun("result exceeds the 8 KiB limit")
    return json.loads(encoded)


def _run_summary(run: ScheduledJobRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "job_name": run.job_name,
        "schedule_key": run.schedule_key,
        "dry_run": run.dry_run,
        "status": run.status,
        "attempt_count": run.attempt_count,
        "max_attempts": run.max_attempts,
        "next_attempt_at": run.next_attempt_at.isoformat() if run.next_attempt_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _attempt_summary(attempt: ScheduledJobAttempt) -> dict[str, Any]:
    return {
        "attempt_number": attempt.attempt_number,
        "runner_id": attempt.runner_id,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "finished_at": attempt.finished_at.isoformat() if attempt.finished_at else None,
        "error_code": attempt.error_code,
        "result": attempt.result,
    }


async def enqueue_daily_service_health(
    db: AsyncSession,
    schedule_key: str,
) -> tuple[ScheduledJobRun, bool]:
    """Create one dry-run health record per UTC date; duplicate delivery is harmless."""
    validate_schedule_key(schedule_key)
    existing = await db.scalar(
        select(ScheduledJobRun).where(
            ScheduledJobRun.job_name == JOB_DAILY_SERVICE_HEALTH,
            ScheduledJobRun.schedule_key == schedule_key,
        )
    )
    if existing is not None:
        return existing, False

    run = ScheduledJobRun(
        job_name=JOB_DAILY_SERVICE_HEALTH,
        schedule_key=schedule_key,
        dry_run=True,
        status="queued",
        attempt_count=0,
        max_attempts=MAX_ATTEMPTS,
    )
    try:
        async with db.begin_nested():
            db.add(run)
            await db.flush()
        await db.commit()
        return run, True
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(
            select(ScheduledJobRun).where(
                ScheduledJobRun.job_name == JOB_DAILY_SERVICE_HEALTH,
                ScheduledJobRun.schedule_key == schedule_key,
            )
        )
        if existing is None:
            raise
        return existing, False


async def claim_run(
    db: AsyncSession,
    run_id: int,
    runner_id: str,
    claim_token: str,
) -> dict[str, Any]:
    """Atomically claim a due run, recovering expired leases as a new attempt."""
    if not runner_id or len(runner_id) > 100:
        raise InvalidScheduledRun("runner_id must be between 1 and 100 characters")
    if not claim_token or len(claim_token) < 32 or len(claim_token) > 100:
        raise InvalidScheduledRun("claim_token must be between 32 and 100 characters")

    now = _utcnow()
    token_hash = hashlib.sha256(claim_token.encode("utf-8")).hexdigest()
    due = or_(
        and_(
            ScheduledJobRun.status.in_(("queued", "retry_wait")),
            or_(ScheduledJobRun.next_attempt_at.is_(None), ScheduledJobRun.next_attempt_at <= now),
        ),
        and_(ScheduledJobRun.status == "running", ScheduledJobRun.lease_expires_at <= now),
    )
    claim = await db.execute(
        update(ScheduledJobRun)
        .where(
            ScheduledJobRun.id == run_id,
            ScheduledJobRun.attempt_count < ScheduledJobRun.max_attempts,
            due,
        )
        .values(
            status="running",
            attempt_count=ScheduledJobRun.attempt_count + 1,
            current_attempt=ScheduledJobRun.attempt_count + 1,
            claimed_by=runner_id,
            lease_expires_at=now + LEASE_DURATION,
            next_attempt_at=None,
            updated_at=now,
        )
        .returning(ScheduledJobRun.attempt_count)
        .execution_options(synchronize_session=False)
    )
    attempt_number = claim.scalar_one_or_none()
    if attempt_number is None:
        await db.rollback()
        current = await db.get(ScheduledJobRun, run_id)
        if current is None:
            raise ScheduledRunNotFound("scheduled run not found")
        if (
            current.status == "running"
            and current.claimed_by == runner_id
            and current.current_attempt
            and _is_after_utc(current.lease_expires_at, now)
        ):
            active_attempt = await db.scalar(
                select(ScheduledJobAttempt).where(
                    ScheduledJobAttempt.run_id == run_id,
                    ScheduledJobAttempt.attempt_number == current.current_attempt,
                    ScheduledJobAttempt.status == "running",
                )
            )
            if active_attempt and hmac.compare_digest(active_attempt.claim_token_hash, token_hash):
                return {"claimed": True, "claim_token": claim_token, "run": _run_summary(current)}
        if current.status == "running" and current.attempt_count >= current.max_attempts:
            expired = await db.execute(
                update(ScheduledJobRun)
                .where(
                    ScheduledJobRun.id == run_id,
                    ScheduledJobRun.status == "running",
                    ScheduledJobRun.lease_expires_at <= now,
                )
                .values(status="failed", completed_at=now, lease_expires_at=None, updated_at=now)
                .returning(ScheduledJobRun.id)
            )
            if expired.scalar_one_or_none() is not None:
                await db.execute(
                    update(ScheduledJobAttempt)
                    .where(
                        ScheduledJobAttempt.run_id == run_id,
                        ScheduledJobAttempt.attempt_number == current.current_attempt,
                        ScheduledJobAttempt.status == "running",
                    )
                    .values(status="lease_expired", error_code="lease_expired", finished_at=now)
                )
                await db.commit()
                current = await db.get(ScheduledJobRun, run_id)
            else:
                await db.rollback()
                current = await db.get(ScheduledJobRun, run_id)
        return {"claimed": False, "run": _run_summary(current)}

    previous_attempt = attempt_number - 1
    if previous_attempt > 0:
        await db.execute(
            update(ScheduledJobAttempt)
            .where(
                ScheduledJobAttempt.run_id == run_id,
                ScheduledJobAttempt.attempt_number == previous_attempt,
                ScheduledJobAttempt.status == "running",
            )
            .values(status="lease_expired", error_code="lease_expired", finished_at=now)
        )

    db.add(
        ScheduledJobAttempt(
            run_id=run_id,
            attempt_number=attempt_number,
            runner_id=runner_id,
            claim_token_hash=token_hash,
            status="running",
            started_at=now,
        )
    )
    await db.commit()
    current = await db.get(ScheduledJobRun, run_id)
    return {"claimed": True, "claim_token": claim_token, "run": _run_summary(current)}


async def claim_next_run(
    db: AsyncSession,
    runner_id: str,
    claim_token: str,
) -> dict[str, Any]:
    """Claim the oldest due read-only health run, including abandoned prior dates."""
    now = _utcnow()
    if not runner_id or len(runner_id) > 100:
        raise InvalidScheduledRun("runner_id must be between 1 and 100 characters")
    if not claim_token or len(claim_token) < 32 or len(claim_token) > 100:
        raise InvalidScheduledRun("claim_token must be between 32 and 100 characters")
    token_hash = hashlib.sha256(claim_token.encode("utf-8")).hexdigest()
    active_run_id = await db.scalar(
        select(ScheduledJobRun.id)
        .join(ScheduledJobAttempt, ScheduledJobAttempt.run_id == ScheduledJobRun.id)
        .where(
            ScheduledJobRun.job_name == JOB_DAILY_SERVICE_HEALTH,
            ScheduledJobRun.status == "running",
            ScheduledJobRun.claimed_by == runner_id,
            ScheduledJobRun.lease_expires_at > now,
            ScheduledJobAttempt.status == "running",
            ScheduledJobAttempt.claim_token_hash == token_hash,
        )
        .limit(1)
    )
    if active_run_id is not None:
        await db.rollback()
        return await claim_run(db, active_run_id, runner_id, claim_token)

    exhausted = await db.execute(
        update(ScheduledJobRun)
        .where(
            ScheduledJobRun.job_name == JOB_DAILY_SERVICE_HEALTH,
            ScheduledJobRun.status == "running",
            ScheduledJobRun.lease_expires_at <= now,
            ScheduledJobRun.attempt_count >= ScheduledJobRun.max_attempts,
        )
        .values(status="failed", completed_at=now, lease_expires_at=None, claimed_by=None, updated_at=now)
        .returning(ScheduledJobRun.id, ScheduledJobRun.current_attempt)
    )
    for run_id, attempt_number in exhausted.all():
        if attempt_number is not None:
            await db.execute(
                update(ScheduledJobAttempt)
                .where(
                    ScheduledJobAttempt.run_id == run_id,
                    ScheduledJobAttempt.attempt_number == attempt_number,
                    ScheduledJobAttempt.status == "running",
                )
                .values(status="lease_expired", error_code="attempts_exhausted", finished_at=now)
            )
    await db.commit()

    ready = or_(
        and_(
            ScheduledJobRun.status.in_(("queued", "retry_wait")),
            or_(ScheduledJobRun.next_attempt_at.is_(None), ScheduledJobRun.next_attempt_at <= now),
        ),
        and_(ScheduledJobRun.status == "running", ScheduledJobRun.lease_expires_at <= now),
    )
    candidates = await db.scalars(
        select(ScheduledJobRun.id)
        .where(
            ScheduledJobRun.job_name == JOB_DAILY_SERVICE_HEALTH,
            ScheduledJobRun.dry_run.is_(True),
            ScheduledJobRun.attempt_count < ScheduledJobRun.max_attempts,
            ready,
        )
        .order_by(ScheduledJobRun.created_at, ScheduledJobRun.id)
        .limit(10)
    )
    candidate_ids = list(candidates)
    await db.rollback()
    for candidate_id in candidate_ids:
        claim = await claim_run(db, candidate_id, runner_id, claim_token)
        if claim.get("claimed"):
            return claim
    return {"claimed": False, "run": None}


async def finish_run(
    db: AsyncSession,
    run_id: int,
    claim_token: str,
    outcome: str,
    result: dict[str, Any],
    error_code: str | None = None,
) -> dict[str, Any]:
    """Finish the current attempt; failures receive bounded delayed retries."""
    if outcome not in {"succeeded", "failed"}:
        raise InvalidScheduledRun("outcome must be succeeded or failed")
    if error_code is not None and not _ERROR_CODE.fullmatch(error_code):
        raise InvalidScheduledRun("error_code must contain lowercase letters, digits, or underscores")

    clean_result = _serialize_result(result)
    now = _utcnow()
    run = await db.get(ScheduledJobRun, run_id)
    if run is None:
        raise ScheduledRunNotFound("scheduled run not found")
    if run.current_attempt is None:
        raise ScheduledRunConflict("scheduled run has no active attempt")
    attempt = await db.scalar(
        select(ScheduledJobAttempt).where(
            ScheduledJobAttempt.run_id == run_id,
            ScheduledJobAttempt.attempt_number == run.current_attempt,
        )
    )
    if attempt is None:
        raise ScheduledRunConflict("active attempt record is missing")

    provided_hash = hashlib.sha256(claim_token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(attempt.claim_token_hash, provided_hash):
        raise ScheduledRunConflict("invalid claim token")
    if attempt.status != "running":
        prior_outcome_matches = (
            (outcome == "succeeded" and attempt.status == "succeeded")
            or (outcome == "failed" and attempt.status in {"retry_scheduled", "failed"})
        )
        if prior_outcome_matches and attempt.result == clean_result and attempt.error_code == error_code:
            return {"run": _run_summary(run), "attempt": _attempt_summary(attempt), "idempotent": True}
        raise ScheduledRunConflict("attempt is no longer active")
    if run.status != "running" or run.current_attempt != attempt.attempt_number:
        raise ScheduledRunConflict("claim is no longer current")

    success = outcome == "succeeded"
    retrying = not success and attempt.attempt_number < run.max_attempts
    delay_seconds = min(60 * (2 ** (attempt.attempt_number - 1)), 300) if retrying else None
    run_status = "completed" if success else "retry_wait" if retrying else "failed"
    attempt_status = "succeeded" if success else "retry_scheduled" if retrying else "failed"

    update_attempt = await db.execute(
        update(ScheduledJobAttempt)
        .where(
            ScheduledJobAttempt.id == attempt.id,
            ScheduledJobAttempt.status == "running",
            ScheduledJobAttempt.claim_token_hash == provided_hash,
        )
        .values(
            status=attempt_status,
            finished_at=now,
            error_code=error_code,
            result=clean_result,
        )
        .returning(ScheduledJobAttempt.id)
    )
    if update_attempt.scalar_one_or_none() is None:
        await db.rollback()
        raise ScheduledRunConflict("attempt was already completed")

    update_run = await db.execute(
        update(ScheduledJobRun)
        .where(
            ScheduledJobRun.id == run_id,
            ScheduledJobRun.status == "running",
            ScheduledJobRun.current_attempt == attempt.attempt_number,
        )
        .values(
            status=run_status,
            lease_expires_at=None,
            claimed_by=None,
            next_attempt_at=now + timedelta(seconds=delay_seconds) if delay_seconds else None,
            completed_at=now if not retrying else None,
            updated_at=now,
        )
        .returning(ScheduledJobRun.id)
    )
    if update_run.scalar_one_or_none() is None:
        await db.rollback()
        raise ScheduledRunConflict("run state changed before completion")

    await db.commit()
    await db.refresh(run)
    await db.refresh(attempt)
    return {
        "run": _run_summary(run),
        "attempt": _attempt_summary(attempt),
        "idempotent": False,
        "retry_after_seconds": delay_seconds,
    }


async def get_run(db: AsyncSession, run_id: int) -> dict[str, Any]:
    run = await db.scalar(
        select(ScheduledJobRun)
        .where(ScheduledJobRun.id == run_id)
        .execution_options(populate_existing=True)
    )
    if run is None:
        raise ScheduledRunNotFound("scheduled run not found")
    attempts = await db.scalars(
        select(ScheduledJobAttempt)
        .where(ScheduledJobAttempt.run_id == run_id)
        .order_by(ScheduledJobAttempt.attempt_number)
    )
    return {"run": _run_summary(run), "attempts": [_attempt_summary(row) for row in attempts]}