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

**Autonomous Agent System (21 agents):**
All agents inherit from `app/agents/base.py:BaseAgent` and are registered in `app/agents/coordinator.py`.

| Agent | Interval | Purpose |
|---|---|---|
| `live-match-tracker` | 60s | IN_PLAY match detection, live score updates, IoT broadcasts |
| `match-scout` | 10m | Pre-match (48h window, 5/cycle) + live tactical AI briefs |
| `news-sentinel` | 20m | Injury scraping + impact analysis (3 teams/cycle) |
| `odds-anomaly` | 15m | Odds movement detection + AI explanation |
| `analytics-reporter` | 24h | Daily brief + Monday weekly deep-dive |
| `ai-source-ranker` | 1h | Rank AI prediction sources by accuracy |
| `performance-monitor` | 30m | Model accuracy tracking |
| `weight-optimizer` | 6h | Dynamic model weight adjustment |
| `retrain-trigger` | 6h | Trigger retraining when accuracy drops |
| `data-pipeline` | 1h | Fetch & upsert fixtures, odds, injuries |
| `prediction-generator` | 30m | Generate predictions for upcoming matches |
| `accumulator-publisher` | 4h | Publish accumulator bets |
| `settlement-checker` | 5m | Check and settle finished matches |
| `revenue-optimizer` | 24h | Revenue analytics |
| `governance-executor` | 1h | Execute governance proposals |
| `self-healing` | 15m | Restart failed processes |
| `audit-sentinel` | 1h | Security audit logging |
| `prediction-moderator` | 1h | Flag suspicious predictions |

API endpoints:
- `GET /agents/status` — full agent status
- `GET /agents/summary` — lightweight health summary
- `POST /agents/trigger/{name}` — manual trigger
- `GET /agents/providers` — AI provider status
- `GET /agents/result/{name}` — last result for agent
- `GET /agents/reports` — recent AgentInsight feed (filterable)
- `GET /agents/live-scores` — current live match scores from DB

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
- **Puter AI:** Browser-side free Claude via Puter.js at `frontend/src/lib/puter-ai.ts`
- **WebSocket:** `frontend/src/lib/websocket.ts` — `vitWS.on("notification", cb)` for live events

## Agent Intelligence Data Flow
1. Agent `run_cycle()` → calls `call_ai(prompt)` → stores `AgentInsight` in DB → broadcasts via `store_and_broadcast()`
2. Frontend `reports.tsx` polls `GET /agents/reports` every 30s + listens to `vitWS` for `live_score_update`/`goal_scored`/`ai_signal` events
3. Live score ticker auto-populates from WebSocket events without page reload

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

## Key Files
- `main.py` — FastAPI app entry point, mounts all routers
- `app/agents/coordinator.py` — Agent registry and lifecycle manager
- `app/services/ai_client.py` — Shared multi-provider AI cascade
- `app/services/results_settler.py` — Match settlement pipeline
- `app/modules/ai/weight_adjuster.py` — EMA weight logic, bootstrap/reactivate functions, type priors
- `app/modules/ai/routes.py` — AI engine API routes incl. /performance/bootstrap and /performance/reactivate-zero-sample
- `app/services/clv_streak_monitor.py` — CLV auto-demotion (CLV_MIN_SAMPLES=50 guard)
- `app/db/models.py` — All SQLAlchemy models
- `frontend/src/App.tsx` — All frontend routes
- `frontend/src/lib/websocket.ts` — WS singleton `vitWS`
- `frontend/src/lib/puter-ai.ts` — Puter browser AI
- `scripts/start_fullstack.sh` — Dev startup script
