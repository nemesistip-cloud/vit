# Internal Dependency Graph — VIT Network (generated)

This file summarizes the primary services, runtime roles, and integration links discovered in the workspace during Phase 1 audit.

## Services (from render.yaml)

- vit (web; in-process schedules enabled, GitHub Actions handles periodic workflows)
  - DATABASE_URL -> vitnetwork
  - REDIS_URL -> vitnetwork-redis
  - VIT_AI_URL -> https://vit-ai-z3d4.onrender.com
  - TACHYON_URL -> https://vitstorage.onrender.com
  - VITE_GATEWAY_URL -> https://vit-fwjz.onrender.com
  - VITE_AI_URL -> https://vit-ai-z3d4.onrender.com
  - VITE_STORAGE_URL -> https://vitstorage.onrender.com
  - VITE_CHAIN_URL -> https://vit-chain-5bd9.onrender.com

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

- `app/worker` — Celery task definitions; no separate paid worker is provisioned.

## Key Config / Defaults

- `backend/app/config.py` resolves runtime URLs via env vars: `VIT_AI_URL`, `VIT_STORAGE_URL`, `VIT_CHAIN_URL`, `REDIS_URL`, `DATABASE_URL`.
- Frontend Vite build-time variables are baked in via `VITE_*` env vars from `render.yaml`.

## Observations / Critical Links

- `app/` depends on `vit_chain` (local package) for chain operations.
- Redis (`vitnetwork-redis`) is critical across caching, task queues, and rate-limiting.
- Alembic migrations exist; production historically had a missing migration (`22c85e91a8d9_add_remaining_module_tables`).
- Render config bakes `VITE_*` URLs into front-end build, so moving service hosts requires updating `render.yaml` or frontend env.

## Next actions

1. Keep this map in sync with Render and GitHub Actions when service URLs change.
2. Verify production workflows after updating GitHub Actions secrets.

