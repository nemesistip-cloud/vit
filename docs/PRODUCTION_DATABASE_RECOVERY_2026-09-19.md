# VIT Production Database Recovery

**Date:** 2026-09-19  
**Gateway:** `srv-d8sipgjeo5us73eis7hg`  
**Database:** `dpg-da2m9j3m8hqs73dvpjr0-a`

## DATABASE

| Field | Result |
|---|---|
| Database ID | `dpg-da2m9j3m8hqs73dvpjr0-a` |
| Name | `vitnetwork` |
| Status before recovery | `suspended` |
| Status after resume request | Still `suspended` |
| Suspension reason | `billing` |
| Region | `oregon` |
| Plan | `free` |
| PostgreSQL version | `18` |
| Disk autoscaling | Disabled |
| Disk usage/capacity | Not exposed by the Render resource API response |
| Expiry | 2026-09-18 08:09 UTC |
| Replacement database | Not created |

The database is the only Postgres instance visible to the Render account and shares the gateway's `oregon` environment. Its hostname is the one used by the existing gateway `DATABASE_URL` linkage. Render logs show the gateway failure as an `asyncpg` DNS/connection failure while this database is suspended.

## RECOVERY

The supported Render resume operation was sent to the original database ID and accepted with HTTP 202. The official Render CLI uses the same resume endpoint. Repeated status checks continued to report `suspended` with `suspenders=[billing]`; application code cannot resolve this state. Billing/plan recovery in Render is required before the database can accept connections.

No destructive operation, plan mutation, database replacement, migration, restore, or production data modification was performed.

## DATA PRESERVATION

Render exposes one logical export created at `2026-09-18 08:27 UTC`. It was downloaded securely and confirmed to be a PostgreSQL directory-format archive containing `toc.dat` and many table data files. This proves an export exists and production data is preserved outside the suspended instance.

Render recovery metadata reports `recoveryStatus=NOT_AVAILABLE`, so PITR was not available through the API. Disk usage and capacity were not available from the database metadata endpoint. The archive was not restored or modified. Exact row counts remain unavailable because the database is suspended and the local environment does not have `pg_restore`.

| Data item | Count/status |
|---|---|
| Users | Not queried; database unavailable |
| Predictions | Not queried; database unavailable |
| Transactions | Not queried; database unavailable |
| Audit records | Not queried; database unavailable |
| Schema/export | PostgreSQL directory archive present |

## APPLICATION

- `DATABASE_URL` configured in gateway: **yes**, linked to the original Render Postgres resource.
- `REDIS_URL` configured in gateway: **no** in the current Render environment variables.
- Gateway connected: **no**, because the database is suspended/unreachable.
- Worker database linkage: declared in `render.yaml` to the same `vitnetwork` resource; live worker connectivity was not independently verified.
- Migrations current: **not verifiable** while the database is unavailable. No migration was run.

## LIVE HEALTH BEFORE DATABASE RECOVERY

| Endpoint | Result |
|---|---|
| `/ping` | HTTP 200 |
| `/health` | HTTP 200, `status=degraded`, `db_connected=false` |
| `/readiness` | HTTP 500 before the DNS-aware fix is deployed/verified against this state |
| `/deep-health` | HTTP 500 before the DNS-aware fix is deployed/verified against this state |

The gateway deployment containing the application hardening is live at commit `d56947e3b360258bcfb73fb64dd9bf9f37618401`. The database remains the external blocker.

## DEPENDENTS

Repository and Render configuration identify these consumers of the same database resource:

- `vitnetwork` gateway
- `vitnetwork-worker`
- authentication and admin routes within the gateway
- prediction, training, and background task paths within the gateway/worker

The AI, chain, storage, and explorer services responded to their own health endpoints, but database-backed gateway functionality could not be exercised.

## NEXT REQUIRED OPERATION

1. Resolve the Render billing suspension for `vitnetwork` or have the workspace owner restore the eligible production plan.
2. Recheck the original database until status is available; do not create a replacement database.
3. Use the existing internal connection metadata for a read-only connectivity test.
4. Run read-only schema and count queries, then inspect Alembic revision state.
5. Verify gateway and worker connections, followed by `/readiness`, `/deep-health`, real admin login, and the capability matrix.
6. Retain the existing logical export as the recovery fallback and document its storage location and retention policy.