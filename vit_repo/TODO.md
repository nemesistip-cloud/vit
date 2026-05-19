# VIT Sports Intelligence — Project Status & TODO

## ✅ Recently Resolved & Debugged
- **Environment Stability**: Fixed `requirements.txt` and environment conflicts for `aiohttp`, `aiosqlite`, and `alembic`. Ensured `pytest-cov` and `email-validator` are correctly installed.
- **Automated Test Infrastructure**: Implemented a robust database initialization and seeding engine in `tests/conftest.py`. The test suite now automatically builds a fresh schema and populates it with default Config, Subscription Plans, Task Categories, and an Admin account.
- **API Routing Fixes**: Corrected 404 errors across the test suite by standardizing on the `/api` prefix for all major module routers.
- **Schema Validation**: Resolved 422 Unprocessable Entity errors in the Prediction engine by updating the `PredictionResponse` schema to support complex nested model metadata in the `model_weights` field.
- **Security Compliance**: Fixed WebSocket handshake failures in smoke tests by implementing JWT authentication for real-time notification streams (SEC-01 compliance).
- **Test Coverage**: Successfully reached **100% pass rate** (249/249 tests) with ~30% code coverage across the 13+ statistical and neural modules.

## 🚀 Pending Phase 3 Implementation (To-Do)

### Phase 3a: Data & Integration
- [ ] **Real Data Sync (TheSportsDB)**: Finish extending `app/services/sportsdb_api.py` to fully replace synthetic data with 500+ historical matches for ML training.
- [ ] **Result Settlement**: Finalize the `sync_fixture_results()` loop to automatically update match outcomes every 4 hours.

### Phase 3b: ML Pipeline & Monitoring
- [ ] **Retraining Bootstrap**: Enable the `retrain_trigger.py` agent to create `TrainingJob` records when settled prediction volume exceeds 50.
- [ ] **Performance Dashboard**: Build the React visualization for model accuracy trends, Sharpe ratios, and ROI heatmaps (`frontend/src/pages/model-performance.tsx`).

### Phase 3c: User Experience & Bankroll
- [ ] **Bankroll Management**: Implement the Kelly Criterion calculation service and 30-day profit/loss history charts.
- [ ] **Email Notifications**: Integrate the Resend API for automated win/loss alerts (requires `RESEND_API_KEY`).

### Phase 3d: DAO & Blockchain Polish
- [ ] **Governance MVP**: Activate the voting logic (1 VIT = 1 Vote) for platform fee changes and league additions.
- [ ] **Cross-Chain Bridge**: Seed liquidity pools for VIT/USDT and demonstrate testnet bridge transactions.

## 🛠️ Maintenance & Refinement
- [ ] **Calibration Tuning**: Address "partial_calibration" warnings identified during neural ensemble runs.
- [ ] **Alembic Migration Path**: Move the manual DDL logic from `main.py` into structured Alembic versions for safer production deployments.
