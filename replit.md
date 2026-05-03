# VIT Sports Intelligence Network

## Overview
The VIT Sports Intelligence Network is an institutional-grade football prediction platform that employs a 12-model AI ensemble for predictions. It integrates a VITCoin wallet economy, supports blockchain-verified staking, features a model marketplace, and includes a governance DAO. The platform offers multi-tier subscriptions and provides advanced sports analytics, real-time live match tracking, and AI agent intelligence reports. Its business vision is to deliver sophisticated, reliable sports predictions and foster a decentralized, community-driven ecosystem around sports intelligence.

## User Preferences
I prefer iterative development with a focus on clear, modular code. Please use functional programming paradigms where appropriate and provide detailed explanations for significant architectural decisions or complex algorithms. Ask before making major changes to the project structure or core functionalities.

## System Architecture
The platform is built with a microservices-oriented approach.

**Backend:**
- **Core Technology:** Python 3.11 with FastAPI and SQLAlchemy for asynchronous ORM.
- **Database:** SQLite (development) with WAL mode enabled, PostgreSQL (production).
- **AI Orchestrator:** Manages a 12-model AI ensemble with dynamic weight adjustment.
- **Multi-Provider AI Client:** Features a cascade fallback system (Gemini → Claude → OpenAI → xAI) with rate-limit awareness.
- **Authentication:** JWT and TOTP for secure 2FA authentication.
- **Prediction System:** Dynamically determines best bet sides and consensus probabilities across various markets.
- **Settlement Pipeline:** Processes match results, updates profit, and attributes CLV.
- **Notification System:** Multi-channel email, Telegram DMs, and in-app WebSockets.
- **Autonomous Agent System:** Comprises 22 agents inheriting from `BaseAgent`, each with a `node_id` and responsible for specific tasks (e.g., `live-match-tracker`, `match-scout`, `news-sentinel`, `oracle-node`, `network-guardian`). Agents record network contributions.
- **VIT Oracle:** A blockchain consensus layer that aggregates match results from agent nodes.
- **VIT DID (Decentralized Identity):** W3C-compliant DID documents for users and agents, with Verifiable Credentials issued by the network.
- **VIT Network Node System:** Tracks `NodeActivity` for agents and aggregates hourly `NetworkSnapshot` data.
- **VIT SCIE (Self-Contained Intelligence Engine):** A zero-external-API dependency layer providing functionalities like `synthetic_odds`, `get_team_form`, `get_head_to_head`, and template fallbacks for agents.
- **ML Accountability System:** Tracks performance metrics for 24 models (12 base + 12 v2) with mechanisms for bootstrapping and reactivating models.
- **Quant Module:** Provides endpoints for financial analysis including `summary`, `backtest`, `monte-carlo` simulations, `ev-scanner`, and `strategy-optimizer`.

**Frontend:**
- **Core Technology:** React 19, TypeScript, Vite, TailwindCSS 4, ShadCN UI.
- **State Management:** `@tanstack/react-query` for server state, `vitWS` singleton for WebSocket.
- **Key Pages:** Includes dashboards for matches, AI agent reports, agent monitoring, match details with AI insights, AI source management, oracle health, and network statistics.
- **Puter AI Integration:** Browser-side AI via Puter.js.

## External Dependencies
- **Football-Data.org:** Live and finished match data. NOTE: This API is unreachable from the Replit sandbox environment (ConnectTimeout on all requests). The system falls back entirely to synthetic match data and simulated FT results.
- **Transfermarkt:** Injury data (scraped).
- **Resend.com / SMTP:** Email notifications.
- **Telegram Bot API:** User DMs and webhooks.
- **Gemini API:** Primary AI provider.
- **Anthropic API (Claude):** Fallback AI provider.
- **OpenAI API:** Fallback AI provider.
- **xAI (Grok):** Fallback AI provider.
- **Puter.js:** Browser-side AI.
- **Stripe:** Subscription checkout.
- **Paystack:** NGN deposits.

## Data & Match Pipeline

### Football API Network Status
The football-data.org API endpoint (`api.football-data.org:443`) is **blocked at the network level** from this Replit environment. DNS resolves correctly but TCP connections timeout. This is a Replit sandbox restriction, not an API key issue. The system operates correctly in offline mode using:
1. Synthetic match fixtures (real team names, realistic odds)
2. Deterministic FT score simulation via `ft_backfill.py` for past matches
3. Network-level circuit breaker in `results_settler.py` (10-minute backoff after first ConnectTimeout)

### Match Status Values
The system uses lowercase status values throughout:
- `upcoming` — scheduled future match (not yet kicked off)
- `scheduled` — alternative for upcoming (legacy)
- `live` — match in progress (live tracker active)
- `in_play` — alternative for live
- `completed` — match finished (has actual_outcome set)
- `finished` — alternative for completed

### Match Sources
- `footballdata` — from Football-Data.org API (real)
- `synthetic` — placeholder data with real team names (no API)
- `synthetic+sim_ft` — synthetic match with simulated FT score
- `predict` — auto-created when a prediction request references unknown match
- `manual_upload` — uploaded via CSV
- `unknown` — legacy/untracked (should not appear in healthy DB)

### Deduplication
Matches are deduplicated via:
1. `external_id` (Football-Data.org match ID)
2. Content fingerprint: SHA256 of `date::home::away::league` (first 16 hex chars)
3. Exact team name + 24-hour kickoff window fallback (predict.py)

## Performance Optimizations Applied
- **Football API timeout:** Reduced from 15s → 5s, retries 5 → 2 (`football_api.py`)
- **Results settler timeout:** Reduced from 30s/15s → 8s (`results_settler.py`)
- **SQLite WAL mode:** Enabled for concurrent read/write (`database.py`)
- **npm install skip:** Skipped on startup if node_modules exists (`start_fullstack.sh`)
- **Network circuit breaker:** After first ConnectTimeout, all football API calls skip for 10 minutes (`results_settler.py`)
- **Live tracker cycle time:** Was 80s (10 leagues × 8s timeout), now 0.01s (circuit opens after first timeout)
- **Admin fetch fixtures timeout:** 20s → 8s (`admin.py`)

## Database State (as of last cleanup)
- 20 total matches: 6 completed (with simulated FT scores), 14 upcoming
- No duplicates, no test data, no fake seeded matches with `source=unknown`
- Past matches (kickoff > 2h ago) are auto-completed by `LiveMatchTrackerAgent._auto_complete_past_matches()`
- Startup seeding: tries Football API first, falls back to synthetic if API unreachable

## Key Files
- `main.py` — startup lifecycle, fixture seeding logic (lines ~1070-1150)
- `app/db/models.py` — Match model (status, home_goals/away_goals columns)
- `app/agents/live_match_tracker_agent.py` — live tracking + auto-completion of past matches
- `app/services/ft_backfill.py` — FT result simulation for local/synthetic matches
- `app/services/results_settler.py` — API settlement with circuit breaker
- `app/services/football_api.py` — FootballDataClient (timeout 5s, retries 2)
- `app/db/database.py` — SQLite WAL mode
- `app/api/routes/predict.py` — Match find-or-create with 3-level dedup
- `app/api/routes/matches.py` — Match CRUD endpoints (prefix: `/matches/`)
- `scripts/start_fullstack.sh` — startup script
