# VIT Sports Intelligence Network

## Overview
The VIT Sports Intelligence Network is an institutional-grade football prediction platform (v4.7.5). It utilizes a 12-model AI ensemble for predictions, integrates a VITCoin wallet economy, supports blockchain-verified staking, features a model marketplace, and includes a governance DAO. The platform offers multi-tier subscriptions (Free, Pro, Elite) and provides advanced sports analytics, real-time live match tracking, and AI agent intelligence reports.

## User Preferences
I prefer iterative development with a focus on clear, modular code. Please use functional programming paradigms where appropriate and provide detailed explanations for significant architectural decisions or complex algorithms. Ask before making major changes to the project structure or core functionalities.

## System Architecture
The platform is built with a microservices-oriented approach.

**Backend:**
- **Core Technology:** Python 3.11 with FastAPI, SQLAlchemy for asynchronous ORM.
- **Server:** Uvicorn serves the application on port 8000, Vite dev server on port 5000.
- **Database:** SQLite (dev), PostgreSQL (prod). Models in `app/db/models.py`.
- **AI Orchestrator:** Manages a 12-model AI ensemble, loading trained `.pkl` weights and per-model calibrators. CLV-blended weight adjuster for dynamic model contribution updates.
- **Multi-Provider AI Client:** `app/services/ai_client.py` — shared `call_ai()` with cascade: Gemini → Claude → OpenAI → xAI (grok). Rate-limit awareness and automatic fallback.
- **Authentication:** JWT and TOTP for secure authentication, including 2FA with DB-backed token revocation and brute-force protection.
- **Prediction System:** Dynamically determines best bet sides, consensus probabilities, and model probabilities for various markets.
- **Settlement Pipeline:** `app/services/results_settler.py` — processes match results, updates `was_correct`, `settled_profit`, CLV attribution, bankroll updates.
- **Notification System:** Multi-channel: email (HTML templates), Telegram DMs (per-user), in-app WebSockets.
- **IoT Stream:** `app/iot/processor.py` — `store_and_broadcast()` sends events to all connected WebSocket clients.

**Autonomous Agent System (22 agents):**
All agents inherit from `app/agents/base.py:BaseAgent` and are registered in `app/agents/coordinator.py`.
Each agent has a `node_id` (DID: `did:vit:agent:{name}`) and logs a `NodeActivity` record after every successful cycle via `_record_network_contribution()`.

| Agent | Interval | Purpose |
|---|---|---|
| `live-match-tracker` | 60s | IN_PLAY match detection, live score updates, IoT broadcasts |
| `match-scout` | 10m | Pre-match (48h window, 5/cycle) + live tactical AI briefs |
| `news-sentinel` | 20m | Injury scraping + impact analysis (3 teams/cycle) |
| `odds-anomaly` | 15m | Odds movement detection + AI explanation |
| `analytics-reporter` | 24h | Daily brief + Monday weekly deep-dive |
| `performance-monitor` | 30m | Model accuracy tracking |
| `weight-optimizer` | 6h | Dynamic model weight adjustment |
| `retrain-trigger` | 12h | Trigger retraining when accuracy drops |
| `fixture-gap` | 30m | Detect fixture data gaps |
| `accumulator-publisher` | 4h | Publish accumulator bets |
| `revenue-optimizer` | 24h | Revenue analytics |
| `governance-executor` | 10m | Execute governance proposals |
| `self-healing` | 5m | Restart failed processes |
| `audit-sentinel` | 24h | Security audit logging |
| `prediction-moderator` | 20m | Flag suspicious predictions |
| `kyc-screener` | 10m | KYC review processing |
| `fraud-review` | 15m | Fraud flag resolution |
| `withdrawal-gatekeeper` | 5m | Withdrawal risk checks |
| `marketplace-audit` | 30m | Marketplace listing review |
| `model-promoter` | 2h | Promote top-performing models |
| `oracle-node` | 10m | Submits DB match results to oracle consensus layer |
| `network-guardian` | 1h | Issues node VCs, creates NetworkSnapshots, manages DID registry |

API endpoints:
- `GET /agents/status` — full agent status
- `GET /agents/summary` — lightweight health summary
- `POST /agents/trigger/{name}` — manual trigger
- `GET /agents/providers` — AI provider status
- `GET /agents/result/{name}` — last result for agent
- `GET /agents/reports` — recent AgentInsight feed (filterable)
- `GET /agents/live-scores` — current live match scores from DB

**VIT Oracle (`app/modules/blockchain/oracle.py` + `/api/oracle/*`):**
- Oracle consensus layer that aggregates match result submissions from agent nodes.
- `oracle-node` agent auto-submits finalized DB results every 10 minutes.
- `GET /api/oracle/stats` — submission counts, consensus rate, recent oracle results.
- `GET /api/oracle/results` — paginated oracle results with source breakdown.

**VIT DID — Decentralized Identity (`app/modules/did/`):**
- W3C-compliant DID documents for every user and agent: `did:vit:{uuid5}` (users), `did:vit:agent:{name}` (agents).
- Verifiable Credentials (VCs) issued by `did:vit:network` issuer.
- Tables: `vit_identities`, `verifiable_credentials`.
- `GET /api/did/registry` — admin: list all registered DIDs.
- `GET /api/did/agent/{name}` — resolve agent DID (public).
- `GET /api/did/user/{user_id}` — admin: resolve/create user DID.
- `GET /api/did/credentials/{identity_id}` — list VCs for an identity.
- `POST /api/did/credentials/issue` — admin: issue a VC.
- `POST /api/did/user/register` — self-register caller's DID.
- `GET /api/did/{did}` — resolve any `did:vit:` DID document (catch-all, must stay last).
- Route ordering critical: specific routes (`/registry`, `/credentials/…`, `/user/…`, `/agent/…`) MUST precede `/{did:path}`.

**VIT Network Node System (`app/modules/network/`):**
- Every agent cycle records a `NodeActivity` row (`activity_meta` column — NOT `metadata`, reserved by SQLAlchemy).
- `NetworkSnapshot` stores hourly network health aggregates (created by `network-guardian`).
- Tables: `node_activities`, `network_snapshots`.
- `GET /api/network/stats` — total nodes, active nodes, contributions, health score.
- `GET /api/network/nodes` — per-node contribution leaderboard.
- `GET /api/network/growth?hours=N` — hourly contribution buckets.
- `GET /api/network/activity` — raw recent activity feed.

**Frontend:**
- **Core Technology:** React 19, TypeScript, Vite, TailwindCSS 4, ShadCN UI. Runs on port 5000.
- **Routing:** `wouter` — all routes in `frontend/src/App.tsx`.
- **State:** `@tanstack/react-query` for server state. `vitWS` singleton for WebSocket.
- **Key Pages:**
  - `/matches` — Intelligence Feed with live/upcoming/completed match cards
  - `/reports` — Real-time AI agent intelligence dashboard (live scores, expandable reports)
  - `/agents` — Agent system monitor
  - `/match/:id` — Match detail with AI insight comparison (4 providers inc. Puter)
  - `/ai-sources` — Admin AI source management (upcoming/live only, no past fixtures)
  - `/oracle` — VIT Oracle node health, submission stats, recent oracle results
  - `/network` — Node Network: DID registry, contribution leaderboard, network growth chart
- **Puter AI:** Browser-side free Claude via Puter.js at `frontend/src/lib/puter-ai.ts`
- **WebSocket:** `frontend/src/lib/websocket.ts` — `vitWS.on("notification", cb)` for live events

## Agent Intelligence Data Flow
1. Agent `run_cycle()` → calls `call_ai(prompt)` → stores `AgentInsight` in DB → broadcasts via `store_and_broadcast()`
2. Agent `_record_network_contribution()` → POSTs `NodeActivity` to DB → reflected in `/api/network/stats`
3. Frontend `reports.tsx` polls `GET /agents/reports` every 30s + listens to `vitWS` for `live_score_update`/`goal_scored`/`ai_signal` events
4. Live score ticker auto-populates from WebSocket events without page reload

## VIT SCIE — Self-Contained Intelligence Engine
`app/services/vit_intelligence.py` — zero external API dependency layer:
- `synthetic_odds(home, away)` — deterministic probability model using team name hash + form proxies
- `get_team_form(team, db)` — queries DB match history for recent W/D/L streak
- `get_head_to_head(home, away, db)` — head-to-head stats from historical matches
- `get_match_context(match, db)` — full pre-match context bundle (form + H2H + odds)
- `build_scout_prompt(match, context)` — builds match-scout prompt without external odds
- `detect_probability_drift(match, db)` — ML-based anomaly detection from DB probability deltas
- `build_league_snapshot(league, db)` — league form table from stored match data

**SCIE Template Fallbacks** — agents always produce output even when all AI providers fail:
- `analytics_reporter_agent._template_brief()` — structured daily/weekly brief from DB metrics alone
- `news_sentinel_agent` — generates structured JSON injury brief from Transfermarkt data (no AI needed)

## External Dependencies
- **Football-Data.org:** Live and finished match data (v4 API)
- **Transfermarkt:** Injury data (scraped — working, fetches ~68 injuries)
- **Resend.com / SMTP:** Email notifications
- **Telegram Bot API:** Per-user DMs and webhooks
- **Gemini API:** Primary AI (free tier, `GEMINI_API_KEY`) — rate-limited on heavy load
- **Anthropic API:** Claude fallback (`CLAUDE_API_KEY`) — check key validity if 401
- **OpenAI API:** Third fallback (`OPENAI_API_KEY`) — rate-limited on heavy load
- **xAI (Grok):** Fourth fallback (`XAI_API_KEY`, models: `grok-3-mini`, `grok-2-1212`, `grok-2`, `grok-3`)
- **Puter.js:** Browser-side free AI (no key needed)
- **Stripe:** Subscription checkout (`STRIPE_WEBHOOK_SECRET`)
- **Paystack:** NGN deposits (`PAYSTACK_WEBHOOK_SECRET`)

## ML Accountability System
The CLV-Blended Accountability dashboard (`/admin` → Accountability tab) tracks 24 models (12 base + 12 v2):
- `GET /api/ai-engine/performance` — returns per-model metrics with `metric_source` ("live"|"bootstrapped"|null) and `training_metrics` from version_history
- `POST /api/ai-engine/performance/bootstrap` — seeds brier/log_loss/accuracy for models with <5 live predictions using training pkl metrics (priority 1) or model-type benchmark priors (priority 2). Safe to re-run; live models skipped. `?force=true` resets existing bootstrapped values.
- `POST /api/ai-engine/performance/reactivate-zero-sample` — reactivates demoted models with 0 settled predictions (no empirical basis for demotion)
- EMA warm-start: model-type priors used as fallback instead of random baseline (brier=0.444/log_loss=log(3)) when no live value exists
- `BOOTSTRAP_LIVE_THRESHOLD=5` — minimum predictions to treat metrics as "live"
- Frontend shows `~` prefix and `est` label on bootstrapped metrics; Bootstrap + Reactivate buttons in accountability card header

## Phase 2 — VIT Quant Engine (completed 2026-05-02)

### New Module: `app/modules/quant/routes.py`
Five async endpoints under `/api/quant/`, all requiring auth:

| Endpoint | Description |
|---|---|
| `GET /api/quant/summary` | Headline stats: win rate, ROI, avg odds, avg EV across all settled predictions |
| `GET /api/quant/backtest` | Replay settled predictions as flat (fixed %) and full-Kelly staking curves; returns bankroll history + max drawdown |
| `GET /api/quant/monte-carlo` | N-trial simulation sampling from historical distribution; returns ruin %, profit %, percentile table (p5/p25/p50/p75/p95), full distribution array |
| `GET /api/quant/ev-scanner` | EV = p×(odds-1) - (1-p) for each market; live upcoming or historical fallback; uses `closing_odds_home/draw/away` |
| `GET /api/quant/strategy-optimizer` | Segment predictions by bet_side × confidence × odds range; returns ROI for each segment, flags best |

**Schema notes:** `Prediction` uses `timestamp` (not `created_at`). `Match` uses `kickoff_time`, `closing_odds_home/draw/away` (not `match_date`, `home/draw/away_odds`).

### New Frontend: `frontend/src/pages/research.tsx`
Bloomberg-style Research Terminal at `/research` (Pro nav group). Four panels:
- **Strategy Backtester** — configurable bankroll + flat%, dual line chart (flat=blue, kelly=green)
- **Monte Carlo Simulator** — configurable trials/bets/staking; histogram coloured by profit/loss; percentile bar
- **EV Scanner** — tabular signal list with side badges, edge%, EV highlight; auto-detects live vs historical mode
- **Strategy Optimiser** — accordion list sorted by ROI; best strategy badged; expandable detail row

Registered in `App.tsx` at `/research`. Added "Research" nav item with `FlaskConical` icon in layout.tsx Pro group. Uses `recharts` (already installed) and `@tanstack/react-query`.

## Phase 1 — Sealed Cracks (completed 2026-05-02)

### 1. Real Email Delivery
- **`app/services/email_service.py`** — Added `send_verification_email()` and `send_password_reset_email()` with VIT-branded HTML, CTA button, and TTL info. Both try Resend first (`RESEND_API_KEY`), fall back to SMTP (`SMTP_HOST`), fall back to console log in dev.
- **`app/auth/verification.py`** — Replaced the old `_send_email` stub with direct calls to the above. Imports `send_verification_email`, `send_password_reset_email` from `email_service`. Dev mode exposes `dev_token` + `dev_link` in the response only when neither transport is configured.

### 2. Retraining Pipeline
- **`app/tasks/retraining.py`** — Replaced the log-only stub. `run_training_subprocess()` is an `async` function that launches `scripts/train_models.py` via `asyncio.create_subprocess_exec()`, streams stdout to the logger in real-time, and returns a structured `{status, returncode, stdout_tail, started_at, finished_at}` dict. Celery task (`retrain_models_task`) wraps it synchronously when Celery is available. `_AsyncShimTask` fires it as a `loop.create_task()` when Celery is absent. `retrain_trigger` agent continues to use `.delay()` — works in both modes.

### 3. Offerwall Completion Endpoint
- **`app/modules/rewards/routes.py`** — Added `POST /api/rewards/complete/{offer_id}`. Idempotency: one-time categories (`onboarding`, `activity`, `referral`, `education`) = one claim ever; daily categories (`streak`, `survey`, `quiz`) = one claim per UTC calendar day. Uses `sha256(internal:{user_id}:{offer_id}:{window})` as the `provider_payload_hash` idempotency key. Credits VITCoin via `WalletService.deposit_vitcoin()`, creates `OfferCompletion` with `status="confirmed"`, `provider="internal"`. Returns `409` on duplicate claim.
- **Schema fix:** `offer_completions.updated_at` was NOT NULL with no INSERT default — fixed by passing `updated_at=now` explicitly on create. `email_tokens.used_at` column was missing from DB — fixed with `ALTER TABLE email_tokens ADD COLUMN used_at DATETIME`.

### 4. Leaderboard XP + Streak Settlement
- **`app/services/results_settler.py`** — Both settlement paths (`settle_results` and `settle_completed_db_matches`) now update the user record after each prediction is settled: `+50 XP` on win, `+10 XP` on loss, `current_streak += 1` on win (reset to 0 on loss), `best_streak` updated if exceeded. All wrapped in try/except so a DB error here is non-fatal to settlement. `User` model imported at the top.

## Key Files
- `main.py` — FastAPI app entry point, mounts all routers
- `app/agents/coordinator.py` — Agent registry and lifecycle manager
- `app/agents/base.py` — BaseAgent with node_id, contribution_count, _record_network_contribution()
- `app/agents/oracle_node_agent.py` — Oracle node agent (auto-submits match results)
- `app/agents/network_guardian_agent.py` — DID registry manager + VC issuer + NetworkSnapshot creator
- `app/modules/did/models.py` — VITIdentity, VerifiableCredential SQLAlchemy models
- `app/modules/did/engine.py` — DID generation, resolution, VC issuance logic
- `app/modules/did/routes.py` — DID API routes (route order critical: specific before /{did:path})
- `app/modules/network/models.py` — NodeActivity (activity_meta), NetworkSnapshot models
- `app/modules/network/routes.py` — Network stats/nodes/growth API routes
- `app/services/ai_client.py` — Shared multi-provider AI cascade
- `app/services/results_settler.py` — Match settlement pipeline
- `app/modules/ai/weight_adjuster.py` — EMA weight logic, bootstrap/reactivate functions, type priors
- `app/modules/ai/routes.py` — AI engine API routes incl. /performance/bootstrap and /performance/reactivate-zero-sample
- `app/services/clv_streak_monitor.py` — CLV auto-demotion (CLV_MIN_SAMPLES=50 guard)
- `app/db/models.py` — Core SQLAlchemy models
- `frontend/src/App.tsx` — All frontend routes
- `frontend/src/lib/websocket.ts` — WS singleton `vitWS`
- `frontend/src/lib/puter-ai.ts` — Puter browser AI
- `scripts/start_fullstack.sh` — Dev startup script (imports all modules for create_all)
