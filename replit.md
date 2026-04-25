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

## Recent Changes — Asian Handicap + Correct Score + CLV Backfill (Apr 25 2026)
Two-feature drop. Adds AH and CS market support to the orchestrator + persistence layer
and an automatic backfill job that fills CLV rows the live settler missed.

**1) Asian Handicap & Correct Score markets**
- **Schema**: alembic `008_add_ah_cs_markets.py` adds `ah_line`, `ah_home_prob`,
  `ah_away_prob`, `ah_lines` (JSON ladder), `cs_probs` (JSON {"H-A": p}),
  `top_correct_score`, `top_cs_prob` to `predictions`. Idempotent (column-existence
  guards) so it is safe to re-run.
- **Orchestrator** (`services/ml_service/models/model_orchestrator.py`): new helpers
  `_build_score_matrix(λh, λa)`, `_ah_prob_from_matrix(line, side)`,
  `_build_ah_ladder()`, `_pick_fair_ah_line()`, `_correct_score_probs(top_n=15)`.
  `predict()` now emits `ah_line / ah_home_prob / ah_away_prob / ah_lines` and
  `cs_probs / top_correct_score / top_cs_prob` from the same Poisson λ_h, λ_a it
  already solves for 1X2 / OU2.5 / BTTS. Matrix is 7×7 (≥99.9% mass).
- **Persistence + response**: `app/api/routes/predict.py` writes the seven new
  fields onto every Prediction and `build_prediction_response` surfaces them;
  `PredictionResponse` schema in `app/schemas/schemas.py` extended.
- **Bet selection**: `MarketUtils.determine_best_bet` now scores AH (when bookmaker
  `ah_home`/`ah_away` odds are present in `match.market_odds`) and CS (when a
  `cs_odds: {"H-A": price}` dict is provided), with proper two-way devig for AH and
  proportional inverse-odds devig across the priced CS subset.

**2) Automatic CLV backfill**
- **Service**: new `app/services/clv_backfill.py` exposes `backfill_missing_clv(db,
  limit, dry_run)`. Scans settled predictions (`Match.actual_outcome IS NOT NULL`,
  `bet_side`+`entry_odds` set) whose paired `CLVEntry` is absent or has `clv IS NULL`,
  reads `closing_odds_{home,draw,away}` off the Match, computes `profit = stake*(odds-1)`
  on win else `-stake`, and upserts the CLV row. Returns counters
  `{scanned, created, updated, skipped, missing_closing_odds}`.
- **Background loop**: `model_accountability_loop` in `main.py` now calls
  `backfill_missing_clv(db, limit=500)` once per cycle and logs the counters.
  Runs alongside the existing weight-update + CLV-streak monitor passes.
- **Admin endpoint**: new `app/api/routes/admin_clv.py` exposes
  `POST /admin/clv/backfill?limit=&dry_run=` (admin role only). Returns the same
  counters dict; useful when closing odds arrive after the live settler has fired.
- Verified: route registered at `/admin/clv/backfill` (returns 401 without auth);
  helpers smoke-tested against λh=1.6, λa=1.1 ⇒ fair AH line –0.5 with 49/51 split,
  top score 1-1 at 11.8%.

## Recent Changes — AI Sources Upload Panel (Apr 25 2026)
Built a dedicated AI data ingestion surface so admins **and** analyst+ tier users can feed
raw Claude / Grok / ChatGPT analysis into the prediction ensemble match-by-match.
- **Schema**: alembic `007_add_ai_source_raw_content.py` adds `raw_content TEXT` and
  `submitted_by INTEGER` columns to `ai_predictions`.
- **Backend**: new `app/api/routes/admin_ai_sources.py` router (`/admin/ai-sources/*`):
  `permissions`, `matches`, `match/{id}`, `POST /ingest`, `DELETE /{id}`.
  Gated via `get_current_user` + `_can_upload` (admin role OR
  `subscription_tier ∈ {analyst, pro, elite}`). Validates probability range, normalises
  ±10%, allows up to 20 000 chars of pasted analysis.
- **Service**: `AIIngestionService.ingest_prediction()` extended with `raw_content` and
  `submitted_by` parameters; upserts on `(match_id, source)`.
- **Frontend**:
  - New `AISourcesTab` in `frontend/src/pages/admin.tsx` (also exported) with match
    selector, source dropdown (claude/grok/chatgpt/gemini/…), home/draw/away/confidence
    inputs, one-line reason, full-text textarea, and a list of existing sources per
    match with delete buttons.
  - New standalone page `frontend/src/pages/ai-sources.tsx` so analyst+ users (without
    admin access) can reach it via `/ai-sources`.
  - Sidebar (`layout.tsx`) shows the **AI Sources** link in the **Pro** group whenever
    `isAdmin || hasTier("analyst")`.
  - Route `/ai-sources` registered in `App.tsx`.

## Recent Changes — Dashboard / Plan / Predictions Audit Fixes (Apr 25 2026)

Audit of the live mobile screenshots surfaced four cross-cutting bugs that made the dashboard read inconsistently with the underlying data. All fixed front-to-back.

- **F1 (P0): Admin's "ACTIVE PLAN" card showed `Free`.** `/api/subscription/my-plan` only consulted the `UserSubscription` Stripe table, ignoring `User.admin_role` and `User.subscription_tier`. Added `_plan_from_user()` helper + `_TIER_TO_PLAN` map, made `get_user_plan()` admin-aware, switched the route to `Depends(get_current_user)` so the user object is available, and now report `subscription.source = "role" | "stripe" | "none"` plus `status = "active"` for admin/elite users without a Stripe row. Admins now correctly see **Validator** plan.
- **F2 (P0): "Accuracy 100% (17 predictions)" while the System Log clearly showed 5 LOSSES + 1 WIN.** Two independent sources of truth had drifted apart — the summary read `CLVEntry.bet_outcome` (only 1 row was populated → 1/1 = 100%) while the system log compared `Match.actual_outcome` to `Prediction.bet_side` (the real result). Introduced `_settled_predictions_for_user()` + `_wins_settled_streak()` helpers in `app/api/routes/dashboard.py` and rewired **`/summary`, `/leaderboard`, and `/achievements`** to all use the same match-outcome source the System Log uses. Response now also exposes `settled_predictions` and `wins` so the UI can show "X / Y settled" if needed.
- **F3 (P1): Streak stuck at `0` despite 100% win rate.** The previous code read `User.current_streak` which was never updated. The new `_wins_settled_streak()` walks settled predictions newest-first, counts the leading run of wins, and persists it back to `User.current_streak` so badges, leaderboard rows, and the level card all stay consistent.
- **F4 (P1): Community Predictions feed showed "PENDING" cards with empty Bet Side / Entry Odds / Stake / P&L.** These are predictions where the model found no edge (`bet_side IS NULL`) — useless to other users. `/history` now filters them out when `all_users=true` (the community scope) while still returning them on the user's own "My Predictions" tab so they can see every fixture they ran.

Inputs that were consistent and **not** changed: VIT Balance / Wallet conversions (different stored balances, not derivations of one another), the "12 Models Active / No model data yet" card (it correctly shows the next-match prediction, not historical accuracy), and the Achievements list (now driven by the corrected win rate).

## Recent Changes — Match-Aware AI Assistant (Apr 25 2026)

The AI Assistant is now embedded directly inside every match-detail page, with that fixture's prediction pre-loaded as context — users can ask things like *"Why does the model favor Arsenal here?"* or *"Is there value on Over 2.5 in this match?"* and get answers grounded in the actual numbers.

- **`frontend/src/components/MatchAssistantCard.tsx` (new):** Reusable collapsible chat card. Builds a structured context block from the match (teams, league, kickoff, FT score, 1X2 / O/U 2.5 / BTTS probabilities, model confidence, market odds, best-bet recommendation, top model contributors) and sends it with every message via the existing `useAssistantChat({ message, history, context })` hook. Match-specific suggested prompts are auto-generated from the team names and probability distribution.
- **`frontend/src/pages/match-detail.tsx`:** Card mounted at the top of the **Analysis** tab so the chat sits above the existing AIInsightComparison + Ensemble Intelligence panels. Collapsed by default to keep the page light; expands on click.
- **Backend reuse:** No new endpoints — the existing `POST /ai/assistant/chat` already accepts `context: Optional[str]`, so the card piggybacks on the same Gemini wrapper used by the standalone `/assistant` page.

## Recent Changes — Subscription / Markets / Training Gap-Fix (Apr 25 2026)

Closed five P0/P1 gaps found during a deep audit. All changes are wired front-to-back; backend imports clean, TypeScript clean, frontend rebuilt, server restarted, `/health` green.

- **G1 — Admin subscription pricing was unreachable (P0).** The frontend `SubscriptionsTab` was hitting `GET /admin/subscriptions` and `PUT /admin/subscriptions/{id}`, but **neither route existed in `app/api/routes/admin.py`** — admins literally could not view or change pricing. Added three endpoints under `get_current_admin`:
  - `GET /admin/subscriptions` — list every plan with id/name/display_name/price_monthly/price_yearly/prediction_limit/features/is_active.
  - `PUT /admin/subscriptions/{plan_id}` — partial update (price, limit, features, active flag) with audit-log entry capturing old→new diffs.
  - `POST /admin/subscriptions` — create a new plan with 409 conflict guard on `name`.
- **G2 — Training upload was destroying the dataset (P0).** `POST /api/training/dataset/upload` defaulted `merge=False`, so every upload **replaced** `historical_matches.json` instead of appending to it. Flipped the default to `merge=True` and added duplicate suppression on `(home_team, away_team, date)`. Response now also returns `duplicates_skipped` so users can see what was filtered.
- **G3 — Best-bet logic only knew H/D/A (P0).** `MarketUtils.determine_best_bet()` ranked only the 1X2 market, ignoring `over_25_prob`/`btts_prob` even though both were already computed by the orchestrator and stored on `Prediction`. Added a 2-way vig-removal helper and extended `determine_best_bet()` with optional `over_25_prob/under_25_prob/over_25_odds/under_25_odds/btts_prob/no_btts_prob/btts_yes_odds/btts_no_odds` params. Picks the highest-edge candidate across **1X2 + Over/Under 2.5 + BTTS** and returns a new `best_market` field plus the full `candidates` list. `app/api/routes/predict.py` now passes the orchestrator's O/U + BTTS probabilities and pulls the matching odds out of `match.market_odds` (`over_2_5`/`under_2_5`/`btts_yes`/`btts_no`).
- **G4 — Admin's own plan badge said "free" (P1).** `/auth/me` returned the raw `User.subscription_tier` which defaults to `"viewer"`, so the admin's own UI gates locked them out of paid features on their own platform. The endpoint now returns `subscription_tier="elite"` whenever `admin_role` is set, while preserving the original value as `raw_subscription_tier` for audit/display.
- **G5 — AI Source Performance had no refresh trigger (P1).** The "AI Source Performance" panel relied on something else writing to `ai_performances` first, so the table sat permanently empty on a fresh install. Added `useUpdateAiPerformance()` hook (POST `/ai/performance/update`) and a purple "Update Performance" button in the panel header that recomputes accuracy/Brier from settled match outcomes and invalidates both the performance and report queries on success.

**Verification**
- `python -c "..."` smoke test of the multi-market scorer → with `home=0.50, draw=0.25, away=0.25, O2.5=0.65@1.85, U2.5@2.0, BTTS yes=0.62@1.75, no@2.05` it correctly picks `over_2_5` (edge 0.1305) instead of the `home` 1X2 leg.
- `GET /admin/subscriptions` → 401 (mounted, auth-gated as designed).
- `PUT /admin/subscriptions/1` → 401 (mounted, auth-gated as designed).
- `npx tsc --noEmit --skipLibCheck` → 0 errors. `npm run build` → green. Backend `/health` → ok.

## Recent Changes — Polish & Bug-Fix Pass (Apr 25 2026)

Tightened both surfaces, fixed a runtime-breaking page, and hardened a couple of small UX rough edges. Full TypeScript pass (`npx tsc --noEmit --skipLibCheck`) now reports **zero errors**.

- **Tasks page (page-breaking bug):** `frontend/src/pages/tasks.tsx` referenced a `TaskActionRow` component in three places that was never defined — opening **/tasks** would throw `ReferenceError: TaskActionRow is not defined` and crash the route. Implemented the component locally with the props the call sites already passed (`task`, `status`, `canUpdate`, `ready`, `pending`, `actionUrl`, `onUpdate`). Internal/external links are detected and rendered with the correct affordance (`<Link>` vs `<a target="_blank">`), and the action button switches between "Mark Progress", "Claim Reward", "Completed" badge, and a "Locked" hint based on state. Also dropped the unused `useEffect` and `Sparkles` imports that survived in the file.
- **Developer page (React warning):** `frontend/src/pages/developer.tsx` mapped the now-dynamic endpoint list with `key={ep.path}`. The new `/api/developer/docs` endpoint emits one row per `(method, path)` pair, so paths with both `GET` and `DELETE` produced React duplicate-key warnings. Composite key `${ep.method}-${ep.path}` is used now.
- **AI Assistant page (a11y polish):** `frontend/src/pages/assistant.tsx` chat textarea now sets `name`, `autoComplete="off"`, `spellCheck`, and `aria-label` — kills the Chrome "input elements should have autocomplete attributes" warning seen on the assistant route and gives screen readers a clear field name.

## Recent Changes — Conversational AI Assistant (Apr 25 2026)

Added an in-app **AI Assistant** so any logged-in user can chat with the platform.

- **Backend:** `app/services/gemini_chat.py` wraps Gemini-1.5-Flash for multi-turn dialogue with a VIT-aware system prompt; `app/api/routes/ai_assistant.py` exposes `POST /ai/assistant/chat` (with history + optional context) and `GET /ai/assistant/status` (reports whether `GEMINI_API_KEY` is set). Both routes require auth (Bearer JWT or `X-API-Key`).
- **Frontend:** `frontend/src/pages/assistant.tsx` — full chat UI with streaming-style typing indicator, history-aware turns, suggested prompts, and graceful "key missing" fallback. Wired through `useAssistantChat` / `useAssistantStatus` hooks in `frontend/src/api-client/index.ts`. Routed at `/assistant` and surfaced in the **Pro** sidebar group.
- **Developer docs (same release):** `GET /api/developer/docs` now introspects the live FastAPI route table instead of returning a hand-written list, so the SDK reference always matches deployed reality.

## Recent Changes — Auto-Demotion Monitor (Apr 25 2026)

The accountability loop now **acts on its own signal** instead of just displaying it. Inside `model_accountability_loop` (main.py), after each weight refresh, `app/services/clv_streak_monitor.check_clv_streaks(db)` walks every active model and:

- If `clv_score < CLV_DEMOTE_THRESHOLD` (default −0.005) AND `clv_samples ≥ CLV_DEMOTE_MIN_SAMPLES` (default 50) → increment `clv_negative_streak_days` (max once per `CLV_CHECK_MIN_HOURS`, default 18h, so faster loops don't inflate the counter).
- Else → reset `clv_negative_streak_days = 0`.
- When the streak hits `CLV_DEMOTE_DAYS` (default 7) → flip `is_active=False` and `auto_demoted=True`. The predictor and weight adjuster already filter on `is_active=True`, so the model stops contributing immediately. A WARNING-level log entry tells the operator which model was demoted and why.

Manual **Reactivate** from the dashboard now clears both `clv_negative_streak_days` and `auto_demoted`, so a model that's been investigated isn't re-demoted on the next tick.

The dashboard's status badge now shows `Watch · day 3/7` and `At Risk · day 5/7` while the streak is climbing, and `Demoted (auto)` vs plain `Demoted` so operators can tell apart machine vs human action.

Migration adds `clv_negative_streak_days INTEGER DEFAULT 0`, `last_clv_check_at TIMESTAMP`, and `auto_demoted BOOLEAN DEFAULT FALSE` to `model_metadata` on both SQLite and PostgreSQL.

All four monitor paths verified end-to-end against the live DB: streak progression 1→7 with no early demotion, demotion firing exactly on tick 7, the cooldown guard skipping faster ticks, positive-CLV resetting the streak without demoting, and manual reactivation clearing the auto-demoted flag.

## Recent Changes — Model Accountability Dashboard (Apr 25 2026)

The CLV signal now has a UI. **Admin → Models → Accountability** renders the per-model CLV-blended scoreboard powered by `/api/ai-engine/performance`.

Per row: status badge (Healthy / Watch / At Risk / Demoted / Insufficient), weight, accuracy %, log-loss, Brier, **rolling CLV score** (green > 0, red < 0), CLV samples, total predictions, and a Demote / Reactivate button.

Status thresholds (computed client-side from a single snapshot — no streak tracking yet):
- Healthy: `clv_score > 0` and `accuracy >= 0.50`
- Watch: `clv_score < 0` or `accuracy < 0.50`
- At Risk: `clv_score < -0.005` with `clv_samples >= 50` (red banner shows at-risk count at the top of the card and on the sub-section button)
- Insufficient: `< 30` settled samples (skip judging until more data)

Backend: new `POST /admin/models/set-active` (admin-auth required) toggles `model_metadata.is_active`. Demoted models are skipped by the predictor's `is_active=True` filter and the weight adjuster's per-model lookup; their history is preserved.

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
