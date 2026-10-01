# VIT Network System Upgrade Roadmap

_Last updated: 2026-10-01_

## Verified Baseline

_Live checks performed 2026-10-01; health of services not listed below was not rechecked._

- Gateway `/ping` and `/ready` returned HTTP 200 after one longer probe; an earlier 15-second probe timed out during cold start. `/health` and `/ready` reported the database and Redis connected, with 13 models loaded.
- The live OpenAPI document returned HTTP 200 and described 835 paths / 908 operations. These are contract entries, not a claim that every operation was individually exercised.
- Authenticated admin checks returned HTTP 200 for `/api/auth/me`, system health, system metrics, audit log, users, and config. The `/api/admin/config` response contained two rows and none of the nine UI feature-flag keys; the frontend now creates a missing flag on first toggle, but that change is local and has not been deployed or exercised against production.
- A sanitized read-only sweep of 18 live dashboard GET endpoints returned HTTP 200, including reliability, launch/emergency state, system health/metrics, users, KYC queue, wallet transactions, matches, validators, model registry, secret metadata, config, API keys, pending marketplace listings, training jobs, and audit log. Response contents were not dumped.
- The live subscription catalog returned `free`, `analyst`, `pro`, and `validator`, with monthly/yearly USD fields and feature maps. The previous UI rendered unrelated static tiers/prices and posted upgrades to the direct subscription mutation route instead of Paystack checkout. The local UI now maps the live schema, uses `/create-checkout`, validates the Paystack HTTPS host, and has error-state coverage; browser tests remain blocked by missing Chromium system libraries.
- VIT Chain gateway reads for status, recent blocks, and metrics returned HTTP 200; observed chain ID was `7764` and block height was `28728`.
- Genesis is intentionally preserved in `bootstrapping`: current stage 7, stages 1–7 completed, database and Redis available, and no failed live validations. It is not marked verified.
- Deployed `/api/admin/system/metrics` returned zero counters. Local middleware instrumentation and focused tests now emit Redis request, 5xx, and average-latency metrics; this code change is not yet deployed.
- Scheduled retraining previously looked for a nonexistent root manifest, parsed the manifest path as a JSON object rather than opening it, treated generated datasets as eligible, and reused the same output filename for ATP/WTA. Local changes correct the path/parser, exclude manifest entries marked ineligible, fail the job on training/upload failures, and generate per-dataset artifacts. Three focused cron tests pass; the scheduled workflow has not run with these changes.
- The public frontend has 49 page components and the deployed OpenAPI spec has 835 paths. This audit sampled high-risk admin, Genesis, chain, subscription, and background-job contracts; it did not execute every operation or re-verify AI/Tachyon.
- Browser-level page auditing is not complete: the targeted Admin/Subscription cases were discovered by Playwright but Chromium could not launch because `libatk-1.0.so.0` is missing from this non-root container. The deploy workflow and subscription changes therefore require CI/browser confirmation after release.

- VIT Chain `/health`: HTTP 200, `db_connected=true`, block height `26322`, active validators `1`.
- VIT Chain `/api/status` and `/api/blocks?limit=1`: HTTP 200 with persisted chain data.
- VIT Chain GET `/api/txs?limit=1` and `/api/metrics`: HTTP 200 after deployment `70df489`; chain health is healthy with persisted block height `26388` and one active validator.
- VIT AI and Tachyon were not rechecked in this audit. The frontend production build passed locally; browser automation remains blocked by missing Chromium system libraries.

## Sprint 1: Runtime Safety and Observability

Status: in progress

- [x] Retain and cancel the Tachyon verification task during lifespan shutdown.
- [x] Fail closed when emergency-control state cannot be read for controlled operations.
- [x] Register static and SPA routes before direct-script Uvicorn startup.
- [x] Test kernel-boot and watchdog cancellation during lifespan shutdown.
- [ ] Add shutdown coverage for the Tachyon worker and schedulers.
- [x] Add structured readiness diagnostics when the database or Redis is unavailable; deployed in `ddae50d` and verified live.
- [x] Require an explicit non-wildcard production CORS allowlist; deployed in `0ef609e` and verified with allowed/untrusted preflight origins.

Acceptance: startup and shutdown leave no background tasks behind; controlled financial and prediction operations return `503` when safety state is unavailable; `/ready` explains the failing dependency.

## Sprint 2: VIT Chain Recovery

Status: partially unblocked; chain database connectivity and persisted state are currently healthy, but API and recovery gates remain open

- [ ] Verify production migration state, backup coverage, and connection limits.
- [ ] Run `alembic upgrade heads` against the VIT Chain production database.
- [ ] Confirm genesis initialization is idempotent and produces block height `0` only before first block creation.
- [x] Confirm live chain database connectivity, nonzero persisted height, and recent block reads.
- [x] Deploy and verify GET `/api/txs` and `/api/metrics` on VIT Chain.
- [x] Deploy and verify the gateway's external transaction, block, and metrics reads against the standalone chain; live reads passed on 2026-10-01.
- [ ] Add automated chain database backup and restore verification.
- [ ] Add a deployment smoke test that fails when `db_connected=false` or block height unexpectedly resets.

Acceptance: chain health reports database connected, a nonzero persisted chain state exists, and explorer endpoints return live records.

## Sprint 3: Authenticated Ecosystem Verification

Status: gateway and admin API access verified; Genesis intentionally remains in bootstrapping; full browser and ecosystem verification remain open

- [x] Restore gateway reachability; `/ping` and `/ready` returned HTTP 200 on 2026-10-01.
- [x] Verify the deployed admin account; login returns `super_admin` after the missing Render env vars were added without replacing existing values.
- [x] Verify authenticated `/api/auth/me`, admin health, metrics, audit-log, and users read endpoints on 2026-10-01.
- [ ] Verify browser login and admin feature-flag views; first-use feature-flag persistence fix is not deployed yet.
- [ ] Verify subscription catalog and Paystack checkout in a real browser; the UI now follows the live API schema, but Playwright cannot launch in this container because `libatk-1.0.so.0` is unavailable.
- [ ] Verify developer API-key creation, authentication, billing/quota behavior, and revoked-key rejection.
- [ ] Verify VIT Chain, Tachyon, AI, wallet, predictions, and notifications from an authenticated browser session.
- [x] Add an opt-in deployed Playwright smoke project; admin credentials are read from `VIT_SMOKE_EMAIL` and `VIT_SMOKE_PASSWORD` only when `VIT_RUN_AUTHENTICATED_SMOKE=true`, and traces are disabled.

Run public deployed checks with `VIT_DEPLOYED_BASE_URL` set. Authenticated CI runs must additionally set `VIT_RUN_AUTHENTICATED_SMOKE=true`, `VIT_SMOKE_EMAIL`, and `VIT_SMOKE_PASSWORD`.

Acceptance: login succeeds without token leakage, admin-only endpoints authorize correctly, and each ecosystem surface reports an actionable status.

## Sprint 4: Contract and Regression Hardening

- [ ] Deploy Redis-backed request, 5xx, and average-latency instrumentation; local middleware regression tests pass, but live metrics remain unverified.
- [ ] Deploy dependency-aware `/ready` checks in the Render keep-alive and deployment workflows; workflow YAML parses locally, but GitHub Actions has not run these changes.
- [ ] Ship the `[render-only]` release guard so Render-targeted commits do not also deploy the separate Cloud Run service; normal pushes and manual Cloud Run dispatch remain available.
- [ ] Deploy first-use feature-flag persistence and live subscription checkout fixes; frontend build passes, browser regressions are blocked on the local Chromium runtime.
- [ ] Run the corrected scheduled retraining job and verify artifact upload for each training-eligible dataset; synthetic NFL, EuroLeague, and rugby rows are excluded.
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
