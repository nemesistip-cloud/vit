# VIT Network System Upgrade Roadmap

_Last updated: 2026-10-20_

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

## Audit Update - 2026-10-20

### Verified and Implemented Locally

- Fixed `get_current_admin` and `get_optional_user` forwarding to pass `Request`, credentials, and database session in the declared `get_current_user` order. Two focused regression tests pass. This change is local and not deployed.
- Changed `get_val()` to prefer non-empty environment variables before lazily materialized config defaults. This prevents early module imports from capturing `dev-jwt-secret` or a local SQLite default when deployment environment values are present. Focused regression and auth/admin tests pass; production effective-config behavior is unverified and the change is not deployed.
- Changed the initial wallet bonus reference from a global constant to `welcome_bonus:<user_id>`, matching the global unique-reference constraint. A fresh in-memory SQLite integration check verified two users each receive one bonus and repeated wallet initialization is idempotent. This change is local and not deployed.
- Changed external PostgreSQL connections to use Python's default certificate- and hostname-verifying TLS context; local `helium`/loopback behavior is unchanged. The focused policy test passes. The workspace has no remote `DATABASE_URL`, so connection compatibility with Render PostgreSQL remains unverified; this change is local and not deployed.
- Restricted the ignored local `.env` file from mode `666` to `600`; no credential values were printed.
- Read-only Render API checks confirmed the configured API key authenticates, the current deployment is `live` on commit `1a9debc2e1bc`, and `RESET_USERS_ON_BOOT` is not configured.

### Baseline Evidence and Open Gaps

- Frontend `npm run build` passes TypeScript, Vite, and asset validation. Vite reports that `useAuth.ts` is both statically and dynamically imported, so the intended chunk split is ineffective.
- Initial backend baseline: 633 passed, 3 skipped, 16 deselected, 108 setup errors, and 2 wallet functional failures. After preserving the isolated `PYTHONPATH` for Alembic subprocesses and applying the regression fixes, the full non-live gate passes: 746 passed, 3 skipped, 16 deselected.
- Fixed the wallet functional test fixtures: funding references are unique per test, and minimum-stake config updates an existing seeded row. The wallet functional suite plus the welcome-bonus regression passes (21/21); one SQLAlchemy connection-cleanup warning remains.
- Focused config/auth/admin/RBAC tests pass (36/36), including the admin training lifecycle; odds-free prediction regressions pass (2/2); wallet plus welcome-bonus tests pass (21/21); the external PostgreSQL TLS policy test passes (1/1). These local checks use isolated SQLite and do not verify production database connectivity.
- Latest read-only live checks returned HTTP 200 only for gateway `/health`; `/ping` and `/ready` timed out. Chain, AI, and Tachyon had returned HTTP 200 in the earlier audit pass, but were not rechecked in this pass.
- Render's read-only Postgres inventory now lists one resource, `vitnetwork-recovery-20260919`, with status `suspended`, region `oregon`, free plan, and expiry `2026-10-19`. The service API masks `DATABASE_URL`, so the deployed database mapping and TLS compatibility could not be verified. The only verified logical export documented by the recovery runbook is dated `2026-09-18`; PITR reports `NOT_AVAILABLE`. No PostgreSQL archive is present in the workspace, and `POST /v1/postgres/{id}/export` returned HTTP 400 for the suspended resource. The user accepts possible data loss, but that does not recover the unavailable archive. The attempted `POST /v1/postgres` returned HTTP 404; Render's documented dashboard creation flow is not automatable from the current tool session. Do not cut over until a candidate is created through the dashboard and a restorable source is available.
- Browser verification remains unperformed: no browser executable/cache is available in this container, and `libatk-1.0.so.0` is absent. Do not claim browser or production workflow verification.
- `vit_chain/AUDIT.md` and `vit_chain/WAVE4_PRODUCTION_READINESS.md` contain materially conflicting implementation/readiness claims. Reconcile both against current code and reproducible tests before asserting protocol production readiness.
- The Render production deployment remains on the pre-audit commit; no deployment or production mutation was performed. Five untracked SQL backup artifacts appeared during test execution; their contents were not inspected or removed.

### Gap Register

| ID | Priority / status | Area and evidence | Next acceptance gate |
| --- | --- | --- | --- |
| CONFIG-01 | P1 / fixed locally | `get_val()` could access the config manager's lazy defaults before `load()` and ignore explicit deployment environment values, potentially selecting a development JWT secret or local SQLite URL. | Verify redacted effective settings and a read-only database query in staging; confirm migration state and backup before release. |
| AUTH-01 | P1 / fixed locally | `get_current_admin` passed arguments in the wrong order to `get_current_user`; active via the compatibility re-export. Focused tests pass. | Deploy only through an approved release; verify authenticated admin and non-admin routes in staging/browser. |
| WALLET-01 | P1 / fixed locally | New wallets reused the globally unique `welcome_bonus` reference. User-scoped references pass a two-user idempotency check. | Verify the existing production ledger schema and wallet creation in staging; do not backfill or change production balances as a test. |
| DB-01 | P1 / fixed locally, deployment unverified | External PostgreSQL TLS disabled certificate and hostname verification. Focused policy test passes; the workspace has no remote database URL. | Verify a read-only TLS connection against staging Render PostgreSQL before release. |
| DB-02 | P1 / blocked externally | Render's only listed Postgres resource is suspended and expired; `/ready` and `/ping` time out. PITR is unavailable, API export was rejected with HTTP 400, API create returned 404, and no archive is present. User approved possible data loss. | Create a Free candidate through the Render dashboard and provide a secure accessible export. The approval of loss does not make the missing export restorable; validate counts, mapping, TLS, and recovery before cutover. |
| QA-01 | P2 / fixed locally | The full non-live backend suite passes locally under Python 3.12 after preserving `PYTHONPATH` for the Alembic subprocess. | Confirm the repository CI workflow on supported Python 3.11 and retain its passing result as the release gate. |
| WEB-01 | P1 / open | Admin and developer browser flows are not verified; no browser executable is installed and the container lacks Chromium libraries. | Run authenticated browser smoke tests in CI or staging at desktop and mobile viewports. |
| CHAIN-01 | P1 / open | Chain audit documents disagree on whether core components exist and claim multi-node production readiness without current reproducible evidence. | Reconcile docs with code; verify migrations, persisted state, restore, and adversarial multi-node finality tests in isolation. |
| OPS-01 | P1 / open | Latest live `/health` returned 200 while `/ping` and `/ready` timed out; persisted-data readiness is not established. | Correlate Render logs with database state and require `/ready` to pass after recovery. |

### Next Priority

1. Restore the authoritative Render Postgres resource and verify mapping, read-only connectivity, and backup recovery before any deployment.
2. Verify the config precedence and external TLS policy against a healthy staging Render Postgres resource.
3. Verify admin authorization through a staging/browser flow with authenticated test credentials.
4. Reconcile the chain audit documents and verify chain persistence, migration state, backup/restore, and finality invariants in an isolated multi-node environment.
5. Remove short-key warnings from the test authentication configuration without weakening production secret validation.

## Release Gates

1. No high-severity runtime or authorization findings remain open.
2. VIT Chain database connectivity and persisted state are restored.
3. Admin and developer authenticated browser flows pass in the deployed environment.
4. Readiness and health endpoints distinguish healthy, starting, degraded, and unavailable states.
5. A rollback procedure and verified database backup exist before the next production deployment.
