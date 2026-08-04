# Phase 1 Findings — Initial Audit

Date: 2026-08-04

## Summary

This is an initial inventory from the Phase 1 audit and first test run.

## Critical Issues (blockers)

1. Alembic migrations not applied to runtime DBs — production historically missed `22c85e91a8d9_add_remaining_module_tables` (docs/VIT_PLATFORM_AUDIT_v6.0.md). Tests show many `sqlite3.OperationalError: no such table` failures.
   - Files: `alembic/versions/*`, `scripts/run_migrations.py`, `scripts/init_db.py`, `scripts/start_production.sh`
   - Impact: Kernel stuck in STARTING; many 500s in production and failing tests locally.

2. Redis configuration and resilience.
   - Files: `app/core/redis.py`, `app/core/persistence/cache.py`, many modules
   - Observations: code includes fakeredis fallback but several services log `redis: not_configured_or_disconnected` in BUG_LIST.md. Render env must set `REDIS_URL`.

3. Tests failing (98 failed, 325 passed). Majority fail due to DB schema missing; other failures include rate-limiter returning 429 and missing lifecycle attributes.
   - Action: Ensure test DB schema creation during test setup (Alembic or Base.metadata.create_all for sqlite test DBs).

4. start_production.sh / migration runner swallows migration failures.
   - Files: `scripts/start_production.sh`, `scripts/run_migrations.py`
   - Impact: Production may boot with incomplete schema.

5. Duplicate OpenAPI operation IDs in Tachyon routers (warnings).
   - Files: `tachyon/api/router.py`, `tachyon/core/s3_compat.py`

## Medium Issues (priority after blockers)

- Many `TODO`/`PLACEHOLDER` occurrences across backend and frontend; inventory available via search results.
- Frontend build-time envs `VITE_*` baked in `render.yaml` — moving hosts requires updates.
- Some lifecycle/orchestrator attributes missing (`LifecycleManager.state_machines`) causing tests to fail.

## Recommended Immediate Next Steps

1. Fix migration story (high priority): ensure migrations run reliably in production and CI; add idempotent, test-friendly path (allow alembic to run against sqlite test DB or create tables from models in tests).
2. Update `start_production.sh` to fail loudly on migration errors so deploys don't continue with broken schema.
3. Add a CI job to run `alembic upgrade heads` against a test DB or run `scripts/run_migrations.py` during CI before tests.
4. Ensure `REDIS_URL` is set in Render for all services; add a health-check fallback that allows partial degraded mode without 429.
5. Triage and assign `TODO/FIXME` items by impact (migrations, auth, payments, blockchain) and create tracked PRs.

## Next action I'm taking

- Add a high-priority todo to fix migrations and re-run tests locally to validate. 
