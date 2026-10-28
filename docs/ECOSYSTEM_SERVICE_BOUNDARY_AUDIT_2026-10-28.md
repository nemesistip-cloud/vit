# VIT Ecosystem Service Boundary Audit

Audit date: 2026-10-28

## Scope and Status

Inspected the local `vit` repository, the GitHub `main` trees for `vit-ai`, `vit-chain`, and `vit-storage`, Render service metadata/events, and recent runtime logs. No credential values were printed. No production service, database, or environment variable was changed.

This is a partial remediation, not a completed migration. Core source now has an explicit in-process scheduler gate and verified Render host defaults. The gate remains enabled in the Render blueprint because Render currently has no deployed `vitnetwork-worker`; switching it off before a replacement job owner is live would strand scheduled work. Core's Render service also has `autoDeploy=no`, so local changes are not active in production.

## Current Architecture

| Service | Current responsibilities and execution | Boundary concerns |
| --- | --- | --- |
| VIT Network core (`vitnetwork`) | HTTP gateway, authentication, API routing, orchestration, shared Postgres access. Gateway lifespan starts an APScheduler with 11 agents; kernel `TaskSubsystem` starts ticker sync, settlement, Telegram digest, and chain snapshot loops; lifespan also starts Tachyon challenge/verification workers and a workflow dispatcher. | Heavy AI/sports agents, chain snapshot work, and storage integrity work share the gateway event loop and DB pool. Several of the same agent jobs are also declared in Celery Beat. |
| VIT-AI (`vit-ai-z3d4.onrender.com`) | Model/inference API and Redis-backed training-job registry; models load during app lifespan. | No scheduled job executor was found in the repository. Training jobs are persisted/restored, but the inspected manager does not execute them. Core owns many AI/model jobs instead. |
| VITChain (`vit-chain-5bd9.onrender.com`) | Chain database and a 15-second consensus epoch scheduler started from the service lifespan. | Scheduler runs in-process without a cross-replica lease. Config defaults `DB_POOL_SIZE` to 10 for PostgreSQL. Render currently reports one instance. |
| VIT-Storage (`vitstorage.onrender.com`) | Storage API and hourly Tachyon verification worker started from the API lifespan; provider health has a 5-second timeout. | Core starts another Tachyon challenge scheduler and verification worker; Celery Beat also declares Tachyon maintenance. Storage scheduler ownership is not coordinated across replicas. |
| Core Celery worker | Source defines Celery tasks and a Beat schedule; `start_worker.sh` starts concurrency 2 with embedded Beat (`-B`). | Render API returned no deployed `vitnetwork-worker`. Therefore the Beat jobs are configured in source but are not currently an active production owner. Running embedded Beat on multiple replicas would duplicate schedules. |

The requested four services are on Render's free plan with one instance each. The explorer service exists but is outside this audit's requested service boundary.

## Job Ownership Inventory

| Workload | Current owner(s) | Intended owner |
| --- | --- | --- |
| `performance-monitor`, `weight-optimizer`, `retrain-trigger`, prediction/model evaluation, model promotion | Core in-process swarm; overlapping Beat entries exist in core source | VIT-AI for model lifecycle and inference; dispatch from core only |
| `match-scout`, `fixture-sync`, `live-match-tracker` | Core in-process swarm | Sports-data/AI execution service by workload; core should retain API contracts and lightweight dispatch, not recurring analytics |
| `kyc-screener`, `governance-executor`, audit/fraud/withdrawal policy agents | Core in-process swarm and some Beat declarations | Core identity, policy, and financial control domains; execute in a worker, not the gateway request process |
| Oracle node/settlement and consensus | Core swarm and core Celery settlement; VITChain owns consensus epochs | VITChain owns chain consensus/oracle state transitions; core submits and reads through its API |
| Tachyon challenges, manifest verification, health/GC | Core lifespan, core Celery Beat, and VIT-Storage lifespan | VIT-Storage owns storage integrity and maintenance; core sends authenticated requests only when needed |
| Ticker sync, Telegram digest, generic workflow dispatch | Core `TaskSubsystem` / workflow dispatcher | Core-owned capabilities; recurring execution belongs in one external worker or a coordinated scheduler |
| Chain DB snapshot | Core `TaskSubsystem` | VITChain/backup owner; current core implementation runs `pg_dump` and optional Dropbox upload |

### Active Core Web Schedules

The deployed gateway had no `ENABLED_AGENTS` override, so the coordinator's default 11-agent set is the relevant current schedule. All use the core Postgres engine; external dependencies are included below. The duplicated Celery schedules are configured in source but are not currently executing in production because no core worker is deployed.

| Job | Schedule | Current execution / dependencies | Duplicate status |
| --- | --- | --- | --- |
| `performance-monitor` | Every 30 min | Core APScheduler; Postgres settled predictions and model metadata | Exact same agent also in Beat every 30 min |
| `live-match-tracker` | Every 120 sec | Core APScheduler; Football-Data API, Postgres, IoT event broadcast | No matching Beat entry; also overlaps settlement responsibilities |
| `network-guardian` | Every hour | Core APScheduler; service/storage probes and Postgres activity records | Beat `agents.tachyon_health` invokes the same agent hourly |
| `weight-optimizer` | Every 6 hours | Core APScheduler; Postgres model metrics and weights | Beat `agents.merit_calculator` invokes the same agent daily |
| `match-scout` | Every 10 min | Core APScheduler; Postgres fixtures/insights and VIT-AI calls | Exact same agent also in Beat every 10 min |
| `fixture-sync` | Every 6 hours | Core APScheduler; sports provider APIs and Postgres | No matching Beat entry |
| `oracle-node` | Every 10 min | Core APScheduler; Postgres oracle rows and VITChain/network calls | Beat `agents.oracle_sentinel` invokes the same agent every minute |
| `kyc-screener` | Every 10 min | Core APScheduler; identity/KYC records and provider checks | No matching Beat entry |
| `academic-tutor` | Every hour | Core APScheduler; user/activity data and AI calls | No matching Beat entry |
| `governance-executor` | Every 10 min | Core APScheduler; governance and proposal records | No matching Beat entry |
| `retrain-trigger` | Every 12 hours | Core APScheduler; model-health state, may dispatch/inline-run training | Overlaps model retraining intent; not the same task as daily settled-data retrain |

If `ENABLED_AGENTS=all` is set, these additional registered agents also schedule. They were not in the production default set at audit time.

| Conditional agent | Schedule | Dependencies / overlap |
| --- | --- | --- |
| `accumulator-publisher` | Every 2 hours | Postgres prediction/odds data |
| `analytics-reporter` | Daily | Postgres platform statistics |
| `audit-sentinel` | Daily | Postgres audit records; overlaps Beat audit sentinel at a different cadence |
| `fixture-gap` | Every 30 min | Sports provider APIs and Postgres |
| `fraud-review` | Every 15 min | Financial activity and risk inputs; overlaps Beat fraud review |
| `marketplace-audit` | Every 30 min | Marketplace records and review APIs |
| `model-promoter` | Every 2 hours | Postgres model metadata; AI/model ownership |
| `news-sentinel` | Every 20 min | News/AI providers and Postgres |
| `odds-anomaly` | Every 8 min | Odds provider APIs and Postgres |
| `prediction-moderator` | Every 20 min | Prediction records and AI moderation |
| `revenue-optimizer` | Daily | Subscription/finance records |
| `self-healing` | Every 5 min | Reads agent/system health state; can trigger recovery work |
| `withdrawal-gatekeeper` | Every 5 min | Withdrawal/policy records; overlaps Beat withdrawal gate |

### Core Celery Beat Schedule (Configured, Not Deployed)

| Beat task | Schedule | Dependencies / boundary | Overlap |
| --- | --- | --- | --- |
| `agents.run_prediction` | Every 5 min | Postgres and prediction/model code | Prediction agent is not in default 11; duplicates if `ENABLED_AGENTS=all` |
| `agents.performance_monitor` | Every 30 min | Postgres prediction/model metrics | Exact duplicate of active core APScheduler job |
| `agents.oracle_sentinel` | Every minute | Postgres and VITChain/oracle calls | Same agent as active `oracle-node`, different cadence |
| `agents.market_scout` | Every 10 min | Postgres and AI calls | Exact duplicate of active `match-scout` |
| `agents.merit_calculator` | Daily at 01:00 Africa/Lagos | Postgres model weights | Same agent as active `weight-optimizer`, different cadence |
| `agents.fraud_review` | Every 15 min | Postgres financial activity and risk inputs | Not in default 11; duplicates if all agents enabled |
| `agents.withdrawal_gate` | Every 5 min | Postgres withdrawal requests and policy state | Not in default 11; duplicates if all agents enabled |
| `agents.audit_sentinel` | Every 30 min | Postgres audit records | Not in default 11; duplicates if all agents enabled |
| `agents.tachyon_health` | Every hour | Storage/network checks plus Postgres agent activity | Same `NetworkGuardianAgent` as active `network-guardian` |
| `ml.evict_stale_models` | Every 10 min | Worker-process RAM and local model registry | Model-specific; belongs in VIT-AI |
| `ml.retrain_from_settled` | Daily at 03:30 Africa/Lagos | Postgres settled predictions, sklearn models, Redis status | Overlaps `retrain-trigger`/`retrain_models_task` intent |
| `ml.evaluate_models` | Daily at 04:00 Africa/Lagos | Postgres settled predictions and Redis metrics | Model-specific; belongs in VIT-AI |
| `reports.daily_summary` | Daily at 06:00 Africa/Lagos | Postgres reporting data | Core-owned report generation |
| `reports.weekly_model_accuracy` | Mondays at 05:00 Africa/Lagos | Postgres model metrics | Model-specific aggregation; coordinate with VIT-AI evaluation |
| `tachyon.health_check` | Hourly | Storage API and Redis status | Overlaps `agents.tachyon_health` and storage-owned health/verification |
| `tachyon.gc_orphans` | Daily at 02:00 Africa/Lagos | Storage API garbage collection | Storage maintenance belongs in VIT-Storage |
| `oracle_settlement_check` | Every 5 min | Core Postgres oracle/consensus tables and VITChain settlement bridge | Overlaps oracle-node orchestration; ownership should split at chain state transition |

### Other Recurring or Long-Lived Loops

| Job | Schedule | Current execution / dependencies | Ownership note |
| --- | --- | --- | --- |
| System ticker sync | Every 60 sec | Core kernel task loop; Postgres and Firestore | Core presentation aggregate; move execution to core worker |
| Automatic settlement | Every 15 min | Core kernel task loop; Postgres settlement service | Core may orchestrate; VITChain owns consensus finality |
| Telegram digest | Daily at 09:00 UTC | Core kernel task loop; Postgres and Telegram | Core notification job |
| Chain snapshot | First run after 5 min, then every 6 hours | Core kernel task loop; `pg_dump`, local temp disk, optional Dropbox | Chain/backup owner; expensive process work does not belong in gateway |
| Tachyon challenge scheduler | Initial delay 60 sec, then configured `CHALLENGE_INTERVAL_S` | Core lifespan; storage manifests and Postgres | Misplaced; VIT-Storage owns challenge policy |
| Tachyon verification worker | Every hour | Core lifespan; storage manifests and provider checks | Duplicate domain responsibility with VIT-Storage verification worker |
| VITChain consensus epoch | Every configured epoch (15 sec by default) | VITChain lifespan; chain database and consensus state | Correct service owner; no distributed lease, so multiple replicas risk duplicate epochs |
| VIT-Storage verification worker | Every hour | VIT-Storage lifespan; storage DB/provider manifests | Correct owner; needs replica coordination/idempotency before scaling |
| Gateway watchdog / kernel health supervision | 60 sec watchdog and 30 sec kernel health cycle | Core process health checks, service probes, DB/Redis checks | Keep only cheap bounded liveness/diagnostics in gateway; not a business scheduler |
| Resource-platform Redis scheduler | Polls every 10 sec; its CRON implementation allows one run per 60 sec | Core `ResourcePlatformSubsystem`; Redis schedule hash and task queue | Active poller, but no application call sites for `schedule_cron`/`schedule_delayed` were found. Schedule check/update is not an atomic claim, so replicas can enqueue the same due job. |
| Resource-platform workers | Two workers per core process; poll queue every 1 sec | Core process; Redis priority queues | Current execution body is a placeholder (`sleep(0.1)`); actual registry/handler dispatch is commented out. Not a real replacement for Celery domain jobs. |
| Workflow dispatcher | Polls its in-memory priority queue every 1 sec; max queue 500, concurrency 8, per-task timeout 30 sec, up to 3 retries | Core lifespan; registered async handlers, process memory | Concurrency and queue are bounded, but queued/task state is not durable across restart and each replica has independent in-memory state. |
| Exchange-rate refresh loop | Every 30 min | `exchange_rate.start_rate_refresh_loop`; external FX API and Postgres | Function is defined, but no caller was found; treat as dormant, not deployed work. |

The coordinator can enable all 24 registered agents with `ENABLED_AGENTS=all`; that activates the 13 conditional agents above in addition to the 11 defaults. The separate `PredictionAgent` is Celery-only, and `ModelTunerAgent` exists in source but is not registered by the coordinator. Production did not have the all-agents override at audit time.

`CHALLENGE_INTERVAL_S` is 3600 seconds (one hour). The resource-platform scheduler is started by the registered kernel subsystem even though no production schedule-creation call sites were found. The VIT-AI `TrainingManager` restores and stores Redis-backed job records, but the inspected code has no recurring trainer/consumer; its presence is not evidence that AI training is running in VIT-AI.

Core's default swarm selection starts 11 agents: `performance-monitor`, `live-match-tracker`, `network-guardian`, `weight-optimizer`, `match-scout`, `fixture-sync`, `oracle-node`, `kyc-screener`, `academic-tutor`, `governance-executor`, and `retrain-trigger`. Celery Beat separately declares prediction, performance, oracle, market scout, fraud, withdrawal, audit, ML, report, Tachyon, and settlement schedules.

## Production Findings

- Render reported repeated `server_failed` events with `HTTP health check failed (timed out after 5 seconds)`. A separate event reported `nonZeroExit: 137`, consistent with the process being killed under memory pressure.
- At 19:08 UTC, gateway `/ping` completed in 5.793 seconds, then Uvicorn shut down; Render logged the instance restart six seconds later. In that same interval, kernel database health and agent jobs logged pool checkout timeouts.
- A four-hour log sample contained 17 SQLAlchemy pool timeout lines across seven modules, including `swarm_orchestrator`, live-match tracking, match-scout, oracle, governance, ticker sync, and model maintenance.
- The deployed gateway has one instance, `/ping` as its Render health route, and `autoDeploy=no`. Its live environment did not contain `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, or `ENABLE_IN_PROCESS_SCHEDULERS`; code defaults therefore remain pool size 2, overflow 1, checkout timeout 10 seconds, and all in-process schedules enabled.
- The DB-free `/ping` handler itself is lightweight, but one observed request exceeded the health limit while the shared event loop and process were under background workload. Pool starvation is confirmed; memory exit 137 and the observed slow ping indicate broader process saturation as well. The logs do not prove that DB checkout alone blocked that request.
- Core's deployed environment used the old AI/storage/frontend hostnames. `VIT_AI_URL` and `VIT_CHAIN_URL` were absent, so source fallbacks also pointed at old hosts. Render currently assigns `vit-ai-z3d4.onrender.com`, `vit-chain-5bd9.onrender.com`, and `vitstorage.onrender.com`.
- Render's live metadata showed empty health-check paths for AI, chain, and storage, despite their repository blueprints declaring `/health` or `/ping`. Storage source exposes `/health`, while its blueprint declares `/ping`; this contract needs reconciliation in the storage repository and Render settings.
- The gateway's `ENABLE_IN_PROCESS_SCHEDULERS` variable was not configured and was not previously read by code. The flag is now implemented and explicit in the local blueprint, but remains `true` until a replacement scheduler is provisioned.
- The core blueprint defines a free-tier worker, but no such worker is currently deployed. The API did not expose a production connection budget for all services, so the shared database's aggregate connection ceiling remains unverified.

### PostgreSQL Connection Budget

Use this upper-bound model for every service attached to a given database:

```text
maximum application connections ~= sum over services(
    instances * OS processes per instance * (pool_size + max_overflow)
) + migrations + deploy overlap + admin/monitoring clients
```

Known and unknown inputs:

- Core currently has one Render instance and one Uvicorn worker. Its production environment did not set pool variables, so the code defaults to 2 persistent + 1 overflow = at most 3 pool slots for that engine/process. A prior local draft used 5+5 (10 slots); that override was removed and must not be deployed without an aggregate budget.
- VITChain has one Render instance. Its source defaults `DB_POOL_SIZE` to 10; the complete effective overflow/process configuration and the production database attachment were not established in this audit.
- VIT-Storage has one Render instance. Its source does not specify explicit PostgreSQL pool bounds in the inspected engine constructor; the deployed database backend/URL is not included here.
- VIT-AI's inspected job manager uses Redis, but a full resource-level database attachment inventory was not available from the public service source.
- The core Celery worker is absent, so its process/pool contribution is currently zero. If created with concurrency 2, its actual engine/pool multiplication must be verified rather than estimated from the web process.
- The Render API did not provide the database provider's current max-connection setting or all environment-group attachments in a form that allowed a safe aggregate calculation.

Do not introduce or deploy the 5+5 setting, or create a worker, until each database attachment, pool bound, process count, deployment overlap, and provider limit have been reconciled.

## Target Architecture

```text
Clients -> VIT Network Core
            auth, API routing, policy, orchestration, bounded dispatch
                 |             |              |
                 v             v              v
              VIT-AI         VITChain       VIT-Storage
          inference/jobs   consensus/oracle  integrity/GC

Core-owned recurring work -> one coordinated worker/scheduler
```

Target ownership is service-local: AI owns model training/evaluation/retraining and inference; VITChain owns consensus and oracle state transitions; VIT-Storage owns challenges, verification, and storage maintenance; core retains authentication, policy, settlement orchestration, user-facing APIs, and small dispatch tasks. A separately provisioned worker may execute core-owned jobs, but it must not become a second owner for service-local schedules.

## Render Worker Feasibility

The core blueprint declares `vitnetwork-worker` with `plan: free`, but Render's [Free instances documentation](https://render.com/docs/free) says Free instances are available only for Static Sites, Web Services, Postgres, and Key Value; other service types do not support Free instances. Background Workers are therefore **not deployable on the currently configured Free plan**. The official [Background Workers documentation](https://render.com/docs/background-workers) describes them as continuously running, queue-consuming services, not an incoming-traffic service. Cron jobs can use a compute plan, but are not a substitute for a continuously available Celery worker.

This is a blueprint/plan mismatch. The API's lack of a deployed `vitnetwork-worker` is consistent with it, but available evidence does not establish that the Free plan was the specific reason the worker was never created.

The current available-plan choices are:

- Upgrade/provision a paid Background Worker after checking aggregate Postgres connections and memory.
- Keep the existing web-process schedules temporarily while reducing their concurrency and workload, then move service-specific jobs into AI/chain/storage only after those service owners are implemented and coordinated.
- Evaluate an external scheduler/queue only if its availability, secrets handling, retries, and single-run coordination are acceptable; do not assume an external free cron has exactly-once semantics.

Do not set `ENABLE_IN_PROCESS_SCHEDULERS=false` while no verified replacement exists.

Before a production cutover:

1. Select and provision a supported paid worker or verified external scheduler. Confirm memory and DB pool fit the shared database limit.
2. Move each current loop to its intended owner, with durable task IDs, idempotency keys/unique constraints, bounded retry/backoff, request deadlines, and clear shutdown cancellation.
3. Use a single Beat instance or a Redis/DB lease with expiry and fencing for any schedule that can run on multiple replicas. Render's current one-instance setting is not a future-proof exactly-once guarantee.
4. Apply the corrected service URLs and health-check paths to the actual Render services. Do not disable gateway scheduling until replacement jobs are visible and verified.
5. Test sustained concurrent API and job load; require `/ping` p95 below 1 second, no health-check failures, no pool timeout lines, and no exit-137 restarts over an observation window.

## Local Changes and Verification

- Added `ENABLE_IN_PROCESS_SCHEDULERS` parsing and guarded kernel/gateway scheduler startup/shutdown. Default remains enabled for backwards compatibility.
- Corrected core Render URL values and source fallback hosts to the actual Render service domains; corrected storage registry probes to `/health`.
- No pool increase is configured locally or deployed. The gateway retains its code defaults of pool size 2 plus overflow 1 until an aggregate connection budget is verified.
- A 5+5 pool was considered earlier but is not retained. Any future pool change requires a verified aggregate connection budget across services, worker concurrency, replicas, deployment overlap, and administrative clients.
- Added the durable scheduled-run/attempt ledger, fail-closed token API, single daily read-only health-audit runner, and a staging-only GitHub Actions workflow gated by `VIT_SCHEDULER_STAGING_ENABLED=true` plus manual confirmation.
- `pytest --noconftest -q tests/test_scheduled_job_runs.py`: 17 passed against temporary SQLite/mock HTTP, covering unique daily enqueue, concurrent claims, lost-response claim/claim-next retries, prior-date recovery, bounded retries, lease recovery/exhaustion, history, HTTP auth, production denial, and staging URL guards.
- Python compile, Render/GitHub workflow YAML checks, migration upgrade/re-upgrade/downgrade and model-column parity, migration revision graph checks, and `git diff --check` passed.
- Existing `retrain-cron.yml` and `keep-alive.yml` were not changed or disabled. No staging variables/secrets were configured, no workflow was triggered, no migration was applied, and no Render deployment or environment mutation was performed.
- Production is not verified after these local changes. Core still has `autoDeploy=no`; the database migration and staging workflow require explicit staging setup before they can be exercised.

## GitHub Actions Staging Pilot

### Existing Action Schedule Ownership

| Workflow | Schedule | Authoritative owner | Work / classification | Cutover state |
| --- | --- | --- | --- | --- |
| `keep-alive.yml` | Every 5 min | GitHub Actions | Lightweight `/ping` wake probe; suitable for Actions, no DB/job execution | Existing production behavior retained unchanged |
| `retrain-cron.yml` | Daily at 03:00 UTC | GitHub Actions today | Manifest-driven local model training and optional Tachyon upload; AI workload with storage side effect | Existing workflow retained unchanged; not migrated here because it lacks durable idempotency/history and overlaps model-maintenance ownership |
| `staging-scheduled-health.yml` | Daily at 03:23 UTC | GitHub Actions | Read-only staging probes; job state in the core ledger | New, disabled by default; not a production replacement schedule |

No other `.github/workflows/*` files declare cron schedules. Core APScheduler/Celery schedules, VITChain consensus, and VIT-Storage integrity loops remain with current owners; none were disabled or moved in this pilot.

| Schedule | Authoritative scheduler | Execution owner | Scope | Idempotency/recovery |
| --- | --- | --- | --- | --- |
| Daily at 03:23 UTC | `.github/workflows/staging-scheduled-health.yml` | Ephemeral GitHub-hosted runner; durable state in the core scheduler API | Read-only GET probes to staging `/ping` and `/health` endpoints only | `daily_service_health` unique by UTC date; atomic claim-next, 15-minute lease, 3 attempts, exponential delays capped at 5 minutes, per-attempt history, expired-lease recovery |

The workflow requires the repository variable `VIT_SCHEDULER_STAGING_ENABLED=true`; `workflow_dispatch` additionally requires `confirm_staging_run=true`. It targets the `staging` GitHub Environment and needs these environment variables: `STAGING_GATEWAY_URL`, `STAGING_VIT_AI_URL`, `STAGING_VIT_CHAIN_URL`, and `STAGING_VIT_STORAGE_URL`. It also needs the GitHub Environment secret `STAGING_GITHUB_SCHEDULER_TOKEN`, mapped to the gateway's `GITHUB_SCHEDULER_TOKEN` setting. URLs are validated as HTTPS and must contain `staging` in the hostname. The API is hard-disabled unless `ENVIRONMENT` is `testing` or `staging`, and returns `503` until its dedicated token is configured.

The runner reports only service label, HTTP status, and latency. It does not print auth headers, token values, response bodies, or raw exception messages. A failed audit persists an attempt and fails the Actions job, which emits a GitHub error annotation and uses normal Actions failure notifications. Daily UTC keys allow later retries without relying on precise cron timing; repeated deliveries on the same UTC date return the existing record. `claim-next` recovers the oldest due prior record before creating competing work; runner-generated claim tokens are stored only as SHA-256 hashes and allow retrying the same claim after a lost response. The API run ledger does not execute domain tasks.

This pilot is additive and staging-only. The existing five-minute keep-alive and daily `retrain-cron.yml` workflow remain unchanged; they have not been disabled or converted. Production AI training, settlement, consensus, oracle finality, and storage maintenance remain with their current service owners until each gets a separate tested migration plan. No production workflow should call this API or use a production URL.

The API schema migration is `zz13_scheduled_job_ledger`, following the single current Alembic head. It was tested with an in-memory SQLite upgrade, repeat upgrade, and downgrade. It has not been applied to any Render database. The Action remains disabled until a staging database is migrated, staging environment variables and token are configured, and the staging endpoint contract is verified.

## Remaining Risks

- The architecture migration is not complete: gateway schedules remain enabled and the production worker is absent.
- AI, chain, and storage repositories are remote and unchanged locally. Their Render-assigned URL defaults, health paths, storage `/ping` mismatch, and scheduler coordination still require changes in those repositories and application of their blueprints.
- Exactly-once execution is not guaranteed across replicas. Existing APScheduler loops, storage workers, and embedded Celery Beat lack a distributed leader/lease or universal idempotency key.
- Current free-tier cold starts cause multi-second service health/integration requests; asynchronous clients need short timeouts and graceful degradation rather than retries that multiply load.
- Aggregate Postgres connection limits and per-service pool allocation remain to be verified before raising pool capacity in production.
- The new API and workflow have only local/temp-database tests; recovery against a real staging gateway, GitHub secrets/environment protection, GitHub cron delay, and runner loss during an HTTP request remain unverified.
- The attached `.env` contained credentials. Rotate the GitHub PAT, both Render API keys, and the admin password; do not put those values in workflow YAML or logs.