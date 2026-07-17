# VIT Test Coverage Audit

**Date**: 2026-07-08
**Type**: Structural Verification

## 1. Quantitative Inventory

- **Number of Test Files**: 62
- **Estimated Number of Tests**: 362 (`def test_` occurrences)
- **Primary Framework**: Pytest / Playwright (Frontend)
- **Global Coverage**: [FAILED TO CALCULATE - KERNEL REGRESSION]

## 2. Coverage by Domain (Structural Presence)

| Domain | Test File Count | Status | Confidence |
| :--- | :---: | :--- | :--- |
| **Core (Kernel/RP)** | 4 | **Verified** | High |
| **Wallet** | 8 | **Verified** | High |
| **AI / ML** | 12 | **Verified** | Medium |
| **Blockchain** | 6 | **Verified** | Medium |
| **Tachyon / Storage** | 3 | **Verified** | Medium |
| **API / Routing** | 15 | **Verified** | Medium |
| **Sports Infra** | 5 | **Verified** | High |
| **Frontend (e2e)** | 2 | **Verified** | Low |

## 3. High-Risk Modules (Missing/Low Tests)

1. **Agent Swarm Logic**: No tests found for autonomous agent coordination.
2. **P2P Gossip**: Basic connectivity tests exist, but network partition and healing tests are missing.
3. **Institutional Admin**: While router files exist, dedicated integration tests for the full admin flow are sparse.
4. **DID Identity**: W3C compliance verification is missing from the suite.

## 4. Current Blockers

- **Kernel Regression**: `pytest` collection currently fails because many tests import from `main.py` or `app.core.kernel`, which crashes during initialization due to the missing `get_subsystem` method.
- **Async DB Cleanup**: Several tests show patterns of manual DB mocking that may lead to flaky results in high-concurrency environments.

## 5. Recommendations

1. **Stabilize Kernel**: Fix the `get_subsystem` method to restore test collection.
2. **Expand E2E Suite**: Add Playwright tests for the Sports Intelligence Terminal (TRACK-014).
3. **Contract Testing**: Implement contract tests between the Python backend and the Solidity smart contracts.

---
**Confidence Level**: Medium (Verified via `find` and `grep`, logic verification pending kernel fix).
