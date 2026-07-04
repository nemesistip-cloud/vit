# TEST_REHABILITATION_PLAN.md

## 1. Executive Summary
The VIT test suite is currently experiencing a **33% failure rate** (118/353 tests) with 5 collection errors. These failures are primarily driven by the architectural transition to the v1.1 Kernel-based runtime and module modularization.

## 2. Categorization of Failures

### A. Architectural Drift (Missing Imports / Renamed Entities)
*   **Root Cause**: Tests attempt to import classes/models that have been moved to core subsystems or specialized modules.
*   **Examples**:
    *   `BackgroundTaskSupervisor` moved from `main.py` to `ResourcePlatformSubsystem`.
    *   `MarketMapping` moved from core models to `app.modules.sports.models`.
*   **Impact**: Blocks test collection for critical modules.
*   **Action**: Update import paths in legacy tests or deprecate tests for obsolete wrappers.

### B. Routing & Namespace Failures (404 Not Found)
*   **Root Cause**: Critical routers (Auth, Wallet, Matches) are either unmounted in `main.py` or their prefixes have shifted (e.g., `/api/auth/` vs `/auth/`).
*   **Examples**: `tests/test_auth.py`, `tests/test_new_modules.py`.
*   **Impact**: Widespread functional failures in API integration tests.
*   **Action**: Consolidate router registration within `main.py` and align test client base URLs.

### C. Persistence Layer Initialization (Database Schema Missing)
*   **Root Cause**: `tests/conftest.py` only synchronizes `WalletBase` metadata. Most tests require the global `Base` metadata (which includes Users, Matches, Predictions).
*   **Examples**: `tests/test_explorer.py`, `tests/test_wallet_manager.py`.
*   **Impact**: "Table not found" or "OperationalError" during test execution.
*   **Action**: Update `conftest.py` to import and synchronize all relevant metadata.

### D. API Contract Drift
*   **Root Cause**: Response envelopes (e.g., error formats) or login response structures have changed, but tests expect legacy formats.
*   **Examples**: `KeyError: 'access_token'` in login tests.
*   **Impact**: Brittle assertions failing on valid but updated responses.
*   **Action**: Align test assertions with the new v1.1 API standards.

### E. Infrastructure & Middleware
*   **Root Cause**: Request ID propagation or other middleware not being correctly applied to the test app instance in `conftest.py`.
*   **Examples**: `tests/test_health.py` failing on `X-Request-ID`.
*   **Impact**: Reliability checks failing.
*   **Action**: Ensure `GZipMiddleware`, `RequestIDMiddleware`, etc., are correctly instantiated in the test harness.

## 3. Rehabilitation Roadmap

### Phase 1: Foundation (Immediate)
1.  **Refactor `conftest.py`**: Ensure all DB metadata is loaded; fix `sqlite:memory` sharing.
2.  **Mount Key Routers**: Register `matches`, `predict`, and `wallet` routers in `main.py`.

### Phase 2: Entity Alignment
1.  Fix import paths for `MarketMapping` and `BackgroundTaskSupervisor`.
2.  Update Auth tests to target correct prefixes.

### Phase 3: Contract Verification
1.  Update assertions for updated API response envelopes.
2.  Fix Middleware test failures.
