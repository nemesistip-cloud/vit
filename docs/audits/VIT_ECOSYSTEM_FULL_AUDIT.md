# VIT Network Full Ecosystem Audit

- Audit date: 2026-10-17
- Continuation evidence recorded: 2026-10-17T02:57:26Z
- Repository revision: `903c940` (`main`)
- Initial worktree: `package-lock.json` already modified; that change was preserved.
- Audit status: local browser/runtime and Wave 1 integrity validation operational; current production requests blocked by Render cold start. Production workflows remain `NOT_VERIFIED`.

## Executive Summary

The repository builds and tests locally in an isolated Python 3.12 environment. Backend CI-selected tests, API/schema regressions, VIT Chain tests, a three-node local consensus test, Tachyon tests, and both frontend builds passed. The new settlement migration was also verified on PostgreSQL 17 against both an existing database containing a prediction and a fresh database. A local Uvicorn process served the repaired subscription and landing APIs.

Three defects/tooling issues have been addressed locally: the subscription router's missing `User` import; the migration chain's missing `predictions.was_correct` column; and the duplicate `/validators` route that caused signed-in users to receive the public shell. The stale Explorer npm lockfile was regenerated from its unchanged manifest. None of these local edits were deployed by this audit.

The host still lacks Chromium shared libraries, so no system packages were installed. A version-matched official Playwright container supplied Chromium 153.0.8010.12; a local page smoke passed and all 25 local Playwright tests passed. Fourteen distinct route patterns received local UI interaction coverage using test fixtures/mocked APIs. This does not verify their production backend workflows. Chromium reaches the canonical production URL but currently receives Render's branded HTTP 503 “Application loading / Service waking up” page. The latest same-commit deployment workflow had previously passed its readiness gate on attempt 9; this points to a later free-tier cold start, not evidence by itself of an application defect. Direct command-line API requests also encountered Cloudflare HTTP 429 challenge pages.

**Operational conclusion:** Wave 0's browser runtime is operational and the access behavior is characterized. The remaining production blocker is obtaining a warm, edge-approved service response and owner-side Render diagnostics; no Cloudflare protection was bypassed. Wave 1's migration and router fixes are implemented and validated locally, including PostgreSQL data preservation, but must not be deployed without the authorized release and backup/recovery process.

## Route Summary

The initial audit found 58 declarations, including two identical `/validators` entries. The duplicate was consolidated into one auth-aware route, leaving 57 current declarations (26 PublicShell, 30 authenticated-tree, one adaptive `/validators`; `*` is the not-found fallback). “Verified Working” here means a complete production workflow; local browser tests use fixtures and do not satisfy that bar.

| Module | Routes Discovered | Verified Working | Partial | Broken | Missing | Not Verified | Highest Severity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Public platform | 10 | 0 | 0 | 0 | 0 | 10 | P1, local config dependency fixed; deploy unknown |
| Developer hub | 1 | 0 | 0 | 0 | 0 | 1 | None confirmed |
| Prediction Intelligence | 10 | 0 | 0 | 0 | 0 | 10 | P1, local settlement-schema gap fixed; deploy unknown |
| Chain, governance, validators, marketplace | 8 | 0 | 0 | 0 | 0 | 8 | P2, `/validators` shell routing fixed locally; deploy unknown |
| Wallet and financial flows | 10 | 0 | 0 | 0 | 0 | 10 | P2, subscription router gap fixed; deploy unknown |
| Identity and settings | 6 | 0 | 0 | 0 | 0 | 6 | None confirmed |
| Workspace, analytics, administration | 11 | 0 | 0 | 0 | 0 | 11 | None confirmed |
| Not-found fallback | 1 | 0 | 0 | 0 | 0 | 1 | None confirmed |
| **Total** | **57** | **0** | **0** | **0** | **0** | **57** | **P1 local finding; production status unknown** |

`Verified Working = 0` means no full production workflow was verified; it does not mean routes are broken. The local Playwright suite passed 25 tests across 14 route patterns with mocked API responses. The remaining 43 route patterns were not visited in a browser, and none of the 57 current routes has production workflow evidence.

## Environment Report

- Runtime constraint: `requires-python = ">=3.11, <4.0"`; `.python-version` requests `3.12.13`. The available version was Python `3.12.3`; global Python was `3.14.2`.
- A project-local `.venv` was created from the available Python 3.12 interpreter. Ubuntu's `python3.12-venv` / `ensurepip` is absent, so pip was bootstrapped with the supported `python -m pip --python .venv/bin/python install pip` option. `.venv/` is now ignored by Git.
- Poetry `2.3.2` installed the lockfile dependencies and dev group. `poetry install --with dev` then failed only at root-package installation because Poetry could not discover a top-level `vit-network` package. The documented setuptools route, `.venv/bin/python -m pip install -e .`, succeeded. `pip check` reported no broken requirements.
- The frontend dependencies were already present. Local Node/npm were `v24.21.0` / `11.19.0`; CI config uses Node 20. The frontend production build and TypeScript compile succeeded.
- The stale Explorer `package-lock.json` was regenerated from its unchanged `package.json`; clean `npm ci --ignore-scripts` and the Explorer build now pass with Vite 7.3.7 and Tailwind 3.4.19. Root `package-lock.json` remains only the pre-existing user modification.
- Backend test commands must put `.venv/bin` on `PATH` as well as use `PYTHONPATH=backend:.`; otherwise test fixtures cannot find the Alembic executable. The first full pytest attempt had 101 fixture errors for that invocation mistake; rerunning with the activated venv passed.
- Local reproducible install sequence for this container:

  ```bash
  python3.12 -m venv .venv
  # If ensurepip is unavailable, use the already-created project venv:
  python -m venv --upgrade --without-pip .venv
  python -m pip --python .venv/bin/python install pip
  .venv/bin/python -m pip install 'poetry==2.3.2'
  .venv/bin/poetry install --with dev
  .venv/bin/python -m pip install -e .
  ```

  The first venv command requires the OS `python3.12-venv` package on a fresh copy of this image. For a repeat run here, retain the `.venv` and use the workaround lines. Do not use the global Python 3.14 for project test commands.
- No production `.env`, credentials, or mainnet operations were used. Local database work used disposable SQLite databases and a test-only Uvicorn configuration.
- Frontend lint remains explicitly blocked: the script exists, but no ESLint dependency or config exists, repository history contains no intended ESLint version, and CI runs Ruff plus TypeScript but no frontend lint. Choosing a version/ruleset would be a new policy decision, so no package or lockfile was invented.

### Browser Runtime

- Host Chromium launch still lacks `libatk-1.0.so.0`, `libatk-bridge2.0.so.0`, `libXcomposite.so.1`, `libXdamage.so.1`, `libXfixes.so.3`, `libXrandr.so.2`, `libgbm.so.1`, `libxkbcommon.so.0`, `libasound.so.2`, and `libatspi.so.0`; the unprivileged host was not modified.
- Resolved runtime: official image `mcr.microsoft.com/playwright:v1.63.0-noble`, Playwright package `1.63.0`, bundled Chromium `153.0.8010.12`. `docker pull mcr.microsoft.com/playwright:v1.63.0-noble` followed by `docker run --rm --ipc=host --volume "$PWD:/work:ro" --workdir /work ... node -e ...` launched Chromium, navigated a local test page (HTTP 200), found its heading, and reported zero page errors.
- The local browser suite ran with `docker run --rm --ipc=host --volume "$PWD:/work" --workdir /work mcr.microsoft.com/playwright:v1.63.0-noble ./node_modules/.bin/playwright test --config playwright.config.ts`; result: 25 passed. The app's dev proxy logged expected `ECONNREFUSED 127.0.0.1:8000` because no local backend was attached; covered API responses were fulfilled by test fixtures.
- Local browser screenshots: [Matches route](../../matches-tabs.png), [Admin route](../../admin-console-ux.png), [mobile Workspace route](../../authenticated-shell-mobile.png), [anonymous Validators](validators-public.png), and [signed-in Validators](validators-authenticated.png).

## Live Deployment and Browser

- Deployment URL source: README's Live app link and `render.yaml`; URL audited: `https://vitnetwork-nls4.onrender.com`.
- A real Playwright Chromium binary was downloaded and the repository's browser tests were attempted. Chromium exited before page creation because these shared libraries are missing: `libatk-1.0.so.0`, `libatk-bridge-2.0.so.0`, `libXcomposite.so.1`, `libXdamage.so.1`, `libXfixes.so.3`, `libXrandr.so.2`, `libgbm.so.1`, `libxkbcommon.so.0`, `libasound.so.2`, and `libatspi.so.0`.
- `npx playwright test --config playwright.config.ts`: 24 test cases failed at browser launch; no page assertions ran. No screenshots were captured.
- `VIT_DEPLOYED_BASE_URL=https://vitnetwork-nls4.onrender.com npx playwright test --config frontend/playwright.deployed.config.ts`: 1 read-only smoke test failed when `/ping` returned HTTP 503; 2 authenticated tests were skipped by the test's explicit credential gate. No credentials were supplied.
- Subsequent direct read-only requests to `/ping`, `/ready`, `/api/chain/status`, `/api/chain/recent-blocks?limit=1`, and `/api/chain/metrics` received Cloudflare HTTP 429 challenge pages. This is an edge response from this audit environment and does not establish whether the application itself is down.
- No live route was rendered. Desktop/tablet/mobile layout, console/network errors, service-worker/CDN behavior, authenticated routes, real persistence, and live data freshness are all `NOT_VERIFIED`.

## Feature and Integration Inventory

| Frontend route group | Backend/API families found in source | Persistence or service boundary | Audit state |
| --- | --- | --- | --- |
| `/`, `/platform`, `/ai`, `/storage`, `/status-page`, `/verification`, `/docs`, `/responsible-use`, `/roadmap`, `/about` | `/api/system/status`, `/api/system/health/summary`, `/api/config/public/*`, `/api/registry`, `/api/matches/*` | FastAPI, configured PostgreSQL/Redis, VIT AI and Tachyon URLs | UI not verified; local landing API verified after repair |
| `/developers` | `/api/developer/docs`, `/api/developer/keys`, `/api/developer/api-keys`, `/api/developer/webhooks`, `/api/developer/usage/*`, `/api/developer/git/*` | Developer module and persistence; webhook delivery not exercised | `NOT_VERIFIED` |
| `/matches`, `/matches/:id`, `/leaderboard`, `/predictions`, `/odds`, `/inplay`, `/accumulator`, `/rollover`, `/backtest`, `/bankroll` | `/api/matches/*`, `/api/predict/*`, `/api/predictions/*`, `/api/odds/compare`, `/api/results`, `/api/analytics/*` | Match/prediction models, ingestion and model services, external sports/odds providers | UI/live data `NOT_VERIFIED`; local settlement migration repaired |
| `/governance`, `/marketplace`, `/chain`, `/validators`, `/validators/:validatorId`, `/validators/:validatorId/:tab`, `/network/validators`, `/explorer` plus authenticated `/validators` | `/api/governance/*`, `/api/marketplace/*`, `/api/chain/*`, `/api/blockchain/*`, `/api/explorer/*` | Main API plus separately configured VIT Chain service | UI/live chain `NOT_VERIFIED`; local three-node test passed |
| `/subscription`, `/wallet`, `/defi`, `/genesis`, `/referral`, `/treasury`, `/vitcoin`, `/exchange`, `/vaults`, `/bridge` | `/api/subscription/*`, `/api/wallet/*`, `/api/defi/*`, `/api/genesis/*`, `/api/referral/*`, `/api/treasury/*`, `/api/exchange/*`, `/api/vaults/*`, `/api/bridge/*` | SQL models, configured payment providers, and external chain integration | Subscription plan read API verified locally; all user workflows `NOT_VERIFIED` |
| `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, `/settings` | `/api/auth/*`, `/api/identity/*`, `/api/audit/me`, `/api/developer/api-keys` | JWT/session, user/identity models, email and optional external identity providers | Local RBAC tests passed; browser and live auth `NOT_VERIFIED` |
| `/dashboard`, `/workspace`, `/analytics`, `/analytics-studio`, `/assistant`, `/tasks`, `/social`, `/ecosystem`, `/enterprise`, `/admin`, `/admin/:tab` | `/api/dashboard/*`, `/api/analytics/*`, `/api/ai/assistant/*`, `/api/tasks/*`, `/api/social/*`, `/api/enterprise/*`, `/api/admin/*` | SQL, Redis, background workers, VIT AI and enterprise integrations | `NOT_VERIFIED` in browser/live deployment |
| `*` | Frontend not-found boundary | React Router | `NOT_VERIFIED` in browser |

The main FastAPI OpenAPI document contained 844 paths and 925 HTTP operations at audit time. These are API declarations, not proof that every operation's full user workflow works. The deployment manifest defines a web service, a worker, PostgreSQL, Redis, and external VIT AI, VIT Chain, and Tachyon URLs. No production database or remote chain state was reachable for cross-checking.

### Non-route Service Inventory

| Component | Implementation surface | Evidence collected | Remaining state |
| --- | --- | --- | --- |
| FastAPI gateway | `backend/main.py`, `backend/app/api/routes/` | Local Uvicorn health and repaired read endpoints; 710 CI-selected tests before fixes plus 31 API/schema tests after fixes | Production PostgreSQL, Redis, full router operations and background boot `NOT_VERIFIED` |
| VIT Chain | `vit_chain/consensus/`, `core/`, `crypto/`, `p2p/`, `rpc/`, `storage/` | 66 chain tests and one three-node WebSocket consensus/restart integration test passed locally | Deployed chain, independent validators, adversarial finality and chain/API data consistency `NOT_VERIFIED` |
| VIT Node | `backend/vit_node/`; `vit-node` CLI entry in `pyproject.toml` | P2P client imported/exercised by the three-node test | CLI lifecycle, standalone daemon, storage participation and production peers `NOT_VERIFIED` |
| Tachyon | `backend/tachyon/{api,core,providers}` and configured external service | 13 package tests passed locally; live storage service was not run | Upload/retrieval against deployed providers, provider quorum, integrity challenges and production persistence `NOT_VERIFIED` |
| Standalone Explorer | Separate React app under `explorer/` | Manifest-range install and build passed; locked `npm ci` fails because lockfile versions conflict with the manifest | Reproducible locked install, API linkage and rendered routes `NOT_VERIFIED` |
| SDKs | Python SDK under `sdk/`; TypeScript package under `packages/sdk/` | Source/docs discovered; no SDK tests were executed in this run | Installation, compatibility, examples and end-to-end SDK calls `NOT_VERIFIED` |
| Render worker and schedules | `render.yaml`, `scripts/start_worker.sh`, backend schedulers | Deployment declaration inspected; application web process booted locally only | Production worker health, queue delivery, retries, schedules and webhook delivery `NOT_VERIFIED` |
| Sports data and payments | Provider clients/configuration for fixtures, odds and Paystack/Stripe | Local API tests and prediction code only; no provider credentials used | Freshness, settlement provenance, provider rate limits and sandbox payment workflow `NOT_VERIFIED` |

## Confirmed Findings and Repairs

### VIT-001: Prediction settlement column missing from migrations

- Severity: P1. Module: Prediction Intelligence and public landing data.
- Reproduction before repair: apply the existing migration chain to a new SQLite database (head `zz10_match_statistics`), then GET `/api/config/public/landing`. It returned 503 with `sqlite3.OperationalError: no such column: predictions.was_correct`.
- Root cause: `Prediction.was_correct` is declared by the ORM and queried by landing, history, accuracy, leaderboard, bankroll, and admin code, but no prior migration adds it. An older index migration skips the matching index when the column is absent.
- Repair: added `alembic/versions/zz11_prediction_settlement.py`, adding nullable `was_correct` and its index idempotently for existing databases.
- Regression coverage: a fresh-database Alembic test checks the column; the public landing API test requires HTTP 200 and a plans payload.
- Result: both tests pass; local Uvicorn served `/api/config/public/landing` with HTTP 200 after startup. Production migration and persisted production outcomes remain unverified.
- Acceptance: deploy the revision; verify the production migration head and column/index on PostgreSQL; verify settled and pending prediction reads through API and UI without changing financial state.

### VIT-002: Subscription router import failure hid routes

- Severity: P2. Module: subscriptions and public config.
- Reproduction before repair: importing `backend.main` logged `NameError: name 'User' is not defined` from `subscription.py`'s `upgrade_plan` annotation. Main catches router import exceptions, so the app could start while subscription and the config router (which imports subscription `PLANS`) were absent.
- Root cause: `User` was referenced in the evaluated annotation but not imported. The existing plans endpoint test accepted HTTP 404, masking the missing route.
- Repair: import `User` from `app.db.models`; require HTTP 200 and non-empty plan data in the existing subscription test.
- Result: the subscription API returned four plans; the config landing API also returned 200 after VIT-001. The focused API/schema suite passed.
- Acceptance: deploy and confirm both public API responses plus checkout authorization and payment-provider behavior using an authorized test account, not production payment credentials.

### VIT-003: Rendered/live verification blocked by environment and edge access

- Severity: P2 audit blocker, not a confirmed application defect. Classification: `BLOCKED_BY_DEPENDENCY`.
- Evidence: Playwright Chromium cannot load required shared objects in this unprivileged container; live requests alternated between HTTP 503 and Cloudflare HTTP 429. Authenticated smoke tests were skipped because no authorized credentials were provided.
- Impact: no claim can be made about production route rendering, responsive layouts, browser interactions, browser console/network behavior, service-worker caching, or live API data.
- Next step: run the same Playwright suites in a browser-enabled runner with the required OS libraries and an authorized staging account; obtain an edge-approved route to the documented staging/production URL.

### VIT-004: Frontend lint command has no ESLint executable

- Severity: P3 tooling gap. Classification: `BLOCKED_BY_DEPENDENCY`.
- Evidence: `npm run lint --prefix frontend` exits with `eslint: not found`; the script exists, but ESLint is not declared in `frontend/package.json` and is absent from the installed workspace dependencies.
- Impact: the advertised frontend lint command cannot run reproducibly. Frontend TypeScript compilation did pass as part of `npm run build`.
- Next step: select and declare an ESLint version/configuration in a separate dependency change, update the correct workspace lockfile, and add the command to CI. The pre-existing modified `package-lock.json` was not changed by this audit.

### VIT-005: Standalone Explorer lockfile is out of sync

- Severity: P3 tooling/release reproducibility gap. Module: standalone Explorer SPA.
- Evidence: `npm ci --prefix explorer --no-audit --no-fund` refuses the checked-in lock because it resolves Vite `8.3.4` and Tailwind `4.3.3` while `explorer/package.json` requires Vite `^7.3.7` and Tailwind `^3.4.17`, and reports additional missing/mismatched transitive entries.
- Impact: clean npm installs using the Explorer lock are not reproducible. A no-lock install from the manifest succeeded and the Explorer Vite build passed, so this is not evidence that the app source itself fails to build.
- Next step: reconcile the Explorer lockfile with the intended manifest and verify `npm ci` plus build; this audit did not change the lock.

## Test and Runtime Report

| Check | Result | Scope / caveat |
| --- | --- | --- |
| `pip check` | Passed | Isolated `.venv`; no broken requirements |
| `python -m compileall -q backend vit_chain` | Passed | Syntax compilation only |
| `ruff check . --output-format=github` | Passed | Ruff 0.17.1; repository configuration |
| CI-selected Python tests | 710 passed, 3 skipped, 16 deselected | `tests/`; live/env-example exclusions and `not live and not integration`; passed after adding venv `bin` to `PATH` |
| API/schema focused tests after repairs | 31 passed | `tests/test_api_endpoints.py tests/test_schema_bootstrap.py` |
| Settlement-specific regression tests | 2 passed | Fresh Alembic migration and landing response |
| VIT Chain tests | 66 passed | `vit_chain/tests/`, isolated local tests |
| Three-node consensus integration | 1 passed | `tests/integration/test_real_multinode_consensus.py`; independent local nodes, local WebSockets and SQLite only |
| Tachyon package tests | 13 passed | `backend/tachyon/tests/`; local implementation tests only |
| Frontend build/typecheck/assets | Passed | `npm run build --prefix frontend`; Vite emitted a non-fatal static/dynamic `useAuth` import chunk warning |
| Frontend lint | Blocked | `eslint: not found` |
| Standalone Explorer `npm ci` | Failed | Existing lockfile does not satisfy manifest versions |
| Standalone Explorer manifest install/build | Passed | `npm install --prefix explorer --package-lock=false --no-audit --no-fund && npm run build --prefix explorer`; lockfile unchanged |
| Local Playwright | 24 failed before browser launch | Chromium missing shared system libraries; zero page assertions executed |
| Deployed Playwright smoke | 1 failed, 2 skipped | `/ping` returned 503 to the test; authenticated cases explicitly skipped |
| Direct live read-only API probes | Blocked | Five requests received Cloudflare HTTP 429 challenge pages |
| Local Uvicorn runtime | Passed after async bootstrap | `/ping`, `/ready`, `/api/subscription/plans`, `/api/config/public/landing` returned HTTP 200; initial readiness was 503 while SQLite schema initialized |
| Fresh Alembic upgrade | Passed | SQLite head advanced from prior `zz10_match_statistics` to new `zz11_prediction_settlement` |

Full CI-selected pytest command (use an isolated DB path and test-only secrets):

```bash
PATH="$PWD/.venv/bin:$PATH" \
DATABASE_URL='sqlite+aiosqlite:///./audit_test.db' \
ENVIRONMENT=test AUTH_ENABLED=false USE_REAL_ML_MODELS=false RATE_LIMIT_ENABLED=false \
JWT_SECRET_KEY='audit-test-secret-not-for-production' \
SESSION_SECRET='audit-test-session-secret' \
PAYSTACK_SECRET_KEY='sk_test_placeholder' PAYSTACK_WEBHOOK_SECRET='whsec_test_placeholder' \
PYTHONPATH=backend:. .venv/bin/python -m pytest tests/ \
  --ignore=tests/test_live.py --ignore=tests/test_env_example.py \
  -m 'not live and not integration' -q --tb=short -p no:warnings
```

The audit removed the disposable SQLite databases and two SQL backup artifacts created by its test run. The ignored `.venv` remains for reproducibility. No production credentials or state-changing production requests were used.

## Implementation Roadmap

### Wave 0: Browser and deployment access

- Provide Chromium's native shared libraries in the audit runner or use the connected browser infrastructure.
- Obtain an edge-approved URL/access path for read-only production or staging verification.
- Acceptance: local and deployed Playwright suites execute assertions, collect console/network results, and capture desktop/tablet/mobile evidence.

### Wave 1: Deploy integrity fixes

- Deploy VIT-001 and VIT-002, then verify PostgreSQL migration head, `predictions.was_correct`, its index, and subscription/config API responses.
- Acceptance: fresh and upgraded PostgreSQL migration tests pass; API responses are correct; settled prediction history and aggregates remain consistent.

### Wave 2: Core user workflows

- Run authorized staging browser workflows for login/session, settings, subscription checkout in provider test mode, matches/predictions, wallet read views, and admin permission boundaries.
- Acceptance: frontend action -> API -> persistence -> refreshed UI is observed for each workflow; no mainnet/real payment changes.

### Wave 3: Data and external services

- Validate sports fixture/result freshness, odds provenance, model availability, VIT AI, Tachyon, VIT Chain, worker schedules, and webhook retries against authorized service health/data.
- Acceptance: compare UI/API/database/service timestamps and provenance; record each blocked provider explicitly.

### Wave 4: UX and route completeness

- Inspect all public routes and authenticated pages at desktop/tablet/mobile sizes, including the duplicate `/validators` declaration and route-specific loading/error/empty states.
- Acceptance: route ownership is unambiguous, direct navigation/back-forward works, and no material layout or keyboard/accessibility defect blocks a workflow.

### Wave 5: Production hardening

- Extend multi-node consensus tests to adversarial/restart/network-partition cases; verify independent operators, state sync and finality evidence; add observability and recovery/load gates.
- Acceptance: signed commit/finality and deterministic state are independently verified across nodes under tested fault scenarios; a local happy path alone is insufficient.

## Residual Risks and Unverified Areas

- Production deploy status and the production PostgreSQL migration head are unknown; workspace fixes are not a deployment.
- Live app, VIT AI, VIT Chain, Tachyon, Redis/PostgreSQL production connectivity, data freshness, provider credentials, payment/webhook delivery, and background worker health were not verified.
- Browser behavior for all 58 declared route entries, authenticated role-specific routes, session expiry, desktop/tablet/mobile layouts, accessibility, and service-worker/CDN invalidation remains `NOT_VERIFIED`.
- Local three-node consensus test coverage does not prove production Byzantine safety, validator-set independence, or finality under adversarial failures.
- The complete Python suite was run before the two source repairs; the affected API/schema modules and regression tests were rerun after repair (31 passed plus the focused 2-test run). The live browser suite remains blocked.
- Dedicated security scanning, real PostgreSQL integration, external payment sandbox flows, and actual deployment/cache invalidation checks were not run.