# VIT Sports Intelligence Network

## Overview
Institutional-grade football prediction platform combining a 12-model AI ensemble, a VITCoin wallet economy, blockchain-verified staking, a model marketplace, governance DAO, and multi-tier subscriptions (Free / Pro $49/mo / Elite $199/mo).

**Version: 4.6.0** — 12-model spec bumped to v2 with `parent_version` lineage; backward-compatible pkl + calibrator fallback to v1; **CLV signal now blended into model-weight adjuster** (40% CLV / 60% log-loss); admin `Textarea` import restored; `vitcoin_pricing_loop()` restored; planned-feature roadmap captured in `CHANGELOG_v4.6.md`.

## Architecture
- **Backend:** Python 3.11, FastAPI, SQLAlchemy (async), Alembic, Uvicorn on port 5000
- **Database:** SQLite (development) / PostgreSQL (production via `VIT_DATABASE_URL`)
- **Frontend:** React 18 + TypeScript, Vite, TailwindCSS, ShadCN UI — built to `frontend/dist/` and served by FastAPI
- **Entry point:** `main.py` → `python main.py`
- **Workflow:** "Start application" runs `python main.py` on port 5000

## Module Map
| Module | Path | Status |
|--------|------|--------|
| AI Orchestrator (12 models) | `app/modules/ai/` | ✅ Running with real trained `.pkl` weights + per-model calibrators |
| Auth (JWT + TOTP) | `app/auth/` | ✅ Complete — 2FA login gate enforced |
| Wallet + VITCoin | `app/modules/wallet/` | ✅ Core complete |
| Predictions | `app/api/routes/predict.py` | ✅ Working |
| Blockchain / Staking | `app/modules/blockchain/` | 🚧 Disabled (flag) |
| Cross-Chain Bridge | `app/modules/bridge/` | 🚧 Simulation only |
| Governance DAO | `app/modules/governance/` | 🚧 Partial |
| Marketplace | `app/modules/marketplace/` | ✅ UI live |
| Developer API | `app/modules/developer/` | ✅ Key management done |
| Notifications + WS | `app/modules/notifications/` | ✅ WS toasts + exponential reconnect |
| Referral | `app/modules/referral/` | 🚧 No reward distribution |
| Trust Engine | `app/modules/trust/` | 🚧 Partial |
| Training Pipeline | `app/api/routes/training.py` | 🚧 Colab-only |

## Key Environment Variables
- `VIT_DATABASE_URL` — SQLite default: `sqlite+aiosqlite:///./vit.db`
- `SECRET_KEY` / `JWT_SECRET_KEY` — Set in Replit secrets
- `ADMIN_EMAIL` / `ADMIN_PASSWORD` — Admin seed account
- `FOOTBALL_DATA_API_KEY` — Configured
- `GEMINI_API_KEY` — Configured
- `STRIPE_SECRET_KEY` — Configured (webhook activates subscriptions)
- `PAYSTACK_SECRET_KEY` — Configured (NGN deposits enabled)
- `SMTP_HOST` — **Missing** (email is console-stub)
- `REDIS_URL` — **Missing** (in-memory rate limiting only)
- `ANTHROPIC_API_KEY` — **Missing** (Claude insights disabled)
- `BLOCKCHAIN_ENABLED` — false (blockchain disabled)
- `USE_REAL_ML_MODELS` — **true** (loads trained `.pkl` weights from `models/`, applies isotonic calibration from `models/calibrators/`)

## Admin Access
- URL: `/admin`
- Email: `admin@vit.network`
- Password: set via `ADMIN_PASSWORD` env var

## Frontend Build
```bash
cd frontend && npm install && npm run build
```
Built output served at `frontend/dist/` by the FastAPI SPA catch-all route.

## Database Migrations
```bash
alembic upgrade head
```
Run after switching to PostgreSQL.

## Roadmap
See `ROADMAP.md` for the full implementation and integration roadmap.

## Recent Changes — CLV-Blended Weight Adjuster (Apr 25 2026)

The model weight loop now uses **Closing Line Value (CLV)** — the leading indicator of true betting edge — as a primary signal alongside log-loss.

`app/modules/ai/weight_adjuster.py`:
- Each settled match looks up its `CLVEntry` (populated inline by `results_settler.py` when closing odds arrive).
- Per model: `clv_delta = clip(clv_value × (model_prob_for_bet_side − market_prob_for_bet_side) × CLV_GAIN, ±CLV_MAX_DELTA)`
- Final delta blends 60% log-loss + 40% CLV (`CLV_WEIGHT=0.40`); when no `CLVEntry` exists the loop falls back to pure log-loss (backward compatible).
- New `model_metadata.clv_score` column stores a rolling EMA of each model's CLV contribution; `clv_samples` counts how many settled matches had a CLV signal.
- Performance leaderboard (`GET /api/ai-engine/performance`) now surfaces `clv_score`, `clv_samples`, `log_loss` per model.
- **Bug fix exposed in testing:** the v2 bump created two `model_metadata` rows with the same `name` ("XGBoost", etc. — one v1, one v2). The adjuster's per-model lookup now filters on `is_active=True` and orders by id desc, eliminating the `MultipleResultsFound` crash that would have surfaced the first time a settled match flowed through.

Migration adds `clv_score` (REAL/DOUBLE PRECISION) and `clv_samples` (INTEGER DEFAULT 0) to `model_metadata` on both SQLite and PostgreSQL paths in `main.py`.

Verified end-to-end with a synthetic match: a model that put 62% on the side that beat the line (vs market 54%) received a positive blend; a model that put 30% on that side received a CLV penalty ~17× larger than its log-loss penalty alone.

## Recent Changes — v4.6.0 Model Spec Bump to v2 (Apr 25 2026)

`services/ml_service/models/model_orchestrator.py` `_MODEL_SPECS` is now a list of dicts (was a list of 5-tuples). Every entry carries:
- `key` — bumped from `*_v1` to `*_v2` (12 keys total)
- `parent_version` — pointer back to the v1 key
- `change_summary` — one-line description of the algorithmic upgrade landing in v2
- the original `name`, `markets`, `sigma`, `market_trust` fields

**Backward compatibility (no v1 regressions):**
- `_try_load_pkl(key)` falls through to `parent_version` if the v2 `.pkl` is missing — existing v1 trained weights keep loading.
- The calibration call site in `predict()` retries with `parent_version` when no v2 calibrators are fitted — all 78 v1 calibrators in `models/calibrators/` continue to apply.
- `_MODEL_CLASS_MAP` registers both v1 and v2 keys against the same Python classes, so any cached prediction record referencing `*_v1` still resolves.

**Registry (`app/modules/ai/registry.py`):**
- Inserts a `model_metadata` row for each v2 key with `version="v4.6.0"`.
- When a v2 row is inserted, the matching v1 row (if present) is `is_active=False` but **never deleted** — preserves history for already-settled predictions.
- Bootstrap log line confirms: `[registry] Bootstrap complete — 12 new v2 models registered`.

**Per-model v2 changes (definition of done; algorithmic deltas land in subsequent commits):** logistic = league-strength interaction term, RF = `class_weight='balanced'`, XGB = early-stopping on log-loss, Poisson = per-league λ priors, Elo = recency-decayed K, Dixon-Coles = ρ grid-search, LSTM = seq-len 10 + dropout 0.2, Transformer = 4-head attention over 64-d, Ensemble = entropy-weighted stacking, Market = Shin devigging, Bayes = Dirichlet-per-league priors, Hybrid = isotonic post-calibration.

**Branch reconciliation:** `branches.md` documents all three remote branches; `MERGE_CONFLICTS.md` explains why `feat/v4.6-implementation` was *not* merged into local `main` (the merge would delete the v4.6 changelog, requirements.txt, and the admin/startup bug fixes — only a cherry-pick of the task-system delta is recommended).

## Recent Changes — Staking Hardening (Apr 22 2026)
All VITCoin balance changes in the staking subsystem now flow through `WalletService.credit/debit`, which:
- Locks the wallet row with `SELECT … FOR UPDATE` (no more double-spend race)
- Records a `WalletTransaction` for every move (full audit trail using existing `STAKE`/`REWARD`/`SLASH` types)
- Honors `is_frozen` and validates balance atomically

Settlement (`settlement.py`) now:
- Refunds (status `REFUNDED`) stakes whose market the oracle could not resolve, instead of marking them LOST
- Accumulates `ValidatorProfile.reward_earned` (was overwriting per-match)
- Batch-loads all involved wallets (no N+1)
- Sends per-stake `MATCH_RESULT` notifications (won / lost / refunded) with PnL

Stake placement (`/predictions/{match_id}/stake`) now:
- Enforces `MIN_STAKE=1`, `MAX_STAKE=100000` VIT
- Blocks staking once `Match.kickoff_time` has passed
- Locks the wallet row before the debit

Validator endpoints (`apply`, `withdraw`, admin `reject`, admin `slash`) all use the same locked, audited path.

## Recent Changes — Per-Route Code Splitting (Apr 22 2026)
`frontend/src/App.tsx` now imports every authenticated/secondary page through `React.lazy` with a single `<Suspense>` boundary around `<Switch>`. Eager pages: landing, auth, info (legal), not-found.

Bundle results (gzip in parens):
- **Main bundle: 814 KB → 412 KB (122 KB gz)** — 49% reduction
- `vendor-charts` (394 KB / 108 KB gz) is no longer in the critical path; only loaded by chart-using pages (dashboard, analytics, admin, training)
- Each route is its own chunk — heaviest are admin (63 KB / 13 KB gz), training (30 KB / 8 KB gz), predictions (28 KB / 9 KB gz)
- 24 route chunks total, fetched on demand

## Recent Changes — Accumulator Auto-Relax (Apr 22 2026)
The accumulator engine now refuses to leave the user with a 1-candidate scan (which can't form an accumulator).

`GET /admin/accumulator/candidates` (`app/api/routes/admin.py`):
- Scores every fixture once, then filters; new params `auto_relax=True` and `target_min=4`
- If fewer than `target_min` candidates pass the user's filters, edge is dropped first in 0.005 steps to 0, then confidence in 0.05 steps to 0.50, until enough candidates emerge
- Response now includes `applied_filters`, `relaxed`, `relax_steps`, `scored`

`frontend/src/pages/accumulator.tsx`:
- Default Min Legs raised from 1 → 2 (an accumulator is by definition multi-leg)
- Yellow "auto-loosened" banner shows the actually-applied filters when they differ from requested
- Orange single-candidate banner with one-tap "Loosen & rescan" button (drops edge to 0, drops confidence by 0.10, scans 10 more fixtures)
- Pluralization fix ("1 candidate" / "N candidates")

## Recent Changes — Real 12-Model Ensemble + Calibration (Apr 23 2026)

### Trained `.pkl` weights now live
The orchestrator now loads 12 real trained models from `models/*.pkl` instead of running the algorithmic fallback. All 12 are orchestrator-native classes from `services.ml_service.models.model_orchestrator`:

| Key | Class | Algorithm |
|-----|-------|-----------|
| `logistic_v1` | `_LogisticModel` | Calibrated sigmoid blend |
| `rf_v1` | `_RandomForestModel` | Random forest residual correction |
| `xgb_v1` | `_XGBoostModel` | Gradient-boosted shrinkage |
| `poisson_v1` | `_PoissonModel` | Pure Poisson goals model |
| `dixon_coles_v1` | `_DixonColesModel` | Poisson + low-score correlation |
| `elo_v1` | `_EloModel` | Elo + draw band |
| `bayes_v1` | `_BayesianModel` | Conjugate Bayesian update on form + market prior |
| `market_v1` | `_MarketModel` | Pure market baseline |
| `lstm_v1` | `_LSTMModel` | Sequence-style softmax over engineered features |
| `transformer_v1` | `_TransformerModel` | Multi-head attention stand-in |
| `ensemble_v1` | `_NeuralEnsembleModel` | Stacker over base models |
| `hybrid_v1` | `_HybridStackModel` | Stacker + market component |

Each model exposes `predict_1x2(base_hp, base_dp, base_ap, lam_h, lam_a, home_team, away_team, market_odds, seed) -> (h, d, a)` and is invoked per-match by `ModelOrchestrator.predict()` in `services/ml_service/models/model_orchestrator.py`.

### Per-model probability calibration
- 78 calibrators in `models/calibrators/` — one per `(model × class × method)`, with `class ∈ {home, draw, away}` and `method ∈ {platt, isotonic}`. Default method is **isotonic** (configurable via `CALIBRATION_METHOD`).
- Fitted from a 799-match holdout taken from `data/historical_matches.csv` (2,660 EPL matches, 7 seasons 2018/19→2024/25).
- Loader: `app.services.calibration.CalibratorRegistry` (process singleton, picks up new pickles via `reload()`).
- Apply site: `model_orchestrator.predict()` line ~1377, called with the model **key** (`logistic_v1`) — not the display name. Fixed Apr 23 2026 — previously the call passed `meta["model_name"]` (e.g. `"LogisticRegression"`), which silently fell through to identity calibration.

### Training scripts
- `scripts/train_models.py` — fits the 5 sklearn-style models on a 10-feature schema (legacy, no longer in `_MODEL_SPECS`).
- `scripts/train_remaining_models.py` — fits 9 algorithmic + sequence stand-in models on the 9-feature schema used by the orchestrator's runtime `feature_map`.
- `scripts/fit_calibrators_from_csv.py` — replays the historical CSV through every loaded `.pkl` model and fits per-class Platt + Isotonic calibrators directly. Bypasses the DB-history fitter (`scripts/fit_calibrators.py`), which requires settled `Prediction` rows joined to `Match.actual_outcome`.

### Smoke-test result (Apr 23 2026)
End-to-end run on fixture `Real Betis vs Athletic Bilbao` (B365 odds H2.40/D3.20/A2.90):
- 12/12 models active, calibration applied to **all 12** (`cal=True`)
- Final ensemble: H=0.445  D=0.262  A=0.293  conf=0.511  agreement=83.3%
- Confirms the staking auto-bootstrap path and the calibrator key-mapping fix
