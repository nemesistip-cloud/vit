# VIT Sports Intelligence Network

## Overview
The VIT Sports Intelligence Network is an institutional-grade football prediction platform that employs a 12-model AI ensemble for predictions. It integrates a VITCoin wallet economy, supports blockchain-verified staking, features a model marketplace, and includes a governance DAO. The platform offers multi-tier subscriptions and provides advanced sports analytics, real-time live match tracking, and AI agent intelligence reports. Its business vision is to deliver sophisticated, reliable sports predictions and foster a decentralized, community-driven ecosystem around sports intelligence.

## Gap Fixes Applied (vit_master_fix_prompts)
- **G01** WebSocket JWT: `frontend/src/lib/websocket.ts` sends `?token=<jwt>` in WS URL; close code 4001 triggers logout + redirect.
- **G02** Redis rate limiting: `app/api/middleware/rate_limit.py` uses Lua atomic sliding window via REDIS_URL, falls back to in-memory deque.
- **G03** Stripe webhook enforcement: `app/modules/wallet/webhooks.py` returns 503 if STRIPE_WEBHOOK_SECRET not set; 400 on bad signature.
- **G04** Email verification tokens DB-backed: already fully implemented in `app/auth/verification.py`.
- **G05** Paystack deposit verify: already fully implemented at `POST /api/wallet/deposit/verify`.
- **G06** Base L2 chain status: `app/services/base_chain.py` + `GET /api/blockchain/chain-status` + `GET /api/blockchain/chain-balance/{address}`.
- **G08** Offerwall completions: `GET /api/rewards/my-completions` paginated endpoint added to `app/modules/rewards/routes.py`.
- **G09** Developer API billing: `bill_api_call()` in `app/modules/developer/service.py`; `POST /api/developer/keys/{id}/bill` route deducts VITCoin (free plan = no charge; paid plans deduct price_per_1k/1000).
- **G10** Governance close + quorum: `POST /api/governance/proposals/{id}/close` admin endpoint added; quorum enforced in `_auto_close_if_needed`.
- **G11** Trust engine graduated actions: `_apply_trust_actions()` in `app/modules/trust/engine.py` — score <15 freezes withdrawals, <30 suspends account (if flags), <50 flags for review.
- **G13** 2FA frontend: already fully implemented in `frontend/src/pages/settings.tsx`.

## User Preferences
I prefer iterative development with a focus on clear, modular code. Please use functional programming paradigms where appropriate and provide detailed explanations for significant architectural decisions or complex algorithms. Ask before making major changes to the project structure or core functionalities.

## System Architecture
The platform is built with a microservices-oriented approach.

**Backend:**
- **Core Technology:** Python 3.11 with FastAPI and SQLAlchemy for asynchronous ORM.
- **Database:** SQLite (development) with WAL mode enabled, PostgreSQL (production).
- **AI Orchestrator:** Manages a 12-model AI ensemble with dynamic weight adjustment.
- **Multi-Provider AI Client:** Features a cascade fallback system (Gemini → Claude → OpenAI → xAI/Grok → Puter) with rate-limit awareness. Keys shorter than 10 chars are skipped as invalid placeholders.
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

## Odds System
- **The Odds API (`ODDS_API_KEY`):** Live bookmaker odds for `/odds/compare` and `/odds/arbitrage`. Correct sport keys used across both `odds_compare.py` and `odds_api.py` (e.g. `soccer_efl_champ`, `soccer_eredivisie`, `soccer_primeira_liga`, `soccer_jupiler_pro_league`, `soccer_spain_la_liga`, etc.). Responses include `requests_remaining` from the `x-requests-remaining` header.
- **Frontend odds page:** Auto-fetches on league selection (`enabled: !!league`), polls every 60 s (`refetchInterval: 60_000`), shows a live freshness bar with countdown, "last updated" timestamp, and API calls remaining.

## External Dependencies
- **TheSportsDB (free, no auth):** Primary fixture source. Free API (key=3) fetches real upcoming and past events for 8 leagues (EPL, La Liga, Bundesliga, Serie A, Ligue 1, Champions League, Eredivisie, Primeira Liga) via `eventsnextleague`, `eventspastleague`, and `eventsday` endpoints. Returns ~58 real fixtures per full sync (16 settled + 42 upcoming).
- **Football-Data.org:** BLOCKED — ConnectTimeout on all requests from Replit sandbox. Removed from active code; legacy references remain in results_settler.py.
- **Transfermarkt:** Injury data (scraped).
- **Resend.com / SMTP:** Email notifications.
- **Telegram Bot API:** User DMs and webhooks.
- **Gemini API:** Primary AI provider.
- **Anthropic API (Claude):** Fallback AI provider.
- **OpenAI API:** Fallback AI provider.
- **xAI (Grok):** Fallback AI provider (4th in cascade).
- **Puter.js:** Browser-side AI (free, no key needed) — puter.js loaded in index.html, `frontend/src/lib/puter-ai.ts` provides `puterChat()` and `analyzeMatchWithPuter()`. Server-side Puter via `PUTER_API_KEY` (5th provider in cascade).
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

## Bug Fixes Applied (v4.7.5 patch session)

### AI Provider Cascade (`app/services/ai_client.py`)
- **Grok model names updated:** Removed deprecated `grok-2` and `grok-beta` (both returned HTTP 400). Now uses `grok-3-mini` and `grok-2-1212`.
- **30-minute backoff on auth failures:** `_mark_provider_failed()` now also sets `_backoff_until` for 30 min. Previously providers that returned 401/403/400 were marked failing but still retried on every single request, wasting time and filling logs.
- **Early break on auth failure:** `_try_claude` and `_try_grok` now `break` immediately on 401/403/400 — no point trying remaining models with the same broken key.

### Match Sync Logging (`app/api/routes/matches.py`)
- **Empty error messages fixed:** `str(e)` on `ConnectError`/`TimeoutException` returns `""`. Changed to `[ExceptionType] repr(e)` so failed leagues now show the actual error in logs.

### Sports-Skills Startup Warning (`app/services/live_ai_feed.py`)
- **Misleading pip install message removed:** `sports-skills` doesn't exist on PyPI. Changed `WARNING` to an `INFO` message that correctly states the integration is simply disabled.

### Vite Startup Flags (`scripts/start_fullstack.sh`)
- **Duplicate `--host --port` flags eliminated:** `package.json` dev script already contains `--host 0.0.0.0 --port 5000`. The start script no longer appends them again (was causing `vite ... --port 5000 --host 0.0.0.0 --port 5000`).

### Odds Anomaly Agent (`app/agents/odds_anomaly_agent.py`)
- **Removed isolated Grok HTTP client:** Agent had its own raw `httpx` POST to `grok-beta` (deprecated model). Replaced with the shared cascade `call_ai()` so it benefits from multi-provider fallback and updated model names.

### News Sentinel Agent (`app/agents/news_sentinel_agent.py`)
- **Silent scraper fallback now logged:** Added explicit `INFO` log when scraper returns no data and the agent switches to SCIE fallback mode.

### AI Support Route (`app/api/routes/ai_support.py`)
- **Replaced Gemini-only implementation with cascade:** Was calling its own isolated Gemini HTTP client (would fail hard if Gemini was rate-limited). Now uses `call_ai()` (Gemini → Claude → OpenAI → Grok cascade).
- **Support `/status` endpoint now reports real provider availability** instead of just whether a Gemini key is set.

### Puter AI Frontend (`frontend/src/lib/puter-ai.ts`, `frontend/src/pages/ai-sources.tsx`)
- **Multi-account support:** Added `PuterAccountPanel` component showing signed-in username with sign-in/out/switch buttons.
- **Rate limit handling:** Inter-call delay raised 2s → 3.5s; on rate limit hit, shows toast + 15s cooldown before continuing.
- **Retry with exponential backoff:** `withRetry()` wraps all Puter calls (max 4 attempts, 10s base delay).

### Backend Rate Limiter (`app/api/middleware/rate_limit.py`)
- **Raised limits:** Anonymous 30→60, auth 120→180, JWT 300 req/min.
- **JWT-based keying:** Authenticated users identified by user ID from JWT payload (not just IP).
- **Extended bypass paths:** Added `/ws`, `/webhook`, `/api/public`, `/notifications/ws`.

## Database State (as of last cleanup)
- 20 total matches: 6 completed (with simulated FT scores), 14 upcoming
- No duplicates, no test data, no fake seeded matches with `source=unknown`
- Past matches (kickoff > 2h ago) are auto-completed by `LiveMatchTrackerAgent._auto_complete_past_matches()`
- Startup seeding: tries Football API first, falls back to synthetic if API unreachable

## 6-Phase Intelligence Upgrade (v5.0)

### Phase 1 — Feature Intelligence Upgrade
- `app/data/feature_engineering.py` — v2.0 rewrite: xG features, referee stats, rest days, odds velocity, Poisson helpers, `compute_source_quality`.

### Phase 2 — Specialized Market Models
- `app/ai/market_models.py` — BTTSModel, OverUnderModel, CorrectScoreModel (PyTorch neural nets + feature vector builders).
- `app/ai/market_trainer.py` — full async training pipeline with joblib save/load.
- `app/api/routes/market_training.py` — REST endpoints: train/btts, train/ou, train/cs, predict/btts, predict/ou, predict/cs, status.

### Phase 3 — Puter Distributed Compute
- `app/modules/quant/routes.py` — `POST /api/quant/monte-carlo/puter`: parallel shard Monte Carlo execution with synchronous fallback.

### Phase 4 — Vector Similarity Engine
- `app/services/vector_similarity.py` — numpy brute-force cosine similarity index (`SimilarityEngine` singleton; FAISS-ready).
- `app/api/routes/similarity.py` — `GET /api/similarity/matches`, `POST /api/similarity/matches/query`, `POST /api/similarity/rebuild`, `GET /api/similarity/status`.

### Phase 5 — RL Reward Loop
- `app/services/rl_reward.py` — reward functions, `RLRewardAccumulator` (EMA signals on settled bets).
- `app/agents/weight_optimizer.py` — `_apply_rl_rewards()` reads accumulator EMA and nudges `ModelMetadata.weight`.

### Phase 6 — Staked Model Marketplace
- `app/modules/marketplace/models.py` — `ModelStake` + `ModelSlashEvent` ORM tables; `total_staked`/`staker_count` on `AIModelListing`.
- `app/modules/marketplace/service.py` — staking service: `stake_model`, `unstake_model`, `distribute_staker_earnings` (auto-called from `call_model`), `admin_slash_stakes`, `get_slash_history`.
- `app/modules/marketplace/routes.py` — staking endpoints: POST/DELETE `/models/{id}/stake`, GET `/models/{id}/stakes`, GET `/my-stakes`, POST `/admin/models/{id}/slash`, GET `/models/{id}/slashes`.
- `frontend/src/pages/marketplace.tsx` — `StakeModal` (stake/unstake/view stakers), `MyStakesTab` (portfolio view with earnings/slash tracking), staking badges on model cards, slashing risk documentation.

## v4.12.0 — Blockchain Expansion & AI Intelligence Layer

### Blockchain Analytics (new in v4.12.0)
- `app/modules/blockchain/models.py` — 3 new tables: `ValidatorSlashEvent`, `OracleDispute`, `BlockchainTransaction`. `UserStake` gains `ah_line` for AH stakes.
- `app/modules/blockchain/auto_slash.py` — Automated slashing engine with configurable thresholds (missed rounds, accuracy drop, inactivity).
- `app/modules/blockchain/analytics.py` — Network stats (`get_network_stats`), leaderboard (`get_validator_leaderboard`), token economics (`get_token_economics`).
- `app/modules/blockchain/consensus.py` — Dynamic AI/validator weighting: `_dynamic_weights()` — <3 validators → AI=0.85, quality signal maps validator weight 0.15→0.65.
- `app/modules/blockchain/settlement.py` — Asian Handicap (push/win/lose) + Correct Score (`cs_N-M`) settlement logic.
- `app/api/routes/blockchain_analytics.py` — 8 endpoints: `/analytics/network`, `/analytics/leaderboard`, `/analytics/economics`, `/analytics/slash-history`, `/analytics/auto-slash`, `/validators/{id}/slash`, `/disputes`, `/disputes/{id}/resolve`.

### AI Intelligence (new in v4.12.0)
- `app/services/openai_advanced.py` — Injury impact analysis, accumulator builder, market regime detector, governance AI.
- `app/services/grok_advanced.py` — Social sentiment, news momentum, team form narrative, breaking news scanner.
- `app/api/routes/ai_intelligence.py` — 8 endpoints: `/openai/injuries`, `/openai/accumulator`, `/openai/market-regime`, `/openai/governance`, `/grok/sentiment`, `/grok/news-momentum`, `/grok/form-narrative`, `/grok/breaking-news`.

### Frontend Improvements (v4.12.0)
- **match-detail.tsx** — 4-tab staking market: 1X2, Goals (Over/Under + BTTS), Asian Handicap (with AH line input + "Use AI Line"), Correct Score (4×4 scoreline grid with CS probabilities from model).
- **validators.tsx** — `NetworkAnalyticsPanel` component with Overview/Leaderboard/Slashings tabs, pulling from live `/api/blockchain/analytics/*` endpoints.
- **api-client/index.ts** — 5 new hooks: `useGetNetworkAnalytics`, `useGetValidatorLeaderboard`, `useGetSlashHistory`, `useGetBlockchainEconomics`, `useGetAiIntelHealth`. `useStakeOnPrediction` extended with optional `ah_line` parameter.

### Seed & Infrastructure
- `scripts/seed_tasks.py` — Fixed: all SQLAlchemy mapper models imported upfront. Seeds 31 tasks across 10 categories.
- `app/agents/network_guardian_agent.py` — Fixed naive/aware datetime comparison for DID `created_at` fields.

## v5.0.0 — VIT Cloud Systems (20 VIT Systems)

### Smart Contract Engine (`app/modules/smart_contracts/`)
- `models.py` — `SmartContract`, `ContractCall`, `ContractEvent` ORM tables. Contract has `address` (SHA3-256 hash of name+version+deployer), `abi` (JSON methods list), `state` (JSON key-value), `gas_limit`, `total_calls`, `vit_locked`.
- `executor.py` — Deterministic rule-based execution engine. Gas table per method, 5 built-in contract handlers (VITToken transfer/approve/balance, Staking stake/unstake, Prediction place/claim, Governance propose/vote, Treasury deposit/withdraw/allocate). SHA3-256 event topics.
- `service.py` — `bootstrap_builtin_contracts()` (5 contracts: VITToken, Staking, Prediction, Governance, Treasury), `execute_call()`, `get_contract_by_address/name`.
- `routes.py` — 9 endpoints under `/api/contracts/`: list, bootstrap, by-name, call, events, calls, pause, terminate.

### Treasury System (`app/modules/treasury/`)
- `models.py` — `TreasuryPool`, `TreasuryTransaction`, `TreasuryGrantProposal`. 8 pool types: validator_rewards, ai_infrastructure, ecosystem_grants, reserve, oracle_incentives, prediction_liquidity, bug_bounty, team_vesting.
- `service.py` — `bootstrap_treasury_pools()`, `deposit()`, `allocate()`, `distribute_epoch_reward()`, `submit_grant_proposal()`, `get_overview()`.
- `routes.py` — 9 endpoints under `/api/treasury/`: overview, pools, deposit, allocate, distribute-epoch, grants, grant approve/reject.

### Merit Protocol (`app/modules/merit/`)
- `models.py` — `UserMeritScore` (score, tier, streak, bonus tracking), `MeritEvent` (delta history). 7 tiers: unranked→bronze→silver→gold→platinum→diamond→sovereign with VIT bonus 0–50%.
- `service.py` — `record_event()` (auto-tier promotion/demotion + streak tracking), `apply_daily_decay()`, `get_leaderboard()`, `get_tier_distribution()`.
- `routes.py` — 9 endpoints under `/api/merit/`: tiers, leaderboard, distribution, user score, user history, event, decay.

### AI Verification Layer (`app/modules/ai_verification/`)
- `models.py` — `AIModelAttestation` (model registry with public keys + accuracy stats), `AIOutputAnchor` (per-prediction hash anchoring), `AIDisputeRecord` (challenge/resolution).
- `service.py` — `bootstrap_model_registry()` (5 built-in model attestations: Gemini, Claude, OpenAI GPT-4o, Grok-3, VIT Ensemble), `anchor_output()`, `verify_output()`, `raise_dispute()`.
- `routes.py` — 10 endpoints under `/api/ai-verify/`: stats, models, anchor, verify, disputes.

### Security Layer (`app/modules/security/`)
- `models.py` — `SybilProfile` (composite anomaly score: prediction_velocity, stake_velocity, device_fingerprints, referral_cluster, account_age), `FraudAlert`, `MultiSigOperation` (threshold signatures), `WalletFreeze`, `RateLimitLedger`.
- `service.py` — `evaluate_sybil_risk()` (5-signal composite score → clean/low/medium/high/flagged/banned), `create_fraud_alert()`, `propose_multisig()`, `sign_multisig()`, `freeze_wallet()`, `get_dashboard()`.
- `routes.py` — 12 endpoints under `/api/security/`: dashboard, sybil/evaluate, alerts, multisig propose/sign/execute, freeze/unfreeze, rate-limit-check.

### Sub-Chain Architecture (`app/modules/subchain/`)
- `models.py` — `SubChain` (8 chains: predictions, oracle, governance, bridge, ai_agents, reputation, treasury, identity — each with `chain_id`, `block_time_ms`, `tps_target`), `SubChainBlock`, `CrossChainMessage`.
- `service.py` — `bootstrap_subchains()` (8 sub-chains), `produce_block()`, `send_cross_chain_message()`, `relay_message()`.
- `routes.py` — 10 endpoints under `/api/subchains/`: list, bootstrap, by-type, produce-block, cross-chain messages.

### AI Agent Registry (`app/modules/agent_registry/`)
- `models.py` — `AIAgentRegistration` (on-chain agent record: DID, capability hash, stake, uptime, reputation), `AgentTaskRecord`, `AgentSlashEvent`.
- `service.py` — `bootstrap_agent_registry()` (8 built-in agents: prediction-oracle, sentiment-analyzer, odds-monitor, news-scanner, form-tracker, risk-assessor, settlement-engine, verification-node), `register_agent()`, `record_task()`, `slash_agent()`.
- `routes.py` — 12 endpoints under `/api/agents/registry/`: stats, list, bootstrap, register, get, tasks, slash.

### Storage Verification (`app/modules/storage_verification/`)
- `models.py` — `StorageContentRecord` (CID + Merkle root + blake3 hash), `StorageVerificationLog`, `StorageChallenge` (proof-of-storage challenge/response protocol).
- `service.py` — `register_content()` (CID generation, Merkle root computation, blake3 hashing), `verify_content()`, `issue_challenge()`, `respond_to_challenge()`, `get_stats()`.
- `routes.py` — 10 endpoints under `/api/storage/`: stats, register, verify, challenges.

### Frontend Pages (v5.0.0)
- `frontend/src/pages/smart-contracts.tsx` — Contract browser + method executor (JSON params input, gas display, event log, call history). Route: `/smart-contracts`.
- `frontend/src/pages/treasury.tsx` — Pool balances (utilization bars), deposit form, epoch reward distributor, grant proposal form. Route: `/treasury`.
- `frontend/src/pages/merit.tsx` — Personal score card with tier progress, leaderboard, tier system grid, event history. Route: `/merit`.
- `frontend/src/pages/security.tsx` — Anti-Sybil evaluator (5-signal radar), multi-sig proposer, wallet freeze panel. Route: `/security`.

### Bootstrap (startup)
All 5 bootstrap calls in `main.py` lifespan:
- `bootstrap_builtin_contracts` → 5 contracts (VITToken, Staking, Prediction, Governance, Treasury)
- `bootstrap_treasury_pools` → 8 pools with allocation percentages
- `bootstrap_model_registry` → 5 AI model attestations
- `bootstrap_subchains` → 8 sub-chains (predictions, oracle, governance, bridge, ai_agents, reputation, treasury, identity)
- `bootstrap_agent_registry` → 8 built-in agents

### Schema Setup
`scripts/start_fullstack.sh` imports all 8 new module models so `Base.metadata.create_all` creates their tables on first run.

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
- `scripts/start_fullstack.sh` — startup script (imports all module models for schema creation)
