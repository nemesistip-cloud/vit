# Test Failure Root Cause Analysis

## 1. Summary
The test suite is currently in a high-failure state due to significant architectural evolution (v1.1 standard) which has rendered many legacy tests incompatible with the current repository structure.

## 2. Categories of Failure

### A. Missing Imports / Renamed Entities
- **Failure Count**: ~20+
- **Representative Tests**: `tests/test_background_supervisor.py`, `tests/test_team_a_refactor.py`
- **Root Cause**: Tests attempt to import entities that have been moved or removed during recent refactors.
  - `BackgroundTaskSupervisor` is no longer in `main.py` or core.
  - `MarketMapping` is missing from `app.db.models`.
- **Confidence**: High

### B. Fixture & Asyncio Loop Conflicts
- **Failure Count**: ~10
- **Representative Tests**: `tests/core/wallet/*`
- **Root Cause**: Conflicts in the shared `Base` metadata when using `:memory:` databases across different async tests, causing "index already exists" errors.
- **Confidence**: High

### C. Router Not Mounted (Functional Failures)
- **Failure Count**: ~15
- **Representative Tests**: `tests/test_api_endpoints.py`
- **Root Cause**: Many business logic routers (Matches, Predict, etc.) are unmounted in `main.py`, causing 404s in functional API tests.
- **Confidence**: High

## 3. Recommended Resolution Strategy
1. **Fixture Isolation**: Update `conftest.py` to use unique file-based SQLite databases for each test session to avoid metadata pollution.
2. **Entity Reconciliation**: Update legacy tests to point to new module locations or deprecate tests for removed features.
3. **Router Mounting**: Explicitly mount critical routers in `main.py` to enable functional testing.
