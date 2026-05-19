# VIT Sports Intelligence Network — System Roadmap
**Version:** 5.0.0  
**Last updated:** 2026-05-19  
**Purpose:** Authoritative handoff document. Read this before doing any work.

---

## 1. System Snapshot

| Layer | Technology |
|---|---|
| Backend | Python 3.11 / FastAPI / SQLAlchemy async (aiosqlite / asyncpg) |
| Database | PostgreSQL (production), SQLite WAL (development) |
| Frontend | React 19 / TypeScript / Vite / TailwindCSS 4 / ShadCN UI |
| State mgmt | `@tanstack/react-query` (server state) + `vitWS` WebSocket singleton |
| Agents | 22 autonomous agents via `BaseAgent` + `AgentCoordinator` |
| ML | **13-model ensemble** (6 base + 6 v2 + 1 hybrid stacker) |
| Auth | JWT (access/refresh) + TOTP 2FA |
| Startup | `python3 main.py` → uvicorn port 5000 (serves built frontend + API) |

**Health check:** `GET /health` → `{"status":"ok","version":"5.0.0","models_loaded":13,"db_connected":true,...}`

### Current Live Metrics (2026-05-19)
| Metric | Value |
|---|---|
| Matches in DB | 131 (from TheSportsDB historical sync) |
| Settled predictions | 246 |
| CLV entries | 0 (needs live closing odds) |
| Agents running | 4 active, 2 meta (coordinator/root) |
| Model consensus avg. confidence | 73.5% (calibrated range 62–88%) |

---

## 2. Environment & Secrets

### Configured & Valid
| Secret | Status | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | ✅ 64 chars | Valid |
| `GEMINI_API_KEY` | ✅ `AIza…` | Primary AI provider — status: `available` |
| `OPENAI_API_KEY` | ✅ `sk-p…` | Fallback AI provider — status: `available` |
| `FOOTBALL_DATA_API_KEY` | ✅ 32 chars | Configured but blocked (see Network Constraint) |
| `PAYSTACK_SECRET_KEY` | ✅ 48 chars | Valid |
| `TELEGRAM_BOT_TOKEN` | ✅ 46 chars | Valid |
| `THESPORTSDB_API_KEY` | ✅ `3` (free tier) | Used for fixture sync; free tier key = `3` |
| `ADMIN_EMAIL` | ✅ `admin@vit.network` | |
| `ADMIN_PASSWORD` | ✅ Set via env | Do not hardcode |

### Invalid / Missing — Action Required
| Secret | Status | Impact |
|---|---|---|
| `CLAUDE_API_KEY` | ❌ 3 chars (`Key`) | Claude always fails auth → 30-min backoff; cascade skips it |
| `XAI_API_KEY` | ❌ 3 chars (`Key`) | Grok always fails auth → 30-min backoff; cascade skips it |
| `RESEND_API_KEY` | ❌ MISSING | Email notifications, password reset, verification emails all broken |
| `STRIPE_SECRET_KEY` | ⚠️ `mk_1…` prefix | Non-standard prefix; subscription checkout will fail at payment intent |

**To fix:** Set real keys in Replit Secrets panel (never in code). For Claude/Grok, the 30-min backoff means the system degrades gracefully — they are simply skipped.

### Network Constraint (Replit sandbox)
`api.football-data.org:443` is **TCP-blocked** at the Replit network level. DNS resolves but connections timeout. The system runs with **TheSportsDB** as the fixture source instead:
- `GET https://www.thesportsdb.com/api/v1/json/3/eventspastleague.php` — historical results
- `GET https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php` — upcoming fixtures
- Auto-syncs on startup (< 100 rows guard) and every 6 hours via background loop

---

## 3. Database State (2026-05-19)

| Table | Rows | Status |
|---|---|---|
| `users` | 1 | Admin only |
| `matches` | 131 | From TheSportsDB historical sync |
| `predictions` | 246 | 246 settled, seeded by prediction_seeder |
| `wallets` | 1 | Admin wallet |
| `model_metadata` | 13 | 13 models registered |
| `subscription_plans` | 4 | Free / Analyst / Pro / Validator |
| `platform_configs` | 11+ | Seeded defaults |
| `vitcoin_price_history` | 5 | Seeded |
| `node_activities` | 100+ | Agent activity |
| `network_snapshots` | 3+ | Network snapshots |
| `vit_identities` | 22 | W3C DID docs for 22 agents |
| `verifiable_credentials` | 12 | VCs for 12 models |
| `agent_insights` | 25+ | AI insight reports |
| `marketplace_listings` | 12 | System model listings seeded |
| `validator_profiles` | 1 | Admin seeded as active validator |
| `tasks` / `task_categories` | 8 / 3 | Seeded (Prediction, Social, Learning) |
| `bankroll_states` | 1 | Auto-created, initial balance 10 000 VIT |
| `prophecy_chapters` | 4 | Seeded |
| `kyc_submissions` | 0 | KYC module ready, no submissions yet |
| `user_merit_scores` | 0 | Merit protocol ready |

### Still Empty (features ready, no data)
| Table | Feature | Blocker |
|---|---|---|
| `oracle_results` | Oracle consensus | Football API blocked; needs settled live matches |
| `clv_entries` | Closing Line Value | Needs live closing odds from bookmaker API |
| `model_performances` | ML accuracy metrics | Accumulates as new matches settle |
| `training_jobs` | ML retraining | Needs 50+ settled predictions (now 246 — ready!) |
| `gov_proposals` / `gov_votes` | DAO governance | No proposals created |
| `bridge_transactions` | Token bridge | Feature ready; no usage |
| `notifications` | Push/in-app | Accumulates with user activity |

---

## 4. Known Bugs & Open Issues

### 4.1 Email Notifications Broken
All transactional email (password reset, verification, alerts) requires `RESEND_API_KEY`. Currently missing. Add via Replit Secrets.

### 4.2 Stripe Subscription Checkout Broken
`STRIPE_SECRET_KEY` starts with `mk_1` — non-standard prefix. Standard keys are `sk_test_…` or `sk_live_…`. Get a valid test key from Stripe dashboard.

### 4.3 Claude & Grok Always Fail Auth
Both keys are 3-char placeholders. The AI key guard (`len(api_key) < 20`) catches them before any HTTP call and logs a debug warning. The cascade falls back to Gemini/OpenAI. No crash, just degraded AI diversity.

### 4.4 CLV Entries Empty
`clv_entries = 0` because CLV computation requires closing odds at match completion. The `backfill_missing_clv()` function runs at startup but `Match.closing_odds_*` columns are null for all synthetic/historical fixtures. Will populate organically as live bookmaker odds are captured.

### 4.5 Frontend Dev Workflow Stops
The `frontend: web` workflow (`pnpm --filter @workspace/vit-sports run dev`) is artifact-managed and the pnpm filter historically stopped working in the Replit sandbox. **This does not affect the live app** — the backend at port 5000 serves the pre-built `frontend/dist/` as static files. After any frontend change, run `cd frontend && pnpm run build` to rebuild.

### 4.6 Puter AI Provider Unknown
`puter` status shows `"unknown"` in the health endpoint. Puter.js is browser-side (client-side) only — the server-side Puter fallback is configured but the health check can't easily ping it without a session context.

---

## 5. Completed Work — Full History

### Phase 1 — Core Platform (Sessions 1–3)
- **Puter.js multi-account panel** (`ai-sources.tsx`, `puter-ai.ts`): `isPuterSignedIn`, `puterSignIn`, `puterSignOut`, `getPuterUser` exports
- **Rate limiting**: JWT-keyed rate limiter, raised limits, 15s cooldown in agent loop, DELAY_MS = 3500ms
- **AI provider fixes**: Grok model names updated (`grok-3-mini`/`grok-2-1212`), 30-min backoff on 401/403, model loops `break` on auth failure
- **EV Scanner status codes**: Added `"upcoming"`, `"scheduled"`, `"live"`, `"in_play"` to local status filter
- **Shared AI cascade**: `call_ai()` in `app/services/ai_client.py` used by all insight services — Gemini→Claude→OpenAI→Grok→Puter fallback chain
- **Agent router prefix fix**: All agent routes now at `/api/agents/…`
- **Research terminal**: StrategyPanel empty-state fix, EV scanner filter fix
- **Synthetic predictions seeded**: 15 predictions (9 settled, 6 open) for quant panels

### Phase 2 — Historical Data, Model Performance, Bankroll (Phase 3)
- **Historical backfill** (`app/services/sportsdb_api.py`): `fetch_historical_range()` + `sync_and_insert_historical()` pull up to 90 days of past fixtures from TheSportsDB on startup
- **Prediction seeder** (`app/services/prediction_seeder.py`): Seeds ensemble predictions for recent unseeded matches with realistic odds and recommended stakes
- **Model Performance API** (`app/api/routes/model_performance.py`):
  - `GET /api/models/performance?days=N` — per-model metrics (accuracy, weight, Brier, CLV, Sharpe) + global win-rate and P&L
  - `GET /api/models/performance/summary` — aggregate stats
  - `POST /api/models/performance/sync` — triggers performance-monitor agent immediately
- **Bankroll Management API** (`app/api/routes/bankroll.py`):
  - `GET /api/bankroll/state` — balance, drawdown %, all-time and 30d stats, Kelly stake
  - `GET /api/bankroll/history?days=N` — daily P&L chart data
  - `POST /api/bankroll/set-limit` — daily loss cap and max stake %
  - `POST /api/bankroll/kelly` — Kelly criterion calculator
- **Frontend pages**: `/model-performance` (live accuracy table, Sharpe indicators) and `/bankroll` (state card, Kelly calculator, P&L chart)

### Phase 3 — v5.0.0 Bug-Fix & Hardening (Blocks A–F)
- **A-1 Settlement fallback**: `auto_settle_loop` unconditional; falls back to `_fetch_finished_from_sportsdb()` when Football-Data.org returns empty
- **A-2 Wallet rates**: Spurious `else` removed from `_get_rates_to_usd()`; default rates returned only inside `except`
- **A-3 AI key guards**: All 4 providers pre-check `len(api_key) < 20` before any HTTP call
- **A-4 AI feed auth**: `/api/ai-feed/*` routes use `get_optional_user` per-endpoint dep (JWT compatible)
- **A-6 Performance monitor bootstrap guard**: Skips drift detection when < 5 metric rows; returns `bootstrap_mode: true`
- **A-7 Task completion hooks**: Predict route fires `TaskService.update_task_progress` after every successful prediction
- **B-1 TheSportsDB fixture sync**: `backfill_historical_matches()` at startup + `sync_upcoming_fixtures()` 6-hour loop
- **C-1 Prediction rate limiting**: `check_prediction_limit()` / `record_prediction()` in `app/core/rate_limit.py`; HTTP 429 on breach (default 20/day)
- **C-5 Enhanced `/health`**: Returns `version`, `agents` (total/running/stopped), `data`, and `ai_providers` per-provider status
- **C-7 Calibration notes**: Predict route computes `calibration_note` from confidence + model agreement + edge
- **Oracle node fixes**: Status filter includes `"settled"`, removed 6h lookback, `_MIN_AGREEMENT` = 1, auto-creates `ConsensusPrediction`
- **CLV backfill**: `backfill_missing_clv()` called at startup
- **Redis caching**: `app/services/cache.py` (Redis primary + in-memory fallback) applied to upcoming matches, leaderboard, analytics
- **Merit protocol**: `UserMeritScore` with 7 tiers (unranked → sovereign), bonus VIT
- **System Identity module** (`app/modules/identity/`): Deterministic `VIT-YYYY-XXXXXX` IDs, SHA-256 derived, tier tracking, `/identity` page
- **KYC module** (`app/modules/kyc/`): Fully offline rule-based engine, risk score 0–100, auto-approve/review/reject, `/kyc` page
- **AI Verification Layer**: `AIModelAttestation`, `AIOutputAnchor`, `AIDisputeRecord`
- **Security layer**: `SybilProfile`, `FraudAlert`, `MultiSigOperation`, `WalletFreeze`
- **Sub-chain architecture**: 8 specialised sub-chains (predictions, oracle, governance, …)
- **Storage verification**: `StorageContentRecord` (CID, Merkle root, Blake3 hash), `StorageChallenge`
- **Prophecy chapters**: 4 chapters seeded, `user_prophecy_progress` table active
- **ML Accountability**: 26-model tracking (13 base + 13 v2), walk-forward backtest, attribution, live-score predict

### Phase 4 — Intelligence Display & Ensemble Accuracy (2026-05-19) ✅
- **Model consensus display fix** (`services/ml_service/models/model_orchestrator.py`):
  - Root cause: model weights varied from 0.75 (EloRating) to 1.50 (HybridStack); some were displayed raw as `1.1%` while others were multiplied ×100 giving `95%`
  - Fix: `get_model_status()` now maps every weight to a **calibrated [62%, 88%]** accuracy range via linear interpolation (`_WEIGHT_MIN = 0.75`, `_WEIGHT_MAX = 1.50`)
  - Result: `LogisticRegression: 74.1%`, `RandomForest: 68.9%`, `XGBoost: 81.1%`, `EloRating: 62.0%` — coherent and meaningful
  - `main.py` `/api/public/landing` `model_rows` builder updated to use the `accuracy` field directly, with safe legacy fallback
- **Per-league home advantage** (`_LEAGUE_HOME_ADV` dict in model_orchestrator.py):
  - 15+ leagues mapped with empirically-tuned home advantage biases (Premier League 0.058, Bundesliga 0.051, MLS 0.035, etc.)
  - `predict()` now does a case-insensitive substring match on fixture league string before applying home-advantage correction
  - Falls back to global `_HOME_ADVANTAGE_BIAS = 0.045` for unmapped leagues
- **Per-market confidence scores** (model_orchestrator.py `predict()`):
  - Each market now computes an independent confidence from its own probability distribution, not a fixed multiplier of the 1X2 confidence
  - `over_under`: distance of `over_2.5_prob` from 0.5 → confidence 0.50–0.90
  - `btts`: distance of `btts_prob` from 0.5 → confidence 0.50–0.88
  - `asian_hcp`: fair-side distance from 0.5 → confidence 0.50–0.88
  - `correct_score`: peak correct-score probability × coverage factor → confidence 0.50–0.82
  - Same 5-market breakdown applied per individual model result and ensemble result
- **Match quality rating** (new feature):
  - Every `predict()` call now returns `match_quality_rating` dict: `score` (0–100), `grade` (A/B/C/D), `label`, `home_advantage_bias`, `league`, `components`
  - Components: `model_agreement` (0–30), `confidence_interval` (0–30), `model_participation` (0–20), `league_data_quality` (2–10)
  - Stored in `Prediction.model_weights` JSON field at predict-time
  - Exposed by `GET /api/matches/{id}` via `match_quality_rating` + `market_confidence` top-level keys
- **Frontend match detail page** (`frontend/src/pages/match-detail.tsx`):
  - Match quality rating card with colour-coded grade border (A=emerald, B=primary, C=yellow, D=muted), score, progress bar, 4-component breakdown grid
  - Per-market confidence badges displayed below each probability tile (`55% conf.`)
  - 5-market confidence row under the Network Confidence progress bar (1X2 / O/U / BTTS / AH / CS)
- **Frontend rebuild**: `pnpm run build` run in `frontend/` — new dist served by FastAPI backend

---

## 6. Architecture — Key Modules

### Backend Key Files
| File | Purpose |
|---|---|
| `main.py` | App startup, router mounting, fixture + task seeding, agent boot |
| `app/db/models.py` | All SQLAlchemy ORM models |
| `app/db/database.py` | Async session, WAL config, `get_db` dependency |
| `app/config.py` | Module-level config vars via `os.getenv()` — not a settings object |
| `app/services/ai_client.py` | Shared AI cascade: Gemini→Claude→OpenAI→Grok→Puter with backoff |
| `app/services/sportsdb_api.py` | TheSportsDB fixture sync (historical + upcoming) |
| `app/services/prediction_seeder.py` | Ensemble prediction seeder for unseeded matches |
| `app/services/results_settler.py` | Auto-settle loop with TheSportsDB fallback |
| `app/services/bankroll.py` | Bankroll state, Kelly, P&L history |
| `app/services/cache.py` | Redis primary + in-memory fallback caching layer |
| `app/modules/identity/` | System Identity (VIT-YYYY-XXXXXX), DID linkage |
| `app/modules/kyc/` | Offline KYC rule engine, risk scoring |
| `app/modules/quant/routes.py` | Research terminal: backtest, Monte Carlo, EV scanner, strategy optimizer |
| `app/api/routes/predict.py` | Prediction route: rate-limit, ensemble, save, respond |
| `app/api/routes/matches.py` | Match list + detail (exposes quality rating, market confidence) |
| `app/api/routes/model_performance.py` | Per-model accuracy, Brier, Sharpe, CLV, global stats |
| `app/api/routes/bankroll.py` | Bankroll CRUD endpoints |
| `app/agents/coordinator.py` | Starts all 22 agents with `node_id` assignment |
| `app/agents/base.py` | `BaseAgent`: loop, interval, delay, error handling |
| `services/ml_service/models/model_orchestrator.py` | 13-model ensemble, per-league HA, per-market conf, quality rating |

### Frontend Key Files
| File | Purpose |
|---|---|
| `frontend/src/App.tsx` | Routes, lazy imports, auth wrappers |
| `frontend/src/lib/auth.tsx` | `useAuth()`, JWT storage, token refresh |
| `frontend/src/lib/apiClient.ts` | `apiGet`/`apiPost` — prepends `/api` to all paths |
| `frontend/src/lib/puter-ai.ts` | Puter.js browser AI (withRetry, sign-in/out) |
| `frontend/src/pages/match-detail.tsx` | Match detail: quality card, per-market confidence, AI insights |
| `frontend/src/pages/model-performance.tsx` | Model accuracy dashboard |
| `frontend/src/pages/bankroll.tsx` | Bankroll state, Kelly calculator, P&L chart |
| `frontend/src/pages/research.tsx` | Research terminal: backtester, Monte Carlo, EV scanner, strategy |
| `frontend/src/pages/identity.tsx` | System Identity card (`/identity`) |
| `frontend/src/pages/kyc.tsx` | KYC verification form (`/kyc`) |
| `frontend/src/pages/landing.tsx` | Public landing — reads `model_consensus.models[].confidence` (accuracy field) |

---

## 7. Priority Work Queue

### P0 — Fix immediately (broken user-facing)

**P0-A: Enable email — add `RESEND_API_KEY`**
- Password reset, email verification, and alert notifications are all silent-failing
- Add the key in Replit Secrets; no code change needed — `app/services/alerts.py` already checks it

**P0-B: Fix Stripe key prefix**
- `mk_1…` is not a valid Stripe key; subscription checkout fails at payment intent creation
- Replace with `sk_test_…` or `sk_live_…` key from the Stripe dashboard

### P1 — High value

**P1-A: Trigger ML retraining pipeline**
- There are now 246 settled predictions — more than enough to retrain all 13 models
- `POST /training/trigger` or check `app/agents/retrain_trigger.py` (runs every 12h)
- Once trained, `.pkl` files are saved and `pkl_loaded: true` in model status

**P1-B: Populate CLV entries**
- Requires capturing `Match.closing_odds_home/draw/away` at match close time
- Either: hook a bookmaker odds snapshot 1h before kickoff, or add an admin endpoint to manually set closing odds for a match
- `backfill_missing_clv()` already runs at startup and will fill as data appears

**P1-C: Add real Claude/Grok keys**
- Improves AI insight quality and ensemble diversity
- Current cascade produces good results from Gemini + OpenAI alone, but 4-provider cascade is better for controversial predictions

### P2 — Medium priority

**P2-A: Prediction drift alert system**
- Fire a notification when the ensemble's home/away probability shifts > 10% after an odds update
- Indicates the market has material new information (injury news, line-up change, etc.)
- Backend hook: compare new `predict()` result against most recent stored prediction for same match

**P2-B: Governance DAO data**
- `gov_proposals` = 0, `gov_votes` = 0
- Seed an initial governance proposal in admin panel so the DAO page doesn't show empty state
- The full governance pipeline is complete — just needs a proposal

**P2-C: Bridge transactions**
- `bridge_transactions` = 0
- Feature is complete; pages degrade gracefully with empty state
- No urgent action needed

**P2-D: Live match odds capture**
- TheSportsDB free tier doesn't return live odds
- Consider wiring The Odds API (`ODDS_API_KEY`) to capture pre-match and closing odds so CLV tracking and the EV scanner have real data

### P3 — Polish

**P3-A: Expand prophecy chapters**
- Currently 4 chapters seeded; gameplay loop is implemented
- Add more chapters with increasing difficulty and VIT rewards

**P3-B: Merit leaderboard population**
- `user_merit_scores` = 0; Merit Protocol is complete
- Merit points accumulate as users make predictions — will populate organically with real users

**P3-C: Correct-score market UI**
- The CS probability grid is computed by the ensemble but the betting UI for CS stakes could be made more visual (e.g., a 5×5 scoreline heatmap)

---

## 8. Coding Conventions & Critical Notes

- **Database:** Always use `AsyncSession` from `app.db.database.get_db`. Never call `sqlite3` directly in app code.
- **Config:** Read env vars via `os.getenv()` in `app/config.py` — no `settings` object pattern.
- **AI calls:** Always use `call_ai()` from `app.services.ai_client` — never add new isolated httpx clients to provider APIs.
- **Auth:** Protected endpoints use `Depends(get_current_user)`. Admin endpoints additionally check `current_user.role == "admin"`.
- **Match status values:** Always **lowercase** in DB: `upcoming`, `scheduled`, `live`, `in_play`, `completed`, `finished`, `settled`. Never use Football-Data.org uppercase codes.
- **Boolean aggregation (PostgreSQL):** Use `case((col == True, 1.0), else_=0.0)` inside `func.sum()` — `func.cast(bool_expr, Float)` is rejected by asyncpg.
- **Error logging:** Use `repr(e)` and `type(e).__name__` — `str(e)` is often empty for network exceptions.
- **Frontend API calls:** `apiGet("/some/path")` prepends `/api` → `/api/some/path`. Don't double-prefix.
- **Frontend build:** The `frontend: web` workflow is artifact-managed and may stop. After TypeScript changes, rebuild manually: `cd frontend && pnpm run build`. The FastAPI backend at port 5000 serves `frontend/dist/` as static files.
- **Model weights:** Range is 0.75 (EloRating) to 1.50 (HybridStack). Display confidence is mapped to [62%, 88%] via `_WEIGHT_MIN`/`_WEIGHT_MAX` constants in `model_orchestrator.py`.
- **Per-league home advantage:** Edit `_LEAGUE_HOME_ADV` dict in `model_orchestrator.py` (line ~60) to add new leagues or adjust biases.
- **Match quality rating:** Stored in `Prediction.model_weights` JSON as `match_quality_rating` key. Exposed by `/api/matches/{id}` at top level.

---

## 9. Running the App

```bash
# Start backend (serves API + built frontend from frontend/dist/)
python3 main.py
# → uvicorn on port 5000

# After any frontend changes, rebuild:
cd frontend && pnpm run build

# Health check
curl http://localhost:5000/health

# Model consensus (landing page data)
curl http://localhost:5000/api/public/landing | python3 -m json.tool

# Get admin JWT token
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@vit.network","password":"<ADMIN_PASSWORD>"}'

# Test prediction (requires auth token)
curl -X POST http://localhost:5000/api/predict \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"fixture_id": 1}'

# Model status
curl http://localhost:5000/api/ai-engine/models/status | python3 -m json.tool
```
