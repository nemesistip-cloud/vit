# TEST_VERIFICATION.md

## 1. Test Session Summary
- **Execution Date**: 2026-07-04
- **Total Collected**: 353
- **Passed**: 230
- **Failed**: 118
- **Skipped**: 2
- **Errors**: 5 (Collection/Setup)
- **Pass Rate**: 65.2%

## 2. Failure Categorization

### A. Missing Imports / Renamed Entities (15%)
- **Root Cause**: Tests referencing `BackgroundTaskSupervisor` in `main.py` or `MarketMapping` in `app.db.models`.
- **Evidence**: `ImportError: cannot import name 'BackgroundTaskSupervisor' from 'main'`.

### B. Router Not Mounted (40%)
- **Root Cause**: Tests targeting `/api/predict`, `/api/matches`, or `/api/auth` prefixes that return 404 because routers are unmounted.
- **Evidence**: `AssertionError: assert 404 == 200`.

### C. Database Initialization (25%)
- **Root Cause**: `conftest.py` only creates tables for `WalletBase`. Tests for Explorer, Users, or Predictions fail because their tables don't exist in the SQLite memory DB.
- **Evidence**: `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: matches`.

### D. Middleware Issues (10%)
- **Root Cause**: Request ID propagation and CORs headers missing in the test client app instance.
- **Evidence**: `AssertionError: assert None == 'health-test-123'`.

### E. Contract Drift (10%)
- **Root Cause**: Login responses now return structured objects instead of flat dictionaries.
- **Evidence**: `KeyError: 'access_token'`.

## 3. Verdict
The test suite is **UNRELIABLE**. The high failure rate is not indicative of broken features but of a decoupled test harness that has not been updated to match the v1.1 architectural standards.
