# VIT Network System Upgrade Roadmap

_Last updated: 2026-09-22_

## Verified Baseline

- VIT Network `/health`: HTTP 200, database connected, 13 models loaded.
- VIT Network `/ping`: HTTP 200.
- VIT AI `/health`: HTTP 200, 16 models loaded.
- Tachyon `/health`: HTTP 200, database and Redis connected, 4 providers active.
- VIT Chain `/health`: HTTP 200 but degraded: database disconnected, block height `0`, active validators `0`.
- Frontend typecheck, production build, and 5 Playwright smoke tests pass.
- Deployed admin login using the repository `.env` credential pair returned HTTP 401; credentials must be reconciled with the deployed environment before authenticated production verification can continue.

## Sprint 1: Runtime Safety and Observability

Status: in progress

- [x] Retain and cancel the Tachyon verification task during lifespan shutdown.
- [x] Fail closed when emergency-control state cannot be read for controlled operations.
- [x] Register static and SPA routes before direct-script Uvicorn startup.
- [ ] Add lifespan tests for startup cancellation and worker shutdown.
- [ ] Add a structured readiness reason when the database or Redis is unavailable.
- [ ] Ensure production CORS has an explicit non-wildcard allowlist when credentials are enabled.

Acceptance: startup and shutdown leave no background tasks behind; controlled financial and prediction operations return `503` when safety state is unavailable; `/ready` explains the failing dependency.

## Sprint 2: VIT Chain Recovery

Status: blocked by deployed database connectivity

- [ ] Verify production `DATABASE_URL`, network access, migrations, and connection limits.
- [ ] Run `alembic upgrade heads` against the VIT Chain production database.
- [ ] Confirm genesis initialization is idempotent and produces block height `0` only before first block creation.
- [ ] Restore chain-state persistence and verify `/health`, recent blocks, transactions, and validator status.
- [ ] Add automated chain database backup and restore verification.
- [ ] Add a deployment smoke test that fails when `db_connected=false` or block height unexpectedly resets.

Acceptance: chain health reports database connected, a nonzero persisted chain state exists, and explorer endpoints return live records.

## Sprint 3: Authenticated Ecosystem Verification

Status: blocked by credential mismatch

- [ ] Reconcile the admin account and credential source between `.env`, deployment secrets, and production database.
- [ ] Verify browser login, `/api/auth/me`, admin health, metrics, feature flags, and audit views.
- [ ] Verify developer API-key creation, authentication, billing/quota behavior, and revoked-key rejection.
- [ ] Verify VIT Chain, Tachyon, AI, wallet, predictions, and notifications from an authenticated browser session.
- [ ] Add a Playwright project for deployed smoke tests with secrets injected through CI environment variables.

Acceptance: login succeeds without token leakage, admin-only endpoints authorize correctly, and each ecosystem surface reports an actionable status.

## Sprint 4: Contract and Regression Hardening

- [ ] Add API contract tests for health, readiness, authentication, developer, chain, and storage endpoints.
- [ ] Add tests for emergency-control database outage behavior.
- [ ] Add tests that unknown API paths return JSON `404`, not SPA HTML.
- [ ] Remove duplicate or ambiguous accessible names from login controls to improve browser automation and accessibility.
- [ ] Run full backend tests under the supported Python version and publish a release readiness report.

Acceptance: CI runs static checks, backend tests, frontend build, local browser smoke tests, and deploy smoke tests with no unreviewed warnings.

## Release Gates

1. No high-severity runtime or authorization findings remain open.
2. VIT Chain database connectivity and persisted state are restored.
3. Admin and developer authenticated browser flows pass in the deployed environment.
4. Readiness and health endpoints distinguish healthy, starting, degraded, and unavailable states.
5. A rollback procedure and verified database backup exist before the next production deployment.
