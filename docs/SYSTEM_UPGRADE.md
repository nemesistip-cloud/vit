# VIT Network — System Upgrade & Roadmap Status Document

> **Version**: 5.5.2  
> **Last updated**: 2026-07-19  
> **Service URL**: <https://vitnetwork-nls4.onrender.com>  
> **Current `/ping`**: `{"status":"ok"}` ✅  
> **Current health**: `{"overall_status":"HEALTHY"}` ✅

This document is the single source of truth for every upgrade, known issue, open track, and deployment decision affecting the VIT Network. It is updated in place — append changes at the top of each section rather than creating new files.

---

## Table of Contents

1. [Session Log — Jul 19 2026 (v5.5.2 Hotfixes)](#1-session-log--jul-19-2026-v552-hotfixes)
2. [Platform Health Snapshot](#2-platform-health-snapshot)
3. [Render Free-Plan Constraints & Mitigations](#3-render-free-plan-constraints--mitigations)
4. [Open Bugs & Incidents](#4-open-bugs--incidents)
5. [Execution Roadmap — All 20 Tracks](#5-execution-roadmap--all-20-tracks)
6. [Business Roadmap — All 5 Phases](#6-business-roadmap--all-5-phases)
7. [Dependency Map & Startup Order](#7-dependency-map--startup-order)
8. [Infrastructure Upgrade Plan](#8-infrastructure-upgrade-plan)
9. [CI/CD Gate Status](#9-cicd-gate-status)
10. [Subsystem Inventory & Health Contract](#10-subsystem-inventory--health-contract)
11. [Frontend & TypeScript Status](#11-frontend--typescript-status)
12. [Multi-Sport Intelligence Status](#12-multi-sport-intelligence-status)
13. [Blockchain & Tachyon Status](#13-blockchain--tachyon-status)
14. [Security & Compliance Checklist](#14-security--compliance-checklist)
15. [Upgrade Decision Log](#15-upgrade-decision-log)

---

## 1. Session Log — Jul 19 2026 (v5.5.2 Hotfixes)

### Context

Full bug audit and immediate hotfix pass on the live Render free-plan deployment. Service was live but booting in a permanent DEGRADED state due to a Pydantic v2 compatibility bug that had been masked by a `try/except BaseException` wrapper introduced in v5.5.1.

### Bugs Found

| # | Severity | Bug | Root Cause |
|---|----------|-----|-----------|
| B-01 | **CRITICAL** | Service starts DEGRADED on every cold boot | `ConfigurationManager.load()` called `raise SystemExit(1)` on any config error. In Pydantic v2, `Model(**alias_keyed_data)` silently drops aliased fields → `ValidationError` → `SystemExit(1)` on every boot. |
| B-02 | **HIGH** | Sports router `ImportError` silently swallowed | `app.api.routes.sports` wrapped in `try/except` in `main.py` but the underlying import failure was never diagnosed. |
| B-03 | **HIGH** | 4 consecutive deploy failures (Jul 18) | TypeScript errors across ~18 frontend pages. No `tsc` gate in CI; broken TS reached Render builds. Docker layer cache hid the error until a clean build exposed it. |
| B-04 | **HIGH** | No TypeScript pre-deploy gate | `ci.yml` had ruff + mypy + pytest but zero TypeScript compilation check. |
| B-05 | **MEDIUM** | `render.yaml` references discontinued free-tier services | Background `worker` service (free workers discontinued) and `redis` service (free Redis discontinued Sept 2024) defined in `render.yaml`. Both fail silently on Render. |

### Fixes Applied

| # | Fix | Commit | Status |
|---|-----|--------|--------|
| F-01 | `app/core/config/manager.py` — full rewrite: `load()` never raises; catches `ValidationError` + `Exception`, logs CRITICAL, falls back to safe defaults; `_build_section()` uses `model.model_validate()` (Pydantic v2 correct API) instead of `Model(**alias_data)` | `fix(config): correct IndentationError` (latest) | ✅ Deployed & live |
| F-02 | `main.py` — add `_kernel_boot_ok` / `_kernel_boot_error_msg` module-level flags; `/ping` returns `{"status":"degraded","detail":"..."}` on boot failure; `/api/system/health/summary` exposes `kernel_boot_error` and `config_error` | `feat(health): expose boot status` | ✅ Deployed & live |
| F-03 | `.github/workflows/ci.yml` — new blocking `typecheck-frontend` job: `pnpm exec tsc --noEmit`; blocks merges to `main` on TS errors | `ci: add blocking TypeScript type-check job` | ✅ Deployed |
| F-04 | Multi-stage Dockerfile attempted (python-builder + frontend-builder + explorer-builder + slim runtime) | `chore(docker): multi-stage build` | ⚠️ Reverted — venv cross-stage path resolution failed on Render's slim runtime; caused `nonZeroExit:1`. Deferred. |

### Incident Timeline

```
09:11 UTC  — Previous working deploy (guard kernel.boot() patch, v5.5.1)
10:57 UTC  — feat(health): main.py boot flags → LIVE ✅
10:59 UTC  — fix(config) + Dockerfile multi-stage + ci.yml → update_failed ❌
             Root cause: config/manager.py had 4-space module-level indent
             (JavaScript template literal indentation bug in push tooling)
11:03 UTC  — Multi-stage Dockerfile venv fix → update_failed ❌
             Root cause: still the broken config/manager.py
~11:20 UTC — Dockerfile reverted → still update_failed ❌
             Root cause: config/manager.py still broken
~11:35 UTC — config/manager.py re-pushed via JS template literal → update_failed ❌
             Root cause: same JS indent bug — fix didn't fix
~11:45 UTC — config/manager.py written via shell heredoc + base64 + curl → LIVE ✅
```

### Key Engineering Lesson

> **Never build Python file content inside indented JavaScript template literals.** The JS indentation level infects the Python content on every line after the first. Always use `ShellExec` with a heredoc, `base64 -w 0`, and `curl` to push Python files to the GitHub Contents API. See `.agents/memory/github-api-python-files.md`.

---

## 2. Platform Health Snapshot

| Subsystem | Status | Notes |
|-----------|--------|-------|
| **API Gateway** | ✅ Healthy | `/ping` → `ok`, `/api/system/health/summary` → `HEALTHY` |
| **Config** | ✅ Healthy | Pydantic v2 bug fixed; safe-defaults fallback in place |
| **Database** | ✅ Healthy | Render free Postgres (vit-postgres-v2), alembic migrations run on start |
| **Redis** | ⚠️ Degraded | `render.yaml` still defines free Redis (discontinued Sept 2024); service runs without Redis but rate-limiting and Celery task brokering are non-functional |
| **AI / ML** | ⚠️ Unknown | No failed health check, but no PyTorch GPU on Render free; inference runs on CPU. Model load times may OOM on 512 MB RAM under load |
| **Blockchain** | ⚠️ Unknown | Depends on Base L2 RPC endpoint config; no `BASE_RPC_URL` confirmed in env |
| **Tachyon Storage** | ⚠️ Unknown | Requires cloud provider keys (GCS/Dropbox); gracefully skipped if absent |
| **Sports Router** | ⚠️ Degraded | `app.api.routes.sports` import silently swallowed in `main.py`; endpoint may 404 |
| **Worker / Celery** | ❌ Down | `render.yaml` worker service on discontinued free plan; no background task processing |
| **Frontend SPA** | ✅ Healthy | Built in Dockerfile and served as static files by FastAPI |
| **Explorer** | ✅ Healthy | Built in Dockerfile; served as static files |

---

## 3. Render Free-Plan Constraints & Mitigations

| Constraint | Limit | Current Mitigation | Recommended Fix |
|------------|-------|--------------------|-----------------|
| RAM | 512 MB | `WEB_CONCURRENCY=1` in Dockerfile | Upgrade to Starter ($7/mo) for 512 MB dedicated; avoid loading PyTorch models at startup |
| CPU | Shared | `--workers 1` in uvicorn | Acceptable for current load |
| Disk | Ephemeral | n/a | Do not rely on local file storage; use Tachyon or Postgres |
| Free Redis | **Discontinued** | Service falls back gracefully; fakeredis not configured for prod | Replace with Upstash Redis free tier (5 MB, always free) or Redis Labs free |
| Free Workers | **Discontinued** | Background tasks silently dropped | Use APScheduler in-process (already scaffolded) or Render cron jobs |
| Cold starts | ~30 s sleep after 15 min idle | `/ping` health check at `healthCheckPath` keeps it warm | Upgrade to paid plan removes cold starts |
| Build time | Full Docker rebuild per commit | No layer caching on free plan | Multi-stage Dockerfile (deferred) + `.dockerignore` optimization |

### Immediate Action: Suppress Discontinued Services in render.yaml

The `render.yaml` worker and Redis entries are dead weight — they cause Render to attempt provisioning on discontinued plans. They should be commented out until paid plan services replace them:

```yaml
# FIXME: worker service removed — Render free workers discontinued.
# Re-enable with plan: starter when upgrading.
# - type: worker ...

# FIXME: Redis removed — Render free Redis discontinued Sept 2024.
# Replace with Upstash or Redis Cloud free tier.
# - type: redis ...
```

**Priority**: High. File: `render.yaml`. Assigned: unassigned.

---

## 4. Open Bugs & Incidents

### B-02 — Sports Router ImportError (HIGH)

**File**: `main.py` sports router import block  
**Symptom**: `app.api.routes.sports` wrapped in `try/except` but root cause unknown. The endpoint may silently 404 or return 500 for all sports routes.  
**Investigation needed**:
1. Read `app/api/routes/sports.py` for the failing import
2. Check if `app.services.sports` or a specific sports provider module is missing
3. Run locally: `python3 -c "from app.api.routes import sports"`
4. If it's a missing optional dependency, add a `_sports_available` flag like `gcs_storage.py` does

**Fix pattern** (from v5.5.0 CHANGELOG — same as GCS/GCP pattern):
```python
try:
    from app.api.routes import sports as _sports_routes
    app.include_router(_sports_routes.router, prefix="/api/sports")
    _sports_available = True
except ImportError as e:
    _sports_available = False
    logger.warning("[main] Sports router unavailable: %s", e)
```

---

### B-05 — render.yaml Discontinued Services (MEDIUM)

**File**: `render.yaml`  
**Symptom**: `vitnetwork-redis` and `vitnetwork-worker` defined on discontinued `free` plan.  
**Fix**: Comment out both blocks; document replacement path (Upstash Redis, APScheduler in-process).  
**Priority**: Medium. No active crash — just silent failures on Celery tasks and rate limiting.

---

### B-06 — Dockerfile Multi-Stage Deferred (LOW)

**File**: `Dockerfile`  
**Status**: Reverted. The slim runtime stage doesn't reliably find venv packages without `VIRTUAL_ENV` being honoured by the process manager.  
**Investigation**: The issue is likely that `bash scripts/start_production.sh` does not inherit the Docker `ENV PATH` when invoked by Render's entrypoint. Need to confirm with `which python3` in the start script.  
**Fix (when resumed)**: Add `source /opt/venv/bin/activate` at the top of `scripts/start_production.sh`, OR use `ENV VIRTUAL_ENV=/opt/venv` + `ENV PATH="/opt/venv/bin:$PATH"` and test locally with `docker build + docker run`.

---

### B-07 — TypeScript Errors on 18+ Pages (MEDIUM, gate now in place)

**Status**: CI gate added (F-03). New TS errors will block merge. Existing errors on the `main` branch need to be cleared.  
**Scope**: ~18 pages had `TS2345` errors (unknown not assignable to string|Date in `timeAgo` calls; already patched in commit `e6a179f`). Run `cd frontend && pnpm exec tsc --noEmit` to get the current error count.  
**Priority**: Medium. Gate prevents regression; existing baseline needs cleanup.

---

## 5. Execution Roadmap — All 20 Tracks

Source: `.engineering/roadmaps/21_EXECUTION_ROADMAP.md`

### Phase 1 — Core Infrastructure (The Foundation)

| Track | Name | Status | Notes |
|-------|------|--------|-------|
| TRACK-001 | Bootstrap Engine | ✅ Complete | `kernel.boot()` + subsystem lifecycle manager live. Fixed: no longer crashes on config error (B-01 fix). |
| TRACK-002 | Module Registry | ✅ Complete | `register_core_subsystems()` in `app/core/subsystems.py`. 13 subsystems registered. |
| TRACK-003 | Dependency Resolver | ✅ Complete | Subsystem `dependencies` field drives boot order in kernel. |
| TRACK-004 | Unified Event Bus | ⚠️ Partial | Redis pub/sub scaffolded; Redis itself is down on Render free plan (B-05). Functional locally. |
| TRACK-005 | Health & Observability Suite | ✅ Complete (v5.5.2 enhanced) | `obs_manager.health`, structured logging, `/api/system/health/summary` now exposes boot errors and config errors. |

### Phase 2 — Intelligence & Storage (The Brain & Memory)

| Track | Name | Status | Notes |
|-------|------|--------|-------|
| TRACK-006 | AI Inference Engine v2 | ⚠️ Partial | Model lazy-loading in place (`USE_REAL_ML_MODELS` flag). CPU-only on Render free. PyTorch/XGBoost/LSTM loaded on demand. Risk: OOM on 512 MB if multiple models loaded simultaneously. |
| TRACK-007 | Agent Workflow Manager | ⚠️ Partial | 22 agents defined in `app/agents/`. Celery worker down (B-05). Agents run synchronously or not at all in current deploy. |
| TRACK-008 | Tachyon Swarm Hardening | ⚠️ Partial | Reed-Solomon (reedsolo) installed, `TachyonConfig` in models, S3-compatible API defined. Cloud credentials (GCS/Dropbox) required. Gracefully skipped when absent. |
| TRACK-009 | Global Search & Indexing | 🔲 Not started | `pgvector` installed. No unified multi-entity fuzzy lookup endpoint found. |

### Phase 3 — Financial & Legal Infrastructure (The Ledger)

| Track | Name | Status | Notes |
|-------|------|--------|-------|
| TRACK-010 | Blockchain Settlement Layer (L2) | ⚠️ Partial | `BlockchainSubsystem` registered. Base L2 chain_id 8453. `vit_chain/` node code exists. Needs `BASE_RPC_URL` env var. |
| TRACK-011 | Wallet Protection Layer | ✅ Complete | Multi-currency wallet (USD, NGN, USDT, VITCoin). Sports/niche segregation in `WalletSubsystem`. |
| TRACK-012 | Merit & Governance Protocols | 🔲 Not started | Electoral oracle scaffolded in roadmap. No `ElectoralOracle.sol` deployment found. |
| TRACK-013 | Compliance & KYC Engine | ⚠️ Partial | W3C DID in place (`IdentitySubsystem`). KYC scoring in `app/services/`. Automated risk scoring not confirmed live. |

### Phase 4 — Vertical Expansion (The Verticals)

| Track | Name | Status | Notes |
|-------|------|--------|-------|
| TRACK-014 | Sports Intelligence Terminal | ✅ Complete (v5.5.1) | `MultiSportOrchestrator` — Football, Basketball, Tennis live. Surface bias (Tennis), efficiency models (Basketball). Admin audit endpoint `/api/admin/audit-predictions`. |
| TRACK-015 | Electoral & Policy Simulator | 🔲 Not started | `ElectoralOracle.sol` not deployed. `Policy Simulator v1.0` not found. Q1 2026 target (overdue). |
| TRACK-016 | Academy & Research Portal | 🔲 Not started | No academic agent or research endpoint found in routes. |
| TRACK-017 | Affiliate Execution Hub | 🔲 Not started | `ShopManager.sol` not found. Agent Recruitment Portal not deployed. Q4 2025 target (overdue). |

### Phase 5 — Distribution & Scale (The Reach)

| Track | Name | Status | Notes |
|-------|------|--------|-------|
| TRACK-018 | Multi-Cloud Orchestration | 🔲 Not started | `cloudbuild.yaml` in root suggests GCP intention. Azure not configured. Currently single Render free service. |
| TRACK-019 | Mobile Native Terminals | 🔲 Not started | No Expo/Flutter project found. 2027+ target. |
| TRACK-020 | Decentralized ID (DID) v1 | ⚠️ Partial | W3C DID issuing in place. On-chain DID anchoring to VIT Chain not confirmed. |

---

## 6. Business Roadmap — All 5 Phases

Source: `docs/ROADMAP.md`

### Phase 1 — Sports Dominance (Current)

| Item | Status | Notes |
|------|--------|-------|
| AI Ensemble for high-precision sports signals | ✅ Complete | 13-model ensemble (LSTM, XGBoost, Transformers) live |
| ERC-20 VITToken & On-chain staking | ✅ Complete | Base L2 deployment |
| Universal Oracle for verifiable sports results | ✅ Complete | Football + Basketball + Tennis via `MultiSportOrchestrator` |
| P2P Network Layer (Track 3): Decentralized peer discovery, gossip protocol | ✅ Complete | `vit_chain/` node infrastructure |

### Phase 2 — Modern Betting Shops (Q4 2025 — Overdue)

| Item | Status | Blocker |
|------|--------|---------|
| Agent Recruitment Portal launch | 🔲 Not started | Requires `ShopManager.sol` deployment |
| `ShopManager.sol` deployment for commission tracking | 🔲 Not started | Smart contract not found in repo |
| Offline terminal integration (low-bandwidth) | 🔲 Not started | No PWA/offline-first implementation found |

**Recovery plan**: Target Q3 2026. Prioritize `ShopManager.sol` first (unblocks Recruitment Portal). Offline terminal can use React PWA with service workers.

### Phase 3 — Electoral & Policy Analytics (Q1 2026 — Overdue)

| Item | Status | Blocker |
|------|--------|---------|
| `ElectoralOracle.sol` integration | 🔲 Not started | No contract in `vit_chain/` |
| Citizen sentiment analytics engine | ⚠️ Partial | Sentiment models exist; political domain not wired to frontend |
| Policy Simulator v1.0 | 🔲 Not started | No simulator endpoint found |

**Recovery plan**: Target Q4 2026. Sentiment engine can be surfaced in 1 sprint (routing only). Oracle + Simulator need contract deployment.

### Phase 4 — E-commerce & Remittances (Q2 2026)

| Item | Status | Blocker |
|------|--------|---------|
| Marketplace integration | ⚠️ Partial | GA per README; verify live payment flow end-to-end |
| Cross-border remittance rails via $VIT | ⚠️ Partial | Beta per README; `wallet/routes.py` warning on payment gateway fallback (fixed in v5.5.0) |
| OPay/PalmPay/MoMo deep integration | 🔲 Not started | Only Paystack/Flutterwave confirmed |

### Phase 5 — Full Continental Dominance (2027+)

| Item | Status |
|------|--------|
| Expansion to Kenya, Ghana, South Africa, Egypt | 🔲 Not started |
| Decentralized ID (DID) for all participants | ⚠️ Partial (see TRACK-020) |
| $VIT as standard for verifiable African analytics | 🔲 Not started |

---

## 7. Dependency Map & Startup Order

Source: `.engineering/roadmaps/20_DEPENDENCY_MAP.md`

```
Boot order (subsystem dependency resolution):
  Priority 0 (foundational)  →  Database, Redis*
  Priority 1 (primary)       →  API Gateway, ConfigSubsystem, ObservabilitySubsystem
  Priority 2 (domain)        →  AI Module, TaskSubsystem, AuthorizationSubsystem
  Priority 3 (integrated)    →  Tachyon Swarm, BlockchainSubsystem, WalletSubsystem
  Priority 4 (presentation)  →  Frontend SPA, PlatformSubsystem, PluginSubsystem

* Redis currently down on Render free plan. System degrades gracefully.
```

### Dependency Rules (enforced by kernel)

1. **Unidirectional**: Frontend MUST NOT be depended on by Core.
2. **No circular deps**: Domain modules communicate via event bus, not direct imports.
3. **Graceful degradation**: Optional integrations (Telegram, GCS, Redis) MUST NOT block startup.
4. **Contractual binding**: Cross-domain dependencies defined in `contracts.json` (verify location).

---

## 8. Infrastructure Upgrade Plan

### Immediate (this sprint)

| Action | File | Priority | Owner |
|--------|------|----------|-------|
| Comment out discontinued worker + Redis in `render.yaml` | `render.yaml` | HIGH | |
| Investigate sports router import error | `app/api/routes/sports.py` | HIGH | |
| Add Upstash Redis free tier (replace Render Redis) | `render.yaml` + env | HIGH | |
| Clear remaining TypeScript baseline errors | `frontend/src/` | MEDIUM | |

### Near-term (next 2 sprints)

| Action | Details |
|--------|---------|
| Upgrade Render to Starter plan | Removes cold starts, doubles RAM to 512 MB dedicated, enables background workers. Cost: $7/mo web + $7/mo worker = $14/mo. |
| Re-attempt multi-stage Dockerfile | Investigate why venv PATH fails on Render. Add `source /opt/venv/bin/activate` to `start_production.sh`. Reduces cold-start image pull time. |
| Add `APScheduler` in-process task runner | Fallback while Celery worker is down. For low-frequency background jobs (health checks, settlement cron). |
| Implement `fakeredis` production fallback | When `REDIS_URL` absent: use in-process fakeredis with a warning log. Restores rate-limiting and session cache without a real Redis instance. |

### Medium-term (Q3 2026)

| Action | Details |
|--------|---------|
| Migrate from Render free → Google Cloud Run | `cloudbuild.yaml` already in repo. Cloud Run scales to zero (same cost profile) but no cold start penalty with min-instances=1. Postgres → Cloud SQL. Redis → Memorystore. |
| Enable Tachyon VESS in production | Configure `GCS_BUCKET`, `DROPBOX_TOKEN`, `TACHYON_ENCRYPTION_KEY`. At least 2 storage nodes required for Reed-Solomon (4 data + 2 parity = 6 shards minimum). |
| Deploy `ShopManager.sol` to Base L2 testnet | Unblocks Phase 2 business roadmap. |

---

## 9. CI/CD Gate Status

File: `.github/workflows/ci.yml`

| Job | Command | Blocking? | Status |
|-----|---------|-----------|--------|
| `lint` | `ruff check . --output-format=github` | ✅ Yes | Active |
| `type-check` | `mypy app/ vit_chain/ --ignore-missing-imports` | ⚠️ Non-blocking (`\|\| true`) | Active — **make blocking** |
| `test` | `pytest tests/ -m "not live and not integration"` | ✅ Yes | Active |
| `typecheck-frontend` | `cd frontend && pnpm exec tsc --noEmit` | ✅ Yes | **Added v5.5.2** |

### Next CI improvements

- **Remove `|| true` from mypy**: The mypy job currently has `|| true` making it non-blocking. Once the type-error baseline is cleared, remove this and let mypy block merges.
- **Add `alembic check`**: Run `alembic check` in CI to catch unapplied migrations before they hit production.
- **Add `pytest --cov-fail-under=30`**: Coverage floor is currently `0`. Set a meaningful baseline.
- **Add `ruff format --check`**: Enforce code formatting in CI.
- **Add E2E smoke test**: `curl https://vitnetwork-nls4.onrender.com/ping` as a post-deploy verification step.

---

## 10. Subsystem Inventory & Health Contract

| Subsystem Class | Name | Dependencies | Failure Impact | Health Check |
|-----------------|------|-------------|----------------|--------------|
| `ConfigSubsystem` | `config` | — | DEGRADED boot (fixed v5.5.2) | `config_manager.is_healthy` |
| `ObservabilitySubsystem` | `observability` | — | No metrics/alerts | `obs_manager.health` ping |
| `DatabaseSubsystem` | `database` | `config`, `observability` | Total outage | `SELECT 1` latency < 100 ms |
| `RedisSubsystem` | `redis` | `config`, `observability` | Degraded (cache/tasks miss) | `PING` response |
| `AuthorizationSubsystem` | `authorization` | `config`, `observability`, `database` | No auth | JWT verify |
| `AISubsystem` | `ai` | `config`, `observability`, `database` | No intelligence | Model loaded flag |
| `BlockchainSubsystem` | `blockchain` | `config`, `observability`, `database` | No settlement | RPC endpoint reachable |
| `WalletSubsystem` | `wallet` | `config`, `observability`, `database` | No payments | Treasury address valid |
| `TaskSubsystem` | `tasks` | `config`, `observability`, `redis` | No background jobs | Worker heartbeat |
| `PlatformSubsystem` | `platform` | `config`, `observability`, `database`, `authorization` | Core ops fail | Smoke request |
| `PluginSubsystem` | `plugins` | `config`, `observability`, `database` | No extensions | Plugin registry count |
| `ResourcePlatformSubsystem` | `resource_platform` | — | Resource limits untracked | CPU/RAM metrics |
| `PersistenceManager` | `persistence` | — | Data loss risk | Write round-trip |

### Health Contract Rules

1. Any subsystem with `failure_impact = Total outage` must NEVER silently swallow startup errors — it must update `obs_manager.health` with `UNHEALTHY` and log CRITICAL.
2. Any subsystem with `failure_impact = Degraded` must catch its own exceptions, log WARNING, and set health to `DEGRADED` so the system continues running.
3. `/api/system/health/summary` is the canonical health endpoint. It MUST reflect `kernel_boot_error` and `config_error` (added v5.5.2).
4. `/ping` is the liveness probe. It MUST return 200 even in DEGRADED state. It MUST return `{"status":"degraded"}` when `_kernel_boot_ok == False`.

---

## 11. Frontend & TypeScript Status

| Area | Status | Notes |
|------|--------|-------|
| React version | 19 | Latest stable |
| Build tool | Vite + Tailwind CSS v4 | Fast HMR, optimized production bundle |
| TypeScript gate | ✅ Active (v5.5.2) | `pnpm exec tsc --noEmit` blocks merges |
| Known TS errors | ⚠️ Baseline unclear | `timeAgo()` `TS2345` fixed in `e6a179f`. Run `pnpm exec tsc --noEmit` from `frontend/` to get current count. |
| Pages | ~18+ admin/analytics/blockchain/DeFi/explorer/governance pages | |
| Explorer | Standalone npm app | Built separately in Dockerfile |

### Frontend Upgrade Tasks

- [ ] Run `pnpm exec tsc --noEmit` and fix all remaining type errors (make the CI gate pass on a clean branch)
- [ ] Audit unused `any` casts introduced as quick TS-bypass fixes
- [ ] Add `eslint` to CI (currently only ruff/mypy for Python)
- [ ] Evaluate React Query / TanStack Query for server-state management
- [ ] Add Storybook for component isolation (useful before mobile terminal work)

---

## 12. Multi-Sport Intelligence Status

Source: `docs/SPORTS_INFRA_UPGRADE_REPORT.md` (v5.5.1)

| Sport | Prediction Engine | Markets | Status |
|-------|------------------|---------|--------|
| **Football** | Full 13-model ML ensemble | 1X2, Asian Handicap, BTTS, O/U, Correct Score | ✅ GA |
| **Basketball** | `MultiSportOrchestrator` heuristic (efficiency-weighted) | Win/Loss, O/U | ✅ Beta |
| **Tennis** | `MultiSportOrchestrator` heuristic (surface bias: Clay/Hard/Grass) | Win/Loss, Set Markets | ✅ Beta |
| **Cricket** | Generic fallback (odds-driven only) | Win/Loss | ⚠️ Minimal |
| **MMA** | Generic fallback | Win/Loss | ⚠️ Minimal |

### Sports Intelligence Upgrade Tasks

- [ ] Promote Basketball + Tennis from heuristic → full ML model (same as Football)
- [ ] Enable `OracleNode` automated self-healing: when audit detects gap, trigger re-sync
- [ ] Add Player Props market depth for Basketball + Tennis
- [ ] Add in-play (live) market support
- [ ] Diagnose and fix sports router import error (B-02)
- [ ] Add `ISPORTS_API_KEY` to Render environment (currently absent per config diagnostics)

---

## 13. Blockchain & Tachyon Status

### VIT Chain (Base L2)

| Component | Status | Notes |
|-----------|--------|-------|
| Base L2 mainnet integration | ⚠️ Configured | `chain_id: 8453`. Needs `BASE_RPC_URL` in Render env vars |
| VITToken (ERC-20) | ✅ Deployed | On-chain staking live |
| `ShopManager.sol` | 🔲 Not deployed | Phase 2 blocker |
| `ElectoralOracle.sol` | 🔲 Not deployed | Phase 3 blocker |
| P2P gossip / node discovery | ✅ Complete | `vit_chain/` node infrastructure |
| JSON-RPC interface | ✅ Complete | Ethereum-compatible gateway |

### Tachyon VESS (Swarm Storage)

| Component | Status | Notes |
|-----------|--------|-------|
| Reed-Solomon coding (`reedsolo`) | ✅ Installed | `TACHYON_DATA_SHARDS=4`, `TACHYON_PARITY_SHARDS=2` in config |
| S3-compatible API | ✅ Implemented | `GET/PUT/DELETE /api/tachyon/s3/{bucket}/{key}` |
| GCS storage provider | ⚠️ Conditional | Lazy import; requires `GCS_BUCKET` + service account JSON |
| Dropbox provider | ⚠️ Conditional | Requires `DROPBOX_TOKEN` |
| Storage challenges (periodic) | 🔲 Not confirmed | Part of TRACK-008 hardening |
| Production activation | 🔲 Blocked | Needs at least one storage provider configured in env |

---

## 14. Security & Compliance Checklist

From `docs/AUDIT_REPORT.md` + v5.5.0 CHANGELOG:

| Item | Status | Notes |
|------|--------|-------|
| Lazy-import guards on optional GCP/Firebase deps | ✅ Fixed v5.5.0 | `GCS_AVAILABLE`, `GCP_SECRETS_AVAILABLE` flags |
| HMAC webhook signature verification | ✅ Implemented | `X-VIT-Signature` header |
| JWT secret rotation | ⚠️ Manual | `JWT_SECRET_KEY` set via Render env; no automated rotation |
| Paystack gateway fallback hardcode removed | ✅ Fixed v5.5.0 | Now logs WARNING instead of silent redirect |
| predict.py idempotency hash float serialization | ✅ Fixed v5.5.0 | Fixed-decimal string serialization |
| Dashboard leaderboard duplicate dict keys | ✅ Fixed v5.5.0 | Removed duplicates |
| Admin password auto-generation at startup | ✅ Implemented | `scripts/start_production.sh` generates if absent |
| 2FA (TOTP) | ✅ Implemented | `pyotp` in requirements |
| Rate limiting | ⚠️ Degraded | Depends on Redis (down); disabled when Redis absent |
| KYC / identity verification | ⚠️ Partial | DID in place; automated risk scoring not confirmed live |
| Secrets in GCP Secret Manager | ⚠️ Optional | Only runs if `GCP_PROJECT_ID` set; currently env-var only on Render |
| `SESSION_SECRET` in Render env | ✅ Set | Confirmed in workspace secrets |

### Security Upgrade Tasks

- [ ] Enable `RATE_LIMIT_ENABLED=true` once Redis is replaced with Upstash
- [ ] Rotate `JWT_SECRET_KEY` — current value was set manually at unknown date
- [ ] Configure `GCP_PROJECT_ID` + `GOOGLE_SERVICE_ACCOUNT_JSON` in Render for production secrets management
- [ ] Add `Content-Security-Policy` header to FastAPI middleware
- [ ] Run `pip-audit` on `requirements.txt` (no CVE check in CI)
- [ ] Add `bandit` to CI security gate

---

## 15. Upgrade Decision Log

Each architectural or infrastructure decision with non-obvious tradeoffs is recorded here for future context.

---

### DEC-001 — Multi-Stage Dockerfile Deferred (2026-07-19)

**Decision**: Reverted multi-stage Dockerfile; stayed on single-stage.  
**Why deferred**: Both `--user` pip install and `/opt/venv` approaches caused `nonZeroExit:1` startup crashes on Render. Root cause: Render's runtime entrypoint does not fully honour Docker `ENV PATH` when invoking `bash scripts/start_production.sh`. The venv/user-packages binary path is not on `$PATH` when the start script runs.  
**Resumption criteria**: Add `source /opt/venv/bin/activate` as first line of `scripts/start_production.sh`, test locally with `docker run`, then re-attempt. Estimated image size saving: ~300 MB (removes Node.js runtime from production image).

---

### DEC-002 — config_manager.load() Never Raises (2026-07-19)

**Decision**: `ConfigurationManager.load()` must never raise or call `sys.exit()`.  
**Why**: Raising from `load()` before the uvicorn server is bound means the process exits before Render's health check can pass. The service shows as DEGRADED with no HTTP response, making it impossible to diagnose remotely.  
**Contract**: On any config error, log CRITICAL, set `self._boot_error`, fall back to all-defaults `VITConfig`. The service starts, `/ping` returns `{"status":"degraded","detail":"..."}`, ops can diagnose via the health endpoint.

---

### DEC-003 — Single Worker Process on Render Free (2026-07-19)

**Decision**: `WEB_CONCURRENCY=1` hardcoded in Dockerfile.  
**Why**: Render free plan has 512 MB RAM shared. PyTorch + XGBoost models loaded in a single process already push 350–450 MB. Two workers = OOM kill.  
**Override**: Set `WEB_CONCURRENCY=2` in Render environment variables if upgrading to Starter plan (1 GB RAM).

---

### DEC-004 — Pydantic v2 Migration (v5.5.2)

**Decision**: All `ConfigurationManager._build_section()` calls now use `model.model_validate(alias_keyed_data)` for Pydantic v2.  
**Why**: In Pydantic v2, `Model(**data)` with alias-keyed data silently drops fields if `model_config` does not set `populate_by_name=True`. `model_validate()` correctly resolves aliases from `Field(..., alias="ENV_VAR")` without any config change.  
**v1 compat**: Maintained via `if hasattr(model, "model_fields")` branch; falls back to `model.__fields__` for any Pydantic v1 models remaining in the codebase.

---

*VIT Network — Verifiable Intelligence. Universal Trust.*  
*Document maintained by: engineering team. Update this file with every non-trivial deploy.*
