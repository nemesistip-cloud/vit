# Verified Implementation Plan — VIT Stabilization

## 1. Task Prioritization

### P0: Kernel Stabilization
- **Task**: Restore `get_subsystem()` to `VITRuntimeKernel`.
- **Impact**: Enables all modules to retrieve their dependencies (e.g., WalletSDK) via the central kernel.
- **Risk**: Low.
- **Rollback**: Standard git revert.

### P0: Critical Router Restoration
- **Task**: Explicitly mount critical business routers (`matches`, `predict`, `dashboard`) in `main.py`.
- **Impact**: Restores basic user functionality and allows functional tests to pass.
- **Risk**: Medium (potential routing conflicts).
- **Rollback**: Comment out routes in `main.py`.

### P1: Test Suite Rehabilitation
- **Task**: Implement isolated file-based SQLite fixtures in `tests/conftest.py` and fix stale imports in legacy tests.
- **Impact**: Re-enables CI/CD confidence by providing a passing test suite.
- **Risk**: Medium (high effort).
- **Rollback**: Revert `conftest.py`.

### P1: Documentation & State Sync
- **Task**: Update `contracts.json`, `topology.json`, and `MODULE_REGISTRY.md` with new platform services (Persistence, Resource, Blockchain, Wallet).
- **Impact**: Aligns automated architecture tools with implementation reality.
- **Risk**: Low.

## 2. Dependencies
1. `get_subsystem()` must be implemented before advanced inter-subsystem integrations.
2. Router restoration is required for end-to-end testing.

## 3. Rollback Strategy
All changes will be atomic commits. Deployment rollback is managed by Render's version control.
