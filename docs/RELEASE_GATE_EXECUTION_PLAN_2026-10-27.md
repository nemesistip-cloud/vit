# VIT Network Release Gate Execution Plan

_Last updated: 2026-10-27_

## Objective

Establish recoverable production data, safe validator consensus, and reproducible release evidence before expanding settlement or commerce features. No production database cutover or deployment is part of this local implementation plan.

## Priority 0: Production Data Recovery (Operator-Gated)

**Status: blocked outside this workspace.** The current upgrade roadmap records the only Render PostgreSQL resource as suspended/expired, no usable export, and unavailable PITR. A local code change cannot restore that data.

- Create or identify a healthy PostgreSQL recovery target in the Render dashboard.
- Obtain an authorized, restorable export or formally record an approved empty-database recovery decision.
- Validate schema/migration heads, row counts, application-to-database mapping, TLS, and connection limits before cutover.
- Verify `/ready` and persisted application/chain state after recovery.

**Exit criteria:** documented source/target provenance, tested restore, validated data counts, and healthy readiness. Do not deploy application migrations against the unavailable or unverified production database.

## Priority 1: Consensus Safety

**Status: implementation in progress.** Current code forwards proposals to the coordinator, but the coordinator issues precommits directly after proposal validation. The node daemon also creates a second vote after `receive_proposal`. Locks, restart-safe local voting, and justified round changes need explicit invariants and tests. Chain block insertion already uses a nested database transaction; preserve and test its rollback behavior.

- Make proposal validation produce a prevote only.
- Issue a precommit only after a verified prevote quorum for the same chain, height, round, and block hash.
- Reject non-validator local signing identities, cross-chain/stale/malformed votes, duplicate votes, and conflicting votes.
- Preserve a lock across rounds and permit a conflicting vote only with a valid higher-round proof for the locked block; never unlock on timeout alone.
- Persist vote/lock state before broadcast and restore it on daemon restart so the node cannot double-vote after restart.
- Remove duplicate vote generation from daemon gossip and keep both gossip adapters on one coordinator-owned state transition path.
- Finalize only with a verified precommit quorum certificate. Keep block, indexes, and finality state atomic.
- Add unit, persistence, restart, partition, and Byzantine/conflicting-vote tests.

**Exit criteria:** adversarial tests demonstrate no precommit without prevote quorum, no conflicting precommit across rounds/restarts, no finalization below quorum, and no partial block/index writes on failure. A real multi-node run must pass before any production-readiness claim.

## Priority 2: RPC Abuse Controls

**Status: body-size cap exists; rate limiting remains to verify/implement.** `/chain/rpc` currently caps request bodies at 2 MiB. Add bounded per-client request rates using shared deployment storage where available, fail closed or explicitly degrade according to the chain's security policy, and test the 413 and 429 boundaries. Avoid a process-local limiter presented as cluster-wide protection.

**Exit criteria:** oversized requests return 413; bursts over policy return 429; compliant clients work; tests cover proxy-derived client identity and concurrent requests.

## Priority 3: Release Verification

- Run the complete backend suite on the supported Python 3.11 runtime and the frontend production build.
- Run isolated migration/restore, authenticated browser smoke, and deployed health/readiness tests.
- Reconcile chain audit/readiness documents against the verified implementation and test evidence.
- Require a tested backup and rollback plan before production deployment.

**Exit criteria:** CI passes on the supported runtime; browser, multi-node, restore, and deploy smoke gates produce retained evidence; no P0/P1 release blockers remain.

## Work Sequencing

1. Complete local Priority 1 consensus invariants and tests.
2. Implement/test Priority 2 RPC rate limiting if a shared limiter is available in this service boundary.
3. Run focused tests, then all available repository checks; document environment blockers without weakening checks.
4. Stop at Priority 0/3 operator gates when credentials, database access, supported runtime, or browser infrastructure are unavailable. Do not claim those external gates are complete.
