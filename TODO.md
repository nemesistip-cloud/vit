# VIT Sports Intelligence — Project Status & TODO

## ✅ Implemented & Resolved (v5.0.0+)

### Core Platform
- **Environment Stability**: Fixed `requirements.txt` and environment conflicts for `aiohttp`, `aiosqlite`, and `alembic`.
- **API Routing**: Standardized all routes on `/api` prefix. Fixed 17+ frontend path-prefix bugs (admin, accumulator, training, api-client, error-boundary).
- **Schema Validation**: `PredictionResponse` supports complex nested model metadata in `model_weights`.
- **Security**: WebSocket JWT authentication for real-time notification streams (SEC-01).
- **Test Coverage**: 249/249 tests pass at ~30% code coverage.

### AI Engine
- **13-Model Ensemble**: Dynamic weight adjustment, per-league weights, bootstrap confidence intervals, model attribution.
- **ML Accountability**: 26 models tracked. APIs: `/api/ai-engine/predictions/{id}/breakdown`, `/api/ai-engine/backtest/walk-forward`, `/api/ai-engine/predictions/{id}/attribution`, `/api/ai-engine/predict/live-score`.
- **Model Performance API**: `/api/models/performance?days=N`, `/api/models/performance/summary`, `/api/models/performance/sync`.
- **Calibration**: `calibration_note` in every `PredictionResponse`.
- **Prediction Rate Limiting**: `MAX_PREDICTIONS_PER_DAY` (default 20); HTTP 429 on breach.

### Data & Sync
- **TheSportsDB**: Historical backfill (90 days) + 6-hour upcoming fixtures loop. Paid key via `THESPORTSDB_API_KEY` env var (defaults to free key `3`).
- **League Coverage**: 22 leagues in home-advantage model, 21 leagues in LEAGUE_PRIORS, full aliases in Football-Data.org COMPETITIONS map, iSports IDs for Ekstraklasa/Liga MX/Conference League.
- **Result Settlement**: Auto-settle loop with TheSportsDB fallback.

### Bankroll & Analytics
- **Bankroll Management**: Kelly Criterion, 30-day P&L history, drawdown tracking. APIs: `/api/bankroll/state`, `/api/bankroll/history`, `/api/bankroll/set-limit`, `/api/bankroll/kelly`.
- **Analytics**: Accuracy dashboard, CLV analysis, system metrics — all silent `except: pass` blocks replaced with `logger.debug`.

### New Routes Added
- **AI Upload**: `/api/ai-upload/sources`, `/api/ai-upload/list`, `/api/ai-upload/submit` — manual external AI prediction submission.
- **System Status**: `/api/system/status` (and `/system/status`) — DB health, agent counts, economy stats. Whitelisted in auth middleware.
- **Public Landing**: `/api/config/public/landing` — real-time stats, ticker, testimonials, plans for landing page.

### Frontend Fixes
- `/ai-upload` page — fully functional (all 3 backend routes now exist).
- `/landing` page — `LandingData` from `/api/config/public/landing` populated with real DB stats.
- `/dashboard` and `useRealtimeTicker` — corrected to call `/api/system/status`.
- `ecosystem-ticker.tsx` — already used `/api/system/status` correctly.

### Backend Modules
- **KYC Module**: Offline rule-based engine. `KYCScreenerAgent` runs on 10-minute cycle.
- **Identity Module**: Deterministic `VIT-YYYY-XXXXXX` SHA-256 IDs per user.

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
