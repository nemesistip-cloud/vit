# VIT Ecosystem Remediation Plan

Phase 2C implementation status: Signed node-facing proposals/votes, 2/3 quorum certificates, finality persistence, and healthy three-node restart/reconnect are verified. The plan remains gated on adversarial consensus scenarios and production validator policy.

## Recommended Implementation Order

### 1. Restore verification foundations (P0)

- Core dependencies are declared in `pyproject.toml`; keep them synchronized with `requirements.txt`.
- `python -m pytest --collect-only -q` collects 555 tests; the current full result is 552 passed, 3 skipped, 0 failed.
- Add a CI gate that fails clearly on collection/import errors.

### 2. Secure and prove node/network startup (P0)

- Server-side signature verification, freshness, and nonce replay protection use the canonical Keccak/ECDSA contract and pass focused real-keystore/client tests.
- `tests/integration/test_real_multinode_consensus.py` proves actual websocket transport, proposal/vote propagation, 2/3 quorum, certificate finality, independent SQLite persistence, restart recovery, and reconnect.
- The existing multi-node test is simulation-only and must not be used as distributed-network evidence.
- Add node startup, handshake rejection, graceful shutdown, restart, and persistence tests.
- Verify P2P peer discovery, message validation, block/transaction receive, and propagation with at least two nodes.

### 3. Prove chain and consensus (P0/P1)

- Execute block creation, validation, transaction state transition, receipt, persistence, and restart recovery.
- Test proposer selection, votes, quorum, finality, conflicting blocks, invalid signatures, malicious messages, slashing, and validator state persistence.
- Expose and smoke-test RPC health, chain height, blocks, transactions, validators, and metrics.

### 4. Reconcile deployment and runtime (P1)

- Verify the reconciled `vitnetwork` database reference against production migration state in a controlled read-only/approved migration window.
- Confirm whether the Celery worker is deployed; verify process, queue, beat schedule, retries, dead-letter behavior, and logs.
- Run health and critical endpoint smoke tests against each Render service; capture deployment version and recent failure state.

### 5. Establish data integrity (P1)

- Build provider matrix with configured, called, persisted, freshness, source attribution, and failure evidence.
- Separate historical/seeded fixtures from production ingestion.
- Add schema fields for retrieval timestamp, source, model version, feature snapshot, and fallback status where absent.
- Verify database migrations against a clean database and current production schema.

### 6. Prove AI/model integrity (P1)

- Verify each configured provider with a safe health/inference probe and explicit timeout/retry behavior.
- Mark external, local, fallback, and mocked responses distinctly.
- Test routing modes, provider failure, fallback, structured output validation, token/latency accounting, caching, and model versioning.
- Add temporal evaluation, calibration/Brier/log-loss reporting, drift checks, and benchmark storage.

### 7. Complete blockchain-backed finance (P1)

- Connect exchange orders to authenticated API, durable balances, settlement receipts, fees, cancellation, history, and recovery.
- Add concurrency/idempotency/risk tests before enabling deposits or withdrawals.
- Define and verify marketplace/payment/vendor boundaries and any Piluno integration; do not infer integration from UI links.

### 8. Integrate frontend against contracts (P2)

- Generate route/API contract coverage for public and protected pages.
- Run Playwright flows for login, dashboard, explorer, wallet, sports, prediction, governance, marketplace, and admin authorization.
- Verify loading/error/empty states, action persistence, real timestamps, and fallback labeling.

### 9. Observability and security hardening (P1/P2)

- Add structured correlation IDs, metrics, traces, queue visibility, provider health, and alertable SLOs.
- Verify secret redaction, CORS/CSRF, security headers, rate limiting, upload validation, SSRF boundaries, SQL input validation, admin authorization, and wallet signing controls.

### 10. Documentation and polish (P3)

- Update README, architecture, roadmap, and API docs from verified behavior.
- Publish a release checklist that requires runtime evidence, not module/file presence.
- Only after the underlying paths pass should cosmetic or UX polish be prioritized.

## Exit criteria for production readiness

- Test collection and all critical unit/integration suites pass in CI.
- Two-node chain test proves authenticated propagation, quorum/finality, persistence and restart recovery.
- Every public critical endpoint has health, auth, validation, error, and contract tests.
- Live provider matrix has recent evidence for calls and persisted data.
- Predictions expose provenance, model version, timestamp, and fallback state.
- Exchange/commerce money movement is authenticated, idempotent, durable, auditable, and risk-controlled.
- Render services, worker, database, Redis, and migrations agree with source configuration and have verified health.
