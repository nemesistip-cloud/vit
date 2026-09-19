# VIT Postgres Failover Runbook

**Purpose:** Recover VIT when the primary Render Postgres instance is suspended or unavailable without silently replacing production data.

## Current incident

- Primary: `dpg-da2m9j3m8hqs73dvpjr0-a` (`vitnetwork`)
- Region: `oregon`
- Plan: `free`
- PostgreSQL: `18`
- State: `suspended`
- Suspension: `billing`
- PITR: `NOT_AVAILABLE`
- Logical export: available from 2026-09-18
- Gateway and worker: both reference the Render database resource named `vitnetwork`

The correct first action remains billing recovery and resume of the original instance. A replacement is a recovery operation, not a normal deployment operation.

## Safe state machine

```text
PRIMARY_HEALTHY
  -> PRIMARY_SUSPENDED
  -> RESUME_REQUESTED
  -> PRIMARY_HEALTHY                 (preferred path)
  -> RECOVERY_ASSETS_VALIDATED       (only if resume is impossible)
  -> CANDIDATE_CREATED
  -> EXPORT_RESTORED
  -> SCHEMA_AND_COUNT_VALIDATED
  -> CANDIDATE_SHADOW_VERIFIED
  -> CUTOVER_APPROVED
  -> SERVICES_RECONNECTED
  -> POST_CUTOVER_VERIFIED
  -> OLD_PRIMARY_RETAINED
  -> OLD_PRIMARY_RETIRED             (manual approval only)
```

No state may skip directly from `PRIMARY_SUSPENDED` to deletion. The old instance is retained until the new database has passed application, data-integrity, authentication, worker, and admin checks.

## Automatic controller policy

The controller may run automatically for **observation and notification**:

1. Inspect Render Postgres status, suspension reason, region, plan, version, expiry, and disk metadata.
2. Confirm the gateway and worker point to the same database resource.
3. List logical exports and recovery/PITR availability.
4. Verify the export is downloadable, non-empty, and contains PostgreSQL archive metadata.
5. Emit an incident with a request ID and recovery checkpoint.
6. Request resume of the original database once per incident, with idempotency protection.

The controller must stop and require explicit operator approval before:

- creating a replacement database;
- restoring an export into a candidate;
- changing `DATABASE_URL` or dependent service environment variables;
- promoting a candidate to production;
- deleting or recycling the old database.

This protects against stale exports, wrong-region databases, partial restores, and accidental data loss.

## Candidate requirements

If the original instance is unrecoverable and a replacement is approved:

- Same Render region as the gateway: `oregon`.
- PostgreSQL major version compatible with the export: `18` unless restore tooling proves compatibility.
- Non-free production plan with sufficient disk and autoscaling where available.
- Deletion protection and a documented backup/export schedule.
- Candidate receives a distinct name such as `vitnetwork-recovery-<incident-id>`.
- Existing primary remains untouched and suspended until cutover verification completes.

## Restore validation

Restore must be performed into the candidate only. Before promotion, record counts for at least:

- `users`
- `predictions`
- `matches`
- wallet/transaction tables
- `audit_logs`
- `model_metadata`
- validator tables
- `platform_config`
- Alembic revision table

Compare counts and schema objects to the export. Any mismatch blocks cutover. Credentials and connection strings must stay in process memory or secret storage and must never enter logs, Git, screenshots, or reports.

## Cutover gates

The candidate is eligible for promotion only when all gates pass:

- TCP and authenticated PostgreSQL connectivity.
- Required schema and current migration revision.
- Read-only count comparison against the export.
- Gateway `/ping`, `/health`, `/readiness`, and `/deep-health`.
- Real admin login and `/api/auth/me`.
- Invalid credentials and invalid token return `401`.
- Unauthenticated admin endpoint returns `401`.
- Authenticated non-admin endpoint returns `403`.
- Authenticated admin read-only endpoints succeed.
- Worker starts and can connect without running destructive jobs.
- Audit log can record a reversible test action.

Only after these checks may an operator update `DATABASE_URL` for the gateway and worker and allow the normal deployment pipeline to redeploy.

## Old-primary retirement

The old database must not be deleted automatically. Retain it until:

1. The candidate has served successfully through the agreed observation window.
2. Export and candidate counts are archived.
3. Admin, worker, prediction, wallet, chain, storage, and audit checks pass.
4. A fresh export of the candidate succeeds.
5. The workspace owner explicitly approves retirement.

If billing recovery later makes the original database available, prefer restoring it over promoting a replacement because it preserves the authoritative production state.

## Prevention upgrades

- Add a scheduled Render Postgres status/export check.
- Alert before plan expiry and billing suspension.
- Alert on export age, export download failure, and disk pressure.
- Add startup validation that distinguishes missing `DATABASE_URL`, DNS failure, authentication failure, suspension, and migration failure.
- Add a deployment gate that requires `/readiness` before marking the gateway healthy.
- Keep `/ping` process-only; keep `/health` dependency-reporting; keep `/readiness` dependency-gating.
- Add a worker readiness check against the same database resource.
- Store incident checkpoints and export identifiers outside the application database.
- Test restore into an isolated candidate on a scheduled basis.

## Current decision

Do not create or delete a database during this incident. Resolve Render billing suspension first. If that is impossible, obtain explicit approval for a candidate restore from the existing logical export and follow every gate above.
