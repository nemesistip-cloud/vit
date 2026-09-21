# VIT Ecosystem Gap Analysis

## Executive Summary

VIT has substantial structural breadth but limited proof of integrated production behavior. Phase 2C now has green regression and a router-backed three-node proposal, signed-vote, 2/3 quorum, certificate finality, persistence, and restart/reconnect path. The highest-risk remaining gaps are adversarial network scenarios, validator admission/selection policy, data lineage, durable exchange settlement, and deployment drift.

## P0 Critical

1. **Adversarial multi-node consensus/finality is not runtime-proven.** The real integration test now proves a healthy three-node proposal, signed votes, 2/3 quorum certificate, finality, persistence, and restart. Partition, timeout, conflicting-proposal, and insufficient-quorum behavior still need live-node tests.
2. **Consensus is not runtime-proven.** Producer, voting, finalizer, verifier and slashing modules exist, but there is no verified multi-node quorum, conflicting-block, invalid-message, or restart test result.
3. **Render worker is not present in live inventory.** The worker is declared in source but its deployed runtime could not be confirmed.

## P1 High

- Worker deployment is declared but absent from the returned Render service inventory; production scheduling/retry execution is therefore unverified.
- AI provider operation is not proven from environment configuration alone; fallback can return a fixed offline message.
- Sports outputs cannot be called live intelligence solely from historical CSV/JSON/training data; provider freshness, source attribution, and prediction persistence need runtime proof.
- Exchange matching exists as a package, but durable balances, settlement, withdrawals, fees, authorization, concurrency controls, and recovery are not demonstrated.
- Public service health and critical endpoint checks were not completed against deployed URLs in this pass.

## P2 Medium

- Explorer API/client contract and pagination/filtering need executable contract tests.
- Frontend route actions need Playwright coverage tied to real backend responses.
- Database model usage is broad but active/obsolete/seed-only tables are not classified by query evidence.
- Rate limiting, CSRF posture, security headers, admin authorization, file-upload controls, and sensitive logging require focused verification.
- Model calibration, drift, benchmark comparison, and model-version lineage are incomplete.
- P2P peer discovery, propagation, sync, and fork recovery need adversarial integration tests.
- Marketplace vendor/catalog/order flows need complete integration tests and payment webhook verification.

## P3 Low

- Documentation and architecture claims should be reconciled with this baseline.
- Remove or clearly label demo/fallback language in user-facing capability claims after behavior is verified.
- Add operational dashboards and deployment evidence links after core paths pass.

## Fake-completeness findings

- Server-side handshake signature verification uses the canonical Keccak/ECDSA contract with freshness and nonce replay protection; real daemon-to-router acceptance remains unverified.
- The normal test command now collects both `tests` and `vit_chain/tests`; 555 tests collect and the full suite passes 552 with 3 skips. Consensus unit/negative tests and one real integration test pass.
- Explicit demo behavior: detached node mode prints “not implemented in this demo”.
- Fixed fallback response: “Intelligence layer is offline. Running on offline failover buffer.”
- Historical/seed data exists under `data/`; it is not evidence of live provider ingestion.
- Many page and route names exist without proof that their actions persist or reach production services.
- Presence of 30 migrations and numerous models does not prove all tables are active or current.

## Security findings

| Area | Status | Evidence |
|---|---|---|
| Secrets in local env | PRESENT, not exposed | `.env` contains `GITHUB_PAT` and `RENDER_API_KEY`; values were withheld |
| Render secret variables | PRESENT | API metadata showed names only; values withheld |
| Auth/JWT modules | PRESENT / PARTIAL | auth hooks, JWT tests and module code exist |
| Authorization/RBAC | PRESENT / PARTIAL | RBAC modules/tests exist; endpoint-wide proof missing |
| Node signing/authentication | PARTIALLY_IMPLEMENTED | signed public-key handshake, freshness, and replay protection pass focused tests; unknown-peer policy remains open |
| Rate limiting | UNKNOWN | needs endpoint/runtime verification |
| CORS/CSRF/security headers | UNKNOWN | needs focused configuration/runtime check |
| Sensitive logging | UNKNOWN | needs log review with redaction tests |
| SQL injection/input validation | UNKNOWN | broad endpoint audit not completed |

## Status interpretation

`FULLY_IMPLEMENTED` is intentionally rare because it requires a connected path plus runtime/test evidence. A source module, route, model, or UI button alone is not sufficient.
