# VIT Sports Intelligence Network — v4.6 Planned Release

> **Status:** PLANNED — not yet released.
> **Current production version:** 4.5.0 (`app/config.py`).
> **Source of truth for completed work:** `replit.md`, `ROADMAP.md` (Apr 23 2026), `FRONTEND_TODO.md` (Apr 24 2026).

The `# main.py — VIT Sports Intelligence Network v4.6.0` header in `main.py` line 1 has been pointing at this release for some time without a backing changelog. This document defines what v4.6 actually contains, and lists every issue that is still unresolved at the moment of writing.

---

## Upgrade History

### Apr 25 2026 — Subscription / Markets / Training Gap-Fix

Five gaps found during a deep audit, all closed in one pass.

**G1 · Admin subscription pricing was unreachable (P0)**
- Frontend `SubscriptionsTab` was calling `GET /admin/subscriptions` and `PUT /admin/subscriptions/{id}` but **neither route existed**. Admins could not view or edit pricing — the tab spun forever on a 404.
- Added 3 admin-gated endpoints in `app/api/routes/admin.py`:
  - `GET /admin/subscriptions` — list every plan.
  - `PUT /admin/subscriptions/{plan_id}` — partial update (`display_name`, `price_monthly`, `price_yearly`, `prediction_limit`, `features`, `is_active`); writes an `AuditLog` entry capturing old→new field diffs.
  - `POST /admin/subscriptions` — create a new plan with 409 conflict guard on `name`.

**G2 · Training upload was destroying the dataset (P0)**
- `POST /api/training/dataset/upload` defaulted `merge=False`, so each upload silently replaced `historical_matches.json`. The user explicitly flagged this: *"when I upload a training data it replaces the existing ones — that is how back infrastructure failed."*
- Flipped the default to `merge=True` and added dedup on `(home_team, away_team, date)`. Response now exposes `duplicates_skipped` so the operator can see what was filtered, and the success message branches between merge / replace wording.

**G3 · Best-bet logic only ranked 1X2 (P0)**
- `MarketUtils.determine_best_bet()` ranked only home/draw/away, ignoring the orchestrator's `over_25_prob` and `btts_prob` outputs — the user wrote: *"the model can also pick bet sides on TOTAL, HDC, BTTS etc."*
- Added a 2-way vig-removal helper `_remove_vig_two_way()` and extended `determine_best_bet()` with optional kwargs: `over_25_prob`, `under_25_prob`, `over_25_odds`, `under_25_odds`, `btts_prob`, `no_btts_prob`, `btts_yes_odds`, `btts_no_odds`. The function now scores **1X2 + Over/Under 2.5 + BTTS** in one pass, picks the highest-edge candidate across all of them, and returns a new `best_market` field plus the full `candidates` list for transparency.
- `app/api/routes/predict.py` now feeds the orchestrator's O/U + BTTS probabilities and pulls the matching market odds out of `match.market_odds` (`over_2_5` / `under_2_5` / `btts_yes` / `btts_no`).
- Sanity check: `home=0.50, draw=0.25, away=0.25` + `O2.5=0.65@1.85, U2.5@2.0` + `BTTS yes=0.62@1.75, no@2.05` → picks `over_2_5` with edge **0.1305**, instead of returning the `home` 1X2 leg (edge ~0.04 after vig removal).

**G4 · Admin's own subscription badge always showed "free" (P1)**
- `/auth/me` returned `User.subscription_tier` which defaults to `"viewer"`. Admins were therefore locked out of their own paid feature gates and the badge in `layout.tsx` sat on the grey "viewer" colour.
- `/auth/me` now resolves an `effective_tier` of `"elite"` whenever `admin_role` is set; the original value is still exposed as `raw_subscription_tier` so audit views can display it.

**G5 · AI Source Performance had no refresh trigger (P1)**
- The admin **AI Source Performance** card relied on something external writing to `ai_performances` first, so the panel sat permanently empty on a fresh install.
- New `useUpdateAiPerformance()` hook (POST `/ai/performance/update`) and a purple "Update Performance" button in the card header — recomputes accuracy / Brier from settled match outcomes and invalidates both the performance and report queries on success.

**Verification**
- Backend imports clean (`python -c "from app.api.routes.admin import router; ..."`).
- Multi-market scorer smoke test passes (correctly elevates Over 2.5 above 1X2 on synthetic input).
- `GET /admin/subscriptions` → 401 (mounted, auth-gated as designed).
- `PUT /admin/subscriptions/1` → 401 (mounted, auth-gated as designed).
- `npx tsc --noEmit --skipLibCheck` → 0 errors.
- `npm run build` → green; admin chunk 96.84 kB gzip:18.86 kB.
- Backend `/health` → `{status:"ok",models_loaded:12,db_connected:true}`.

**Known gaps (not in this pass)**
- Asian Handicap and Correct Score still aren't trained markets; no `ah_prob` / `correct_score_prob` columns exist on `Prediction` yet, so the multi-market scorer can't include them. Adding requires new ML output heads + a calibration cycle.
- AI sources beyond Gemini still need `ANTHROPIC_API_KEY` / `XAI_API_KEY` to actually populate the new performance refresh.

### Apr 25 2026 — Polish & Bug-Fix Pass

**Bugs fixed**
- **Tasks route crash (P0).** `frontend/src/pages/tasks.tsx` referenced `<TaskActionRow>` in three render paths but the component was never defined. Vite skipped the typecheck so the bundle built fine, but `/tasks` would throw `ReferenceError: TaskActionRow is not defined` at runtime. Implemented the component inline with the props the call sites already use (`task`, `status`, `canUpdate`, `ready`, `pending`, `actionUrl`, `onUpdate`); supports internal `<Link>` vs external `<a target="_blank">` rendering and switches between **Mark Progress / Claim Reward / Completed / Locked** based on state.
- **Developer page React duplicate-key warning.** `developer.tsx` keyed the endpoint list by `ep.path`, but the now-dynamic `/api/developer/docs` returns one row per `(method, path)` pair so any route with multiple verbs (e.g. `GET` + `DELETE`) tripped React's duplicate-key check. Switched to composite `${ep.method}-${ep.path}`.

**Polish**
- Removed dead `useEffect` and `Sparkles` imports left in `tasks.tsx`.
- AI Assistant chat textarea now declares `name`, `autoComplete="off"`, `spellCheck`, and `aria-label` — silences the Chrome DOM warning about missing autocomplete attributes and gives assistive tech a proper label.

**Verification**
- `npx tsc --noEmit --skipLibCheck` in `frontend/` → **0 errors** (was 3).
- `npm run build` → green; assistant chunk 6.30 kB gzip:2.48 kB.
- Backend cold-boot → `Application startup complete`, `/health` returns `{status:"ok",models_loaded:12,db_connected:true,clv_tracking_enabled:true}`.

### Apr 25 2026 — Conversational AI Assistant + Dynamic Developer Docs

**Backend (new)**
- `app/services/gemini_chat.py` — multi-turn Gemini-1.5-Flash wrapper with a VIT-aware system prompt, sliding 12-turn context window, structured error handling for 401/403/429/timeouts, and a graceful "no key" fallback.
- `app/api/routes/ai_assistant.py` — `POST /ai/assistant/chat` (auth-gated, accepts `{message, history?, context?}`) and `GET /ai/assistant/status` (reports whether `GEMINI_API_KEY` is configured). Wired into `main.py` alongside the other API routes.

**Backend (improved)**
- `app/modules/developer/routes.py` — `GET /api/developer/docs` now introspects `app.routes` and returns every `(method, path, summary, tags)` exposed by the live server, plus an `endpoint_count` field. The previous hand-curated 7-item list has been retired so the SDK reference can no longer drift.

**Frontend (new)**
- `frontend/src/pages/assistant.tsx` — chat surface with suggested prompts, animated typing indicator, history-aware turns, "New chat" reset, "Ready / Not configured" status pill, and a friendly fallback card when the API key is missing.
- `frontend/src/api-client/index.ts` — `useAssistantChat` mutation + `useAssistantStatus` query hooks (with `AssistantTurn` type) and two new `API` constants (`aiAssistantChat`, `aiAssistantStatus`).
- `frontend/src/App.tsx` — lazy-loaded `/assistant` route under the standard `<ProtectedRoute>` + `<Layout>` shell.
- `frontend/src/components/layout.tsx` — **AI Assistant** entry added to the **Pro** sidebar group with the `Sparkles` icon.

**Verification**
- Frontend `npm run build` → clean; assistant chunk 6.30 kB gzip:2.48 kB.
- Backend startup → router mounted, `/ai/assistant/status` returns `401` without a token (correct), returns `{available, provider, message}` with one.
- `/api/developer/docs` (auth-gated) returns `endpoint_count` matching the live FastAPI route table.

---

## 1. Models (`app/modules/ai/`, `services/ml_service/`)

### Planned upgrades
- **Persistent training-job tracking.** Move job status out of the in-memory dict so Elite users can trigger re-training without losing visibility on restart. Adds a `TrainingJob` table (id, key, status, started_at, finished_at, metrics_json, error) and changes `app/api/routes/training.py` to read/write through it.
- **In-app trainer for the full 12-model batch.** `scripts/train_models.py` already trains the sklearn batch end-to-end; v4.6 wires it behind `POST /api/ai-engine/train/all` so admins don't have to drop into a shell.
- **Auto-promotion guardrails.** `POST /api/ai-engine/upload/{key}` already stages weights as `{key}__{version}.pkl` and refuses to overwrite. v4.6 adds a "promotion policy" check — the candidate version must beat the active version on log-loss/Brier on the holdout set before `auto_promote=true` is honored.
- **Calibration UI.** Surface `POST /admin/calibration/fit` and `POST /admin/calibration/reload` in the admin panel with last-fit timestamp and per-model log-loss before/after (FRONTEND_TODO W-01 / B1).
- **Per-model performance surface.** Wire `GET /ai/performance` and `GET /ai/report` into `analytics.tsx` (FRONTEND_TODO W-05 / B5).

### Unresolved issues
- `USE_REAL_ML_MODELS=true` still requires a real-data Colab run + `.pkl` upload. No production-grade weights are committed.
- Training status is wiped on restart (still in-memory) until the persistence work above lands.
- `colab/train_real_match_models.py` referenced in `ROADMAP.md` does not exist. v4.6 should either create it or update the docs to point at `scripts/train_models.py`.
- LSTM and Transformer trainers are GPU-recommended and have no Replit-friendly fallback.

---

## 2. Predictions (`app/api/routes/predict.py`, `accumulator`, `odds_compare`)

### Planned upgrades
- **Implement the "Coming soon" markets** in `frontend/src/pages/predictions.tsx:520-524` (BTTS variants, Asian Handicap, etc.) end-to-end: backend scoring + UI cards + tests (FRONTEND_TODO P-01 / C1). Or move the supported list to `/predictions/markets/supported` so the frontend cannot drift.
- **Working Arbitrage tab** in `odds.tsx`: render `GET /odds/arbitrage` with edge %, stake-split per outcome, guaranteed profit, and a "copy bets" button (FRONTEND_TODO P-02 / C2).
- **Injuries panel** in `match-detail.tsx` consuming `GET /odds/injuries?match_id=...` (FRONTEND_TODO W-06 / B6).
- **Live odds-movement sparkline** on `match-detail.tsx`, fed by the existing `live_odds` channel of the notifications WebSocket.
- **Manual settlement card** in `admin.tsx` for `POST /admin/settle-results` and `POST /admin/backfill-ft-results`, with a dry-run toggle (FRONTEND_TODO W-02 / B2).
- **Global accumulator broadcast** card in `admin.tsx` for `POST /admin/accumulator/place-bet` and `POST /admin/accumulator/send` (FRONTEND_TODO W-03 / B3).
- **Audit log** tab in `admin.tsx` for the entire `app/api/routes/audit.py` router (FRONTEND_TODO W-08 / B7).

### Unresolved issues
- Some accumulator markets still show "Coming soon" in production (P-01).
- Arbitrage tab lists books but does not display arb edges (P-02).
- The frontend `Map` constructor at `frontend/src/pages/matches.tsx:68-74` fails `tsc --noEmit` (T-01) — must land first because it blocks any clean type check.
- Odds-compare error transparency landed in 4.5 but Pinnacle / Smarkets / Betfair Exchange providers are still pending.

---

## 3. VIT economy (`app/modules/wallet/`, `blockchain/`, `bridge/`, `referral/`)

### Planned upgrades
- **Bug fix — restored `vitcoin_pricing_loop()`.** During this import the function definition had been deleted, leaving its body orphaned inside `task_reset_loop()` and a `NameError: name 'vitcoin_pricing_loop' is not defined` crashing app startup. v4.6 ships the real function (revenue-backed price = `revenue_30d * 12 / supply`, floored by `vitcoin_price_floor` PlatformConfig, written to `VITCoinPriceHistory` every 6 h). Fix is in `main.py` lines 475–512.
- **Referral commission distribution on subscription upgrade.** Tie referral-use events to Stripe webhooks and credit the referrer's wallet on the first paid month.
- **KYC provider integration** (Smile Identity for Africa, Onfido globally): document upload, webhook, admin approve/reject UI in `/admin`. Required to lift withdrawal limits and unlock validator eligibility.
- **Wallet exports.** CSV/JSON transaction export buttons on `wallet.tsx` against `app/api/routes/exports.py` (FRONTEND_TODO W-09 / B8).
- **Wallet PnL + date-range filter** on `wallet.tsx` against `/wallet/transactions?from=&to=` (FRONTEND_TODO P-06).
- **Phase-4 chain prep (kept behind `BLOCKCHAIN_ENABLED=false`).** Pick Polygon/BSC/Solana, draft the VITCoin ERC-20/SPL contract, wire `ORACLE_API_KEY`. v4.6 only adds the contract draft + a feature-flagged client; activation ships in v4.7+.

### Unresolved issues
- `BLOCKCHAIN_ENABLED=false` — full validator network, on-chain staking, consensus engine, and settlement are coded but disabled. No real chain connection exists.
- Cross-chain bridge is internal VITCoin simulation only — no LayerZero / Wormhole hookup yet.
- Governance DAO has no token-gated quorum, no on-chain execution, no time-lock.
- `STRIPE_SECRET_KEY` and `PAYSTACK_SECRET_KEY` are listed as configured in the startup banner but the production keys must be in Replit Secrets before going live; deployment will fail loudly otherwise.
- Pi Network deposits referenced in the wallet schema have no SDK integration.
- Per-user Telegram linking (chat ID in user settings) has no frontend flow.

---

## 4. Task system (`app/modules/tasks/`, supervisor, background loops)

### Planned upgrades
- **Provision Redis (`REDIS_URL`).** Today rate limiting falls back to in-memory and Celery has no broker. With Redis live, v4.6 enables:
  - Persistent rate limiting across restarts.
  - Celery queues for model retraining, scheduled odds refresh, CLV recalculation.
  - Result caching for hot endpoints (predictions, odds compare, leaderboard).
- **WebSocket frontend connection.** Server-side `notifications/websocket.py` is complete; v4.6 wires the notification bell to `wss://{domain}/notifications/ws/{user_id}` with a JWT handshake and splits the channel router into named `notifications` and `live_odds` channels with their own back-off (FRONTEND_TODO C-03).
- **System Health card** in `admin.tsx`: red/green per subsystem (Redis, SMTP, Anthropic, supervisor task list) driven by `/admin/config-status` (FRONTEND_TODO P-03 / C-05).
- **Configuration Health strip** at the top of `admin.tsx` (amber for missing optional, red for missing required).
- **Frontend client-error capture.** `error-boundary.tsx` should fire-and-forget `POST /admin/client-error` so frontend crashes show up server-side (FRONTEND_TODO C-04). Adds the matching backend route.

### Unresolved issues
- Redis is **not** provisioned. Until it is, every "persistent" feature in this group is degraded to in-memory.
- SMTP is **not** configured. `_send_email()` in `app/auth/verification.py` still logs to console only — email verification and password reset are silent in production.
- `ANTHROPIC_API_KEY` and `XAI_API_KEY` are missing — multi-AI insight panel falls back to Gemini only.
- Startup prints `Sports Skills not installed. Run: pip install sports-skills` — package does not exist on PyPI; either remove the warning or replace with a real dependency.
- `.vit_jwt_secret` is still listed in `.gitignore` even though file-based JWT fallback was removed in v4.10.0 per `app/config.py:23` — the gitignore line is harmless but stale.

---

## 5. Cross-cutting unresolved issues (not specific to one area)

- **Version drift.** `main.py` header was already labelled v4.6.0 but the rest of the project was 4.5.0; this changelog reconciles that. When v4.6 ships, bump `APP_VERSION` in `app/config.py` from `"4.5.0"` to `"4.6.0"`.
- **No frontend tests.** Vitest + React Testing Library is not set up; regressions ship unnoticed (FRONTEND_TODO C-07).
- **No virtualization** on long lists (matches, predictions, marketplace, leaderboard) — they will degrade past a few thousand rows (FRONTEND_TODO U-01).
- **Mobile nav drawer** in `frontend/src/components/layout.tsx` is missing routes added in v4.x (governance, bridge, trust) (FRONTEND_TODO U-03).
- **Light-theme contrast** fails WCAG AA on several muted-foreground texts (FRONTEND_TODO U-05).
- **PostgreSQL migration.** App still runs on SQLite (`vit.db`). Production scale needs `VIT_DATABASE_URL=postgresql+asyncpg://...` and `alembic upgrade head`.
- **Tier ordering hard-coded.** `frontend/src/lib/auth.tsx:84` `TIER_ORDER` will silently break if a new subscription tier is added on the backend (FRONTEND_TODO C-02).

---

## 6. Acceptance criteria for cutting v4.6

- [ ] `npx tsc --noEmit` in `frontend/` returns 0 errors.
- [ ] `app/config.py` `APP_VERSION` bumped to `"4.6.0"`.
- [ ] Startup banner reads `VIT Sports Intelligence Network v4.6.0`.
- [ ] No background-task `NameError` regressions (`vitcoin_pricing_loop`, etc.) — `python main.py` reaches "Application startup complete" cleanly.
- [ ] All "Coming soon" copy removed from `predictions.tsx` (or backed by `/predictions/markets/supported`).
- [ ] Arbitrage tab in `odds.tsx` renders real edge / stake-split / guaranteed profit.
- [ ] `replit.md` "Recent Changes" section gains a v4.6 block summarizing what landed.
