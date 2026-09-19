# VIT Network Admin Live Verification

**Date:** 2026-09-19  
**Repository:** `nemesistip-cloud/vit`  
**Latest commit:** `8f858fdfed9ce98043bd801a238e066f2417f7b4`  
**Commit:** `Fix admin bootstrap and route-level UX`

## Scope

This verification used the repository's configured environment credentials without recording credential values. It covered the local code path, GitHub repository access, Render service metadata, deployed service reachability, and the focused frontend verification entrypoint.

## Verified Findings

### Source and commit state

- The worktree was on `main`, aligned with `origin/main` at the latest commit.
- The latest commit changes four files: `frontend/src/pages/MatchDetail.tsx`, `frontend_verify.spec.ts`, `main.py`, and `scripts/ensure_admin.py`.
- The commit adds a fixture heading and document title to match detail, serves PWA assets from the FastAPI application, and loads `.env` for idempotent admin bootstrap.

### GitHub access

The configured GitHub credential could enumerate 15 accessible repositories, including:

- `nemesistip-cloud/vit`
- `vitnetwork/vit-ai`
- `vitnetwork/vit-chain`
- `vitnetwork/vit-contracts`
- `vitnetwork/vit-devops`
- `vitnetwork/vit-docs`
- `vitnetwork/vit-explorer`
- `vitnetwork/vit-governance`
- `vitnetwork/vit-mobile`
- `vitnetwork/vit-network`
- `vitnetwork/vit-prophecy`
- `vitnetwork/vit-sdk`
- `vitnetwork/vit-storage`

The repository's Render service definitions point to the expected split repositories for the chain, AI, storage, and explorer services.

### Render control plane

The Render API credential worked. All five services were reported as `not_suspended` with auto-deploy enabled:

| Service | Last metadata update |
|---|---|
| `vitnetwork` | 2026-09-18 12:01 UTC |
| `vit-chain` | 2026-09-17 07:18 UTC |
| `vit-storage` | 2026-09-17 07:09 UTC |
| `vit-ai` | 2026-09-17 07:09 UTC |
| `vit-explorer` | 2026-09-17 07:09 UTC |

### Live runtime

The gateway and all four dependent Render service URLs returned no HTTP response and timed out at the probe limit:

- `https://vitnetwork-nls4.onrender.com`
- `https://vit-chain.onrender.com`
- `https://vit-ai.onrender.com`
- `https://vit-storage-4trt.onrender.com`
- `https://vit-explorer.onrender.com`

Because the gateway did not respond, the admin login endpoint and authenticated admin routes could not be exercised against the live application. No destructive admin actions were attempted.

## Verification Gaps

- Live admin login using `ADMIN_EMAIL` and `ADMIN_PASSWORD`: **blocked by service timeout**.
- Live admin route checks (`/api/admin/system/health`, users, metrics, validators, models, audit log): **blocked by service timeout**.
- Live browser screenshots and console/network audit: **blocked by service timeout**.
- Focused Playwright tests: **not executed**. The package-manager bootstrap was blocked by pnpm's `esbuild` build-script policy; using the existing binary then exposed a duplicate `@playwright/test` module load and produced no test results.
- Frontend TypeScript and production build: **passed**. The build reports a non-blocking warning that `useAuth.ts` is both dynamically and statically imported, so the dynamic import does not produce a separate chunk.

## Upgrade Priorities

1. **Restore and instrument Render runtime availability.** Add deploy/startup logs, an external uptime check, and a smoke test that distinguishes DNS, TLS, cold-start, process-bind, and application failures. A healthy Render control-plane record is not proof that the service is serving traffic.
2. **Make admin bootstrap deploy-safe.** Run `scripts/ensure_admin.py` as an explicit release/one-off step, emit a non-secret health signal for bootstrap completion, and add a post-deploy login smoke test. Avoid silently treating a missing `ADMIN_PASSWORD` as success in production.
3. **Repair the frontend test toolchain.** Pin one Playwright package resolution, remove the duplicate module-loading path, and declare/approve required build scripts in repository configuration so CI can run `frontend_verify.spec.ts` without mutating workspace files.
4. **Run the authenticated admin regression suite after recovery.** Cover login, authorization denial for a non-admin, read-only admin dashboards, audit log visibility, and safe failure behavior when dependent services are unavailable.
5. **Reconcile split-repository releases.** Add a compatibility matrix or coordinated release marker for `vit`, `vit-ai`, `vit-chain`, `vit-storage`, and `vit-explorer`; verify gateway contracts against the deployed commit rather than repository metadata alone.

## Recheck Command Set

After Render recovery, rerun the following checks without printing secrets:

```bash
curl -fsS https://vitnetwork-nls4.onrender.com/ping
curl -fsS https://vitnetwork-nls4.onrender.com/health
curl -fsS -X POST https://vitnetwork-nls4.onrender.com/api/auth/login \
  -H 'Content-Type: application/json' \
  --data "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}"
```

Then use the returned bearer token for read-only `/api/admin/*` checks and run the focused Playwright suite in a clean dependency environment.

## Follow-up Verification — 2026-09-19

Production partially recovered after the initial outage:

- Gateway `/ping`: HTTP 200.
- Gateway `/health`: HTTP 200 with `status=degraded` and `db_connected=false`.
- Gateway `/openapi.json`: still timed out during the probe.
- Explorer and storage returned HTTP 200; chain and AI returned HTTP 404 at `/`, confirming those processes were reachable even though `/` is not a route for them.
- Render reported the gateway deployment as `live` for commit `8f858fdf`.

The admin credential flow was then tested without exposing credentials:

- `/api/auth/login` with the configured admin credentials: HTTP 500.
- `/api/auth/login` with deliberately invalid credentials: HTTP 500.
- `/api/admin/system/health` without credentials: HTTP 401, so the authorization boundary is active.
- `/api/admin/reliability` without credentials: HTTP 401.
- `/api/matches/upcoming`: HTTP 500.

The identical 500 for valid and invalid login, combined with `db_connected=false`, identifies database access failure before credential verification. The local fix in `main.py` now maps SQLAlchemy failures to `503 database_unavailable` with `Retry-After: 15`; it is not yet deployed, so production must be retested after the next deployment.

Local Python regression execution was blocked because the configured interpreter lacks both `pytest` and `sqlalchemy`. `main.py` passes `py_compile`, and the frontend typecheck/build remain passing from the prior verification.