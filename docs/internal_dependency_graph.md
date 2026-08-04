# Internal Dependency Graph — VIT Network (generated)

This file summarizes the primary services, runtime roles, and integration links discovered in the workspace during Phase 1 audit.

## Services (from render.yaml)

- vitnetwork (web)
  - DATABASE_URL -> vit-postgres-v2
  - REDIS_URL -> vitnetwork-redis
  - VIT_AI_URL -> https://vit-ai.onrender.com
  - TACHYON_URL -> https://vit-storage-4trt.onrender.com
  - VITE_GATEWAY_URL -> https://vitnetwork-nls4.onrender.com
  - VITE_AI_URL -> https://vit-ai.onrender.com
  - VITE_STORAGE_URL -> https://vit-storage-4trt.onrender.com
  - VITE_CHAIN_URL -> https://vit-chain.onrender.com

- vitnetwork-worker (worker)
  - DATABASE_URL -> vit-postgres-v2
  - REDIS_URL -> vitnetwork-redis
  - VIT_AI_URL -> https://vit-ai.onrender.com
  - TACHYON_URL -> https://vit-storage-4trt.onrender.com
  - VITE_* build-time variables same as web

## Repositories / Modules in workspace

- `app/` — Main backend FastAPI app. Integrations:
  - imports `vit_chain` for blockchain endpoints and explorer
  - uses Redis extensively (`app/core/redis.py`, cache, queues, rate limiters)
  - database via `alembic/` and `app/core/persistence`
  - AI integrations via `app/modules/assistant` and `app/services` (VIT_AI_URL)
  - Storage integration via `tachyon/` + TACHYON_URL

- `vit_chain/` — standalone blockchain node library and service.
  - Exposes RPC and models consumed by `app/` (explorer, chain-related endpoints)

- `frontend/` — Vite + React SPA
  - Build-time envs: `VITE_GATEWAY_URL`, `VITE_AI_URL`, `VITE_STORAGE_URL`, `VITE_CHAIN_URL`
  - Calls backend gateway and platform services

- `tachyon/` — storage service with hooks used by `app/` and worker tasks.

- `worker/` and `app/worker` — background tasks and Celery workers.

## Key Config / Defaults

- `app/config.py` resolves runtime URLs via env vars: `VIT_AI_URL`, `VIT_STORAGE_URL`, `VIT_CHAIN_URL`, `REDIS_URL`, `DATABASE_URL`.
- Frontend Vite build-time variables are baked in via `VITE_*` env vars from `render.yaml`.

## Observations / Critical Links

- `app/` depends on `vit_chain` (local package) for chain operations.
- Redis (`vitnetwork-redis`) is critical across caching, task queues, and rate-limiting.
- Alembic migrations exist; production historically had a missing migration (`22c85e91a8d9_add_remaining_module_tables`).
- Render config bakes `VITE_*` URLs into front-end build, so moving service hosts requires updating `render.yaml` or frontend env.

## Next actions

1. Static analysis to produce a service→service call graph (HTTP imports & RPC usages).
2. Identify TODO/FIXME occurrences prioritized by runtime impact.
3. Run tests and lints to surface failing workflows.

