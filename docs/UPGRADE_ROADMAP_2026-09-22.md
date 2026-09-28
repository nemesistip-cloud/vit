# VIT Network System Upgrade Roadmap

_Last updated: 2026-09-28_

## Verified Baseline

_Live checks performed 2026-09-28; health of services not listed below was not rechecked._

- VIT Chain `/health`: HTTP 200, `db_connected=true`, block height `26322`, active validators `1`.
- VIT Chain `/api/status` and `/api/blocks?limit=1`: HTTP 200 with persisted chain data.
- VIT Chain GET `/api/txs?limit=1` and `/api/metrics`: HTTP 200 after deployment `70df489`; chain health is healthy with persisted block height `26388` and one active validator.
- VIT Network gateway: Render metadata reports deployment `7b45be8` as live, but `/ping` timed out from the verification environment. Admin login and authenticated checks could not be completed because the gateway did not respond.
- VIT AI, Tachyon, and frontend checks passed in the 2026-09-22 baseline; they were not rechecked on 2026-09-28.

## Sprint 1: Runtime Safety and Observability

Status: in progress

- [x] Retain and cancel the Tachyon verification task during lifespan shutdown.
- [x] Fail closed when emergency-control state cannot be read for controlled operations.
- [x] Register static and SPA routes before direct-script Uvicorn startup.
- [ ] Add lifespan tests for startup cancellation and worker shutdown.
- [x] Add structured readiness diagnostics when the database or Redis is unavailable; deployed in `ddae50d` and verified live.
- [ ] Ensure production CORS has an explicit non-wildcard allowlist when credentials are enabled.

Acceptance: startup and shutdown leave no background tasks behind; controlled financial and prediction operations return `503` when safety state is unavailable; `/ready` explains the failing dependency.

## Sprint 2: VIT Chain Recovery

Status: partially unblocked; chain database connectivity and persisted state are currently healthy, but API and recovery gates remain open

- [ ] Verify production migration state, backup coverage, and connection limits.
- [ ] Run `alembic upgrade heads` against the VIT Chain production database.
- [ ] Confirm genesis initialization is idempotent and produces block height `0` only before first block creation.
- [x] Confirm live chain database connectivity, nonzero persisted height, and recent block reads.
- [x] Deploy and verify GET `/api/txs` and `/api/metrics` on VIT Chain.
- [ ] Deploy and verify the gateway's external transaction, block, and metrics reads against the standalone chain.
- [ ] Add automated chain database backup and restore verification.
- [ ] Add a deployment smoke test that fails when `db_connected=false` or block height unexpectedly resets.

Acceptance: chain health reports database connected, a nonzero persisted chain state exists, and explorer endpoints return live records.

## Sprint 3: Authenticated Ecosystem Verification

Status: blocked by gateway reachability; deployed admin credentials remain unverified

- [ ] Restore gateway reachability, then verify the deployed admin account and credential source.
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
