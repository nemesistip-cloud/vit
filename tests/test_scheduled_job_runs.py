from __future__ import annotations

import asyncio
import importlib.util
import secrets
from datetime import timedelta
from pathlib import Path

import pytest
import httpx
from fastapi import FastAPI
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from fastapi import HTTPException

from app.api.routes.scheduled_jobs import _require_scheduler_token
from app.api.routes.scheduled_jobs import router as scheduled_jobs_router
from app.db.database import get_db
from app.db.models import ScheduledJobAttempt, ScheduledJobRun
from app.services import scheduled_job_runs as jobs

_runner_spec = importlib.util.spec_from_file_location(
    "staging_health_runner",
    Path(__file__).resolve().parents[1] / "scripts" / "run_staging_scheduled_health.py",
)
assert _runner_spec is not None and _runner_spec.loader is not None
_runner = importlib.util.module_from_spec(_runner_spec)
_runner_spec.loader.exec_module(_runner)
_schedule_key = _runner._schedule_key
_staging_base_url = _runner._staging_base_url


@pytest.fixture
async def job_sessions(tmp_path):
    database_path = tmp_path / "scheduled-jobs.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    async with engine.begin() as connection:
        await connection.run_sync(ScheduledJobRun.__table__.create)
        await connection.run_sync(ScheduledJobAttempt.__table__.create)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _enqueue(sessions, key="2026-10-28"):
    async with sessions() as db:
        return await jobs.enqueue_daily_service_health(db, key)


async def _claim(sessions, run_id, runner_id="test-runner", claim_token=None):
    async with sessions() as db:
        return await jobs.claim_run(db, run_id, runner_id, claim_token or secrets.token_urlsafe(32))


async def _claim_next(sessions, runner_id="test-runner", claim_token=None):
    async with sessions() as db:
        return await jobs.claim_next_run(db, runner_id, claim_token or secrets.token_urlsafe(32))


async def _finish(sessions, run_id, token, outcome, error_code=None):
    async with sessions() as db:
        return await jobs.finish_run(
            db,
            run_id,
            token,
            outcome,
            {"mode": "read_only_dry_run"},
            error_code,
        )


async def _make_retry_due(sessions, run_id):
    async with sessions.begin() as db:
        await db.execute(
            update(ScheduledJobRun)
            .where(ScheduledJobRun.id == run_id)
            .values(next_attempt_at=jobs._utcnow() - timedelta(seconds=1))
        )


@pytest.mark.asyncio
async def test_weekly_enqueue_is_idempotent(job_sessions):
    first, first_created = await _enqueue(job_sessions)
    duplicate, duplicate_created = await _enqueue(job_sessions)

    assert first_created is True
    assert duplicate_created is False
    assert first.id == duplicate.id
    assert duplicate.dry_run is True
    assert duplicate.status == "queued"


@pytest.mark.asyncio
async def test_concurrent_claim_has_exactly_one_winner(job_sessions):
    run, _ = await _enqueue(job_sessions)
    claims = await asyncio.gather(
        _claim(job_sessions, run.id, "runner-a"),
        _claim(job_sessions, run.id, "runner-b"),
    )

    assert sum(claim["claimed"] for claim in claims) == 1
    winner = next(claim for claim in claims if claim["claimed"])
    assert len(winner["claim_token"]) >= 32
    assert winner["run"]["attempt_count"] == 1


@pytest.mark.asyncio
async def test_same_claim_request_can_be_retried_after_lost_response(job_sessions):
    run, _ = await _enqueue(job_sessions)
    token = "stable-claim-request-token-0123456789"
    first = await _claim(job_sessions, run.id, "same-runner", token)
    repeated = await _claim(job_sessions, run.id, "same-runner", token)

    assert first["claimed"] is True
    assert repeated["claimed"] is True
    assert repeated["claim_token"] == token
    assert repeated["run"]["attempt_count"] == 1


@pytest.mark.asyncio
async def test_success_and_completion_retry_are_idempotent(job_sessions):
    run, _ = await _enqueue(job_sessions)
    claim = await _claim(job_sessions, run.id)

    first = await _finish(job_sessions, run.id, claim["claim_token"], "succeeded")
    repeated = await _finish(job_sessions, run.id, claim["claim_token"], "succeeded")
    async with job_sessions() as db:
        recorded = await jobs.get_run(db, run.id)

    assert first["run"]["status"] == "completed"
    assert repeated["idempotent"] is True
    assert len(recorded["attempts"]) == 1
    assert recorded["attempts"][0]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_retry_budget_is_bounded_and_history_is_retained(job_sessions):
    run, _ = await _enqueue(job_sessions)
    for number in range(1, jobs.MAX_ATTEMPTS + 1):
        claim = await _claim(job_sessions, run.id, f"runner-{number}")
        assert claim["claimed"] is True
        finished = await _finish(
            job_sessions,
            run.id,
            claim["claim_token"],
            "failed",
            "health_check_failed",
        )
        expected = "retry_wait" if number < jobs.MAX_ATTEMPTS else "failed"
        assert finished["run"]["status"] == expected
        if number < jobs.MAX_ATTEMPTS:
            await _make_retry_due(job_sessions, run.id)

    async with job_sessions() as db:
        history = await jobs.get_run(db, run.id)
    assert history["run"]["attempt_count"] == jobs.MAX_ATTEMPTS
    assert [attempt["status"] for attempt in history["attempts"]] == [
        "retry_scheduled",
        "retry_scheduled",
        "failed",
    ]
    exhausted = await _claim(job_sessions, run.id)
    assert exhausted["claimed"] is False
    assert exhausted["run"]["status"] == "failed"


@pytest.mark.asyncio
async def test_expired_lease_is_reclaimed_and_previous_attempt_recorded(job_sessions):
    run, _ = await _enqueue(job_sessions)
    first = await _claim(job_sessions, run.id, "runner-lost")
    async with job_sessions.begin() as db:
        await db.execute(
            update(ScheduledJobRun)
            .where(ScheduledJobRun.id == run.id)
            .values(lease_expires_at=jobs._utcnow() - timedelta(seconds=1))
        )

    recovered = await _claim(job_sessions, run.id, "runner-recovery")
    assert recovered["claimed"] is True
    assert recovered["run"]["attempt_count"] == 2
    await _finish(job_sessions, run.id, recovered["claim_token"], "succeeded")

    async with job_sessions() as db:
        history = await jobs.get_run(db, run.id)
    assert history["attempts"][0]["status"] == "lease_expired"
    assert history["attempts"][1]["status"] == "succeeded"
    with pytest.raises(jobs.ScheduledRunConflict):
        await _finish(job_sessions, run.id, first["claim_token"], "succeeded")


@pytest.mark.asyncio
async def test_claim_next_recovers_oldest_expired_prior_date(job_sessions):
    old_run, _ = await _enqueue(job_sessions, "2026-10-27")
    first = await _claim(job_sessions, old_run.id, "runner-lost")
    await _enqueue(job_sessions, "2026-10-28")
    async with job_sessions.begin() as db:
        await db.execute(
            update(ScheduledJobRun)
            .where(ScheduledJobRun.id == old_run.id)
            .values(lease_expires_at=jobs._utcnow() - timedelta(seconds=1))
        )

    recovered = await _claim_next(job_sessions, "runner-recovery")
    assert recovered["claimed"] is True
    assert recovered["run"]["id"] == old_run.id
    assert recovered["run"]["attempt_count"] == 2
    await _finish(job_sessions, old_run.id, recovered["claim_token"], "succeeded")
    assert len(first["claim_token"]) >= 32


@pytest.mark.asyncio
async def test_claim_next_retry_returns_same_live_claim_after_lost_response(job_sessions):
    await _enqueue(job_sessions)
    token = "stable-claim-next-token-0123456789"
    first = await _claim_next(job_sessions, "same-runner", token)
    repeated = await _claim_next(job_sessions, "same-runner", token)

    assert first["claimed"] is True
    assert repeated["claimed"] is True
    assert repeated["run"]["id"] == first["run"]["id"]
    assert repeated["run"]["attempt_count"] == 1


@pytest.mark.asyncio
async def test_schedule_key_and_result_size_are_validated(job_sessions):
    async with job_sessions() as db:
        with pytest.raises(jobs.InvalidScheduledRun):
            await jobs.enqueue_daily_service_health(db, "2026-13-40")
    with pytest.raises(jobs.InvalidScheduledRun):
        jobs._serialize_result({"payload": "x" * (jobs.MAX_RESULT_BYTES + 1)})


def test_scheduler_api_fails_closed_when_token_is_unconfigured(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("GITHUB_SCHEDULER_TOKEN", raising=False)

    with pytest.raises(HTTPException) as error:
        _require_scheduler_token("untrusted")

    assert error.value.status_code == 503


def test_scheduler_api_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("GITHUB_SCHEDULER_TOKEN", "configured-token")

    with pytest.raises(HTTPException) as error:
        _require_scheduler_token("wrong-token")

    assert error.value.status_code == 401


def test_scheduler_api_refuses_production_even_with_token(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("GITHUB_SCHEDULER_TOKEN", "configured-token")

    with pytest.raises(HTTPException) as error:
        _require_scheduler_token("configured-token")

    assert error.value.status_code == 503


def test_runner_rejects_non_staging_service_host(monkeypatch):
    monkeypatch.setenv("STAGING_GATEWAY_URL", "https://vitnetwork.example.com")

    with pytest.raises(RuntimeError, match="staging hostname"):
        _staging_base_url("STAGING_GATEWAY_URL")


def test_runner_accepts_staging_host_and_iso_week_key(monkeypatch):
    monkeypatch.setenv("STAGING_GATEWAY_URL", "https://vitnetwork-staging.example.com")
    monkeypatch.delenv("SCHEDULE_KEY", raising=False)

    assert _staging_base_url("STAGING_GATEWAY_URL") == "https://vitnetwork-staging.example.com"
    assert jobs._DAY_KEY.fullmatch(_schedule_key())


def test_health_probe_rejects_degraded_http_200(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return b'{"status":"degraded","database":"disconnected"}'

    monkeypatch.setattr(_runner.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    monkeypatch.setattr(_runner.time, "sleep", lambda _seconds: None)

    probe = _runner._probe("gateway", "https://gateway-staging.example.com", "/health")

    assert probe["status"] == "degraded"


def _configure_runner_env(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("STAGING_GATEWAY_URL", "https://vitnetwork-staging.example.com")
    monkeypatch.setenv("STAGING_VIT_AI_URL", "https://vit-ai-staging.example.com")
    monkeypatch.setenv("STAGING_VIT_CHAIN_URL", "https://vit-chain-staging.example.com")
    monkeypatch.setenv("STAGING_VIT_STORAGE_URL", "https://vit-storage-staging.example.com")
    monkeypatch.setenv("STAGING_GITHUB_SCHEDULER_TOKEN", "test-token-never-logged")
    monkeypatch.setenv("GITHUB_RUN_ID", "run-123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setattr(_runner.time, "sleep", lambda _seconds: None)


def test_runner_completes_green_read_only_audit(monkeypatch):
    _configure_runner_env(monkeypatch)
    api_calls = []

    def fake_api(_base, _token, path, payload=None, **_kwargs):
        api_calls.append((path, payload))
        if path == "/runs":
            return {"created": True, "run": {"id": 72}}
        if path == "/runs/claim-next":
            return {"claimed": True, "claim_token": "c" * 43, "run": {"id": 71}}
        if path.endswith("/finish"):
            return {"run": {"status": "completed"}}
        raise AssertionError(f"unexpected API path {path}")

    probes = []

    def fake_probe(name, _base, _path):
        probes.append(name)
        return {"service": name, "status": "http_200", "latency_ms": 4}

    monkeypatch.setattr(_runner, "_api_request", fake_api)
    monkeypatch.setattr(_runner, "_probe", fake_probe)

    assert _runner.main() == 0
    assert probes == ["gateway", "ai", "chain", "storage"]
    assert api_calls[0][1] == {"schedule_key": _schedule_key(), "dry_run": True}
    assert any(path == "/runs/71/finish" for path, _payload in api_calls)


def test_runner_records_failure_then_recovers_with_next_attempt(monkeypatch):
    _configure_runner_env(monkeypatch)
    claim_count = 0
    finish_outcomes = []

    def fake_api(_base, _token, path, payload=None, **_kwargs):
        nonlocal claim_count
        if path == "/runs":
            return {"created": True, "run": {"id": 72}}
        if path == "/runs/claim-next":
            claim_count += 1
            return {
                "claimed": True,
                "claim_token": str(claim_count) * 43,
                "run": {"id": 72, "attempt_count": claim_count},
            }
        if path.endswith("/finish"):
            finish_outcomes.append(payload["outcome"])
            if len(finish_outcomes) == 1:
                return {"run": {"status": "retry_wait"}, "retry_after_seconds": 1}
            return {"run": {"status": "completed"}}
        raise AssertionError(f"unexpected API path {path}")

    probe_cycle = 0

    def fake_probe(name, _base, _path):
        nonlocal probe_cycle
        if name == "gateway":
            probe_cycle += 1
        status = "http_503" if probe_cycle == 1 and name == "ai" else "http_200"
        return {"service": name, "status": status, "latency_ms": 4}

    monkeypatch.setattr(_runner, "_api_request", fake_api)
    monkeypatch.setattr(_runner, "_probe", fake_probe)

    assert _runner.main() == 0
    assert claim_count == 2
    assert finish_outcomes == ["failed", "succeeded"]


@pytest.mark.asyncio
async def test_http_contract_auth_enqueue_claim_finish_and_history(job_sessions, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("GITHUB_SCHEDULER_TOKEN", "staging-only-token")
    app = FastAPI()
    app.include_router(scheduled_jobs_router)

    async def override_get_db():
        async with job_sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    headers = {"X-GitHub-Scheduler-Token": "staging-only-token"}

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        denied = await client.post(
            "/api/v1/scheduled-jobs/runs",
            json={"schedule_key": "2026-10-28", "dry_run": True},
            headers={"X-GitHub-Scheduler-Token": "incorrect"},
        )
        assert denied.status_code == 401

        created = await client.post(
            "/api/v1/scheduled-jobs/runs",
            json={"schedule_key": "2026-10-28", "dry_run": True},
            headers=headers,
        )
        duplicate = await client.post(
            "/api/v1/scheduled-jobs/runs",
            json={"schedule_key": "2026-10-28", "dry_run": True},
            headers=headers,
        )
        assert created.status_code == 202
        assert duplicate.status_code == 202
        assert created.json()["created"] is True
        assert duplicate.json()["created"] is False
        run_id = created.json()["run"]["id"]
        assert duplicate.json()["run"]["id"] == run_id

        claim = await client.post(
            f"/api/v1/scheduled-jobs/runs/{run_id}/claim",
            json={"runner_id": "actions-run-42", "claim_token": secrets.token_urlsafe(32)},
            headers=headers,
        )
        assert claim.status_code == 200
        claim_token = claim.json()["claim_token"]

        finish_body = {
            "claim_token": claim_token,
            "outcome": "succeeded",
            "result": {"mode": "read_only_dry_run", "services": []},
        }
        finished = await client.post(
            f"/api/v1/scheduled-jobs/runs/{run_id}/finish",
            json=finish_body,
            headers=headers,
        )
        repeated_finish = await client.post(
            f"/api/v1/scheduled-jobs/runs/{run_id}/finish",
            json=finish_body,
            headers=headers,
        )
        history = await client.get(f"/api/v1/scheduled-jobs/runs/{run_id}", headers=headers)

        assert finished.status_code == 200
        assert finished.json()["run"]["status"] == "completed"
        assert repeated_finish.json()["idempotent"] is True
        assert len(history.json()["attempts"]) == 1
