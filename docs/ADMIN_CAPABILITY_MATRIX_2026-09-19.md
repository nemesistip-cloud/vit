# VIT Network Admin Capability Matrix

**Audit date:** 2026-09-19  
**Production commit:** `96414842735933ee37d1a7c0526af0a4895da701`  
**Verification rule:** `Verified` means exercised against production. Code inspection alone is `Not verified`.

| Feature | Frontend Route | API Endpoint | Real Data Source | Admin Permission | Current State | Required Fix | Verified |
|---|---|---|---|---|---|---|---|
| Admin login | `/login` | `POST /api/auth/login` | Production `User` database | Valid active admin credentials | Broken: production returns `500` before credential validation | Restore gateway database connectivity; retest valid and invalid credentials | No |
| Session identity | Admin shell | `GET /api/auth/me` | Production `User` database and JWT | Authenticated user | Blocked by database failure | Retest access and invalid/expired JWT rejection | No |
| Platform overview | `/admin` | `GET /api/system/status` | Users, predictions, validators, wallets | Admin UI role plus API admin policy where applicable | UI is wired; production data blocked | Verify non-empty/empty production states and response schema | No |
| Gateway health | `/admin` and System tab | `GET /api/admin/system/health` | Gateway, database, model registry | `require_admin` | API returns 401 without auth; admin path blocked by login | Verify authenticated health payload and degraded dependency states | No |
| Runtime metrics | System tab | `GET /api/admin/system/metrics` | Request metrics and DB pool | `require_admin` | Frontend wired; unverified in production | Verify metric provenance and null/error states | No |
| Users | Users tab | `GET /api/admin/users` | `User`, `Wallet`, `Prediction` tables | `require_admin` | Backend and UI implemented; unverified | Verify records and pagination against production | No |
| Wallet transactions | Wallet tab | `GET /api/admin/wallet/transactions` | Wallet transaction store | Admin wallet policy | Backend/UI implemented; unverified | Verify read-only records and sensitive-field handling | No |
| Matches | Matches tab | `GET /api/admin/matches` | `Match` table | `require_admin` | Backend/UI implemented; unverified | Verify production fixtures and empty/error states | No |
| Validators | Validators tab | `GET /api/admin/validators`; `POST /api/admin/validators/{id}/reinstate`; `POST /api/admin/validators/{id}/slash` | `ValidatorProfile` and slash events | Read: admin; mutations: super admin | Frontend endpoint mismatch fixed locally; not deployed/verified | Deploy and verify action contracts; never use zero-amount slash as suspension semantics | No |
| Models | Models tab | `GET /api/admin/models` | `ModelMetadata` registry | `require_admin` | Backend/UI implemented; unverified | Verify model health and registry freshness | No |
| Training jobs | Training tab | `GET/POST /api/admin/training-jobs*` | `TrainingJob` and worker state | Admin; mutations policy-dependent | Backend/UI implemented; unverified | Verify read-only jobs first; test safe cancellation only with an existing disposable job | No |
| Configuration | Config tab | `GET/PUT /api/admin/config*` | `PlatformConfig` | Admin mutation policy | Backend/UI implemented; no production mutation attempted | Verify read-only config; use a documented reversible key only | No |
| Audit log | Audit tab | `GET /api/admin/audit-log` | `AuditLog` table | `require_admin` | Backend/UI implemented; unverified | Verify actor, action, resource, result, timestamp, and correlation metadata | No |
| Control plane | Controls tab | `/api/admin/reliability`, `/api/admin/emergency*`, `/api/admin/token-launch` | Watchdog and `PlatformConfig` | Admin; MFA on selected actions | Mutating controls intentionally not exercised while DB/auth is unhealthy | Verify read-only state, then run only approved reversible actions | No |
| API keys | API Keys tab | `GET/PATCH/DELETE /api/admin/api-keys*` | API key store | Admin; destructive policy | Backend/UI implemented; unverified | Verify secret redaction and disable-only workflow | No |
| Marketplace | Marketplace tab | `GET/POST/DELETE /api/admin/marketplace/listings*` | Marketplace listings | Admin; mutations policy-dependent | Backend/UI implemented; unverified | Verify pending records and audit events before any action | No |

## Production Checks Completed

- Render deployment for commit `9641484`: `live`.
- Gateway `/ping`: HTTP 200.
- Gateway `/health`: HTTP 200, `status=degraded`, `db_connected=false`.
- Gateway `/readiness`: HTTP 500, indicating database dependency failure still occurs before the endpoint handler. Render logs identify the cause as `asyncpg` DNS resolution failure (`Name or service not known`).
- Dependent service `/health` checks: AI, chain, storage, and explorer responded HTTP 200.
- Unauthenticated admin endpoints: `/api/admin/system/health` and `/api/admin/reliability` returned HTTP 401.
- Valid and invalid login attempts both returned HTTP 500; no token was obtained and no admin mutation was attempted.

## Next Implementation Phase

1. Correct the Render `DATABASE_URL` host/DNS configuration or restore the referenced production database; do not change application credentials from the codebase.
2. Redeploy the DNS-aware database-failure classifier and verify `/readiness` returns 503 with `database_unavailable` and `Retry-After`.
3. Re-run real admin login, invalid/expired session checks, and all read-only matrix rows.
4. Fix remaining contract mismatches found by live responses, then add targeted regression tests for each verified contract.
5. Exercise only reversible admin actions with an explicit before/after audit assertion.