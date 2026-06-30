# 13 Testing Standards

## 1. Unit & Functional Testing
- **Backend**: Use `pytest` with `pytest-asyncio`.
- **In-Memory DB**: Use `:memory:` SQLite for fast functional tests. Ensure schema initialization (`Base.metadata.create_all`) in conftest.
- **Coverage**: Aim for 80%+ coverage on core business logic.

## 2. E2E Testing
- **Frontend**: Use Playwright for critical user flows (Login, Wallet, Predictions).
- **Credentials**: Use `testuser` / `password123` for automated tests.

## 3. CI Integration
- All tests must pass in CI before merging to `main`.
- Use `INTEGRATION_CHECKLIST.md` for verifying complex Track-based integrations.
