# VIT Sports Intelligence Network — Technical Audit Report
**Version:** 5.0.0 | **Audited:** 2026-05-06 | **Environment:** Replit Dev (SQLite)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Frontend Pages Audit (57 pages)](#3-frontend-pages-audit)
4. [Backend API Endpoints Audit](#4-backend-api-endpoints-audit)
5. [ML Models & Prediction Engine](#5-ml-models--prediction-engine)
6. [Database Schema Audit](#6-database-schema-audit)
7. [Wallet & Payment System](#7-wallet--payment-system)
8. [Blockchain Economy](#8-blockchain-economy)
9. [Governance DAO](#9-governance-dao)
10. [Autonomous Agents (22 agents)](#10-autonomous-agents)
11. [Notifications & Communications](#11-notifications--communications)
12. [Security Audit](#12-security-audit)
13. [Admin Panel](#13-admin-panel)
14. [Missing Features & Gaps](#14-missing-features--gaps)
15. [Prioritized Recommendations](#15-prioritized-recommendations)
16. [Live Endpoint Test Results](#16-live-endpoint-test-results)

---

## 1. Executive Summary

VIT Sports Intelligence Network is a comprehensive football prediction platform combining a 13-model ML ensemble, multi-AI LLM cascade, VITCoin token economy, blockchain staking, governance DAO, trust engine, developer marketplace, and 22 autonomous AI agents.

**Health snapshot (tested live):**

| Component | Status |
|---|---|
| Backend API | ✅ Running (port 8000) |
| Frontend | ✅ Running (port 5000) |
| Database | ✅ Connected (SQLite dev) |
| ML Models | ✅ 13 loaded (skeleton mode in dev) |
| AI Providers | ✅ Gemini, OpenAI · ❌ Claude, Grok failing |
| Autonomous Agents | ⚠️ 4/6 running, 2 stopped |
| Oracle | ⚠️ 0 submissions, 0 settlements |
| Redis | ⚠️ Not configured (in-memory rate limit fallback) |
| CLV Tracking | ⚠️ 57 matches but 0 CLV entries |

**Overall assessment:** The platform has a very complete feature set with solid security fundamentals. The primary issues are missing external service credentials (Claude, Grok, Football Data API, Redis), absent `.pkl` model weight files for production ML, and several modules that exist architecturally but have never been exercised (oracle, bridge, smart contracts, Pi Network).

---

## 2. System Architecture Overview

### Stack
- **Backend:** Python 3.11 · FastAPI 0.115 · SQLAlchemy 2.0 async · Alembic (18 migrations)
- **Frontend:** React 19 · TypeScript · Vite 6 · TailwindCSS 4 · ShadCN/Radix UI · Wouter routing
- **Database:** SQLite (dev) · PostgreSQL (prod via `VIT_DATABASE_URL`)
- **Auth:** JWT Bearer + TOTP 2FA + token blocklist (`token_blocklist` table, `jti` column)
- **AI Cascade:** Gemini → Claude → OpenAI → Grok → Puter (20s per-provider timeout, 5 providers)
- **Rate Limiting:** Redis sliding window (Lua atomic) + in-memory deque fallback
- **Payments:** Stripe (USD/USDT), Paystack (NGN), Pi Network (stub), VITCoin (on-chain via Base L2)
- **Blockchain:** Base L2 (ERC-20 VITCoin) · Off-chain oracle with 2-of-3 agreement requirement

### File layout (key files)
```
main.py                        2 253 lines, 50+ routers registered
app/db/models.py               Core ORM (Match, Prediction, User, CLVEntry, etc.)
app/modules/                   25 feature modules (wallet, blockchain, governance, trust, …)
app/agents/                    22 autonomous agent files + coordinator
app/api/routes/admin.py        3 000+ line admin mega-router
services/ml_service/models/    model_orchestrator.py (1 300+ lines)
frontend/src/pages/            57 React pages
frontend/src/App.tsx           All routes, lazy-loaded
```

---

## 3. Frontend Pages Audit

### 3.1 Page Inventory (57 pages)

| # | Route | File | Status | Notes |
|---|---|---|---|---|
| 1 | `/dashboard` | `dashboard.tsx` | ✅ Full | AI confidence widget, gamification, recent activity |
| 2 | `/matches` | `matches.tsx` | ✅ Full | Upcoming/live/completed, league filter |
| 3 | `/matches/:id` | `match-detail.tsx` | ✅ Full | Per-match prediction flow |
| 4 | `/predictions` | `predictions.tsx` | ✅ Full | History, results-comparison |
| 5 | `/wallet` | `wallet.tsx` | ✅ Full | 5-currency wallet, deposit/withdraw, conversion, sparkline |
| 6 | `/validators` | `validators.tsx` | ✅ Full | Validator apply/stake/withdraw, admin panel |
| 7 | `/training` | `training.tsx` | ✅ Full | CSV upload, synthetic data, model training |
| 8 | `/analytics` | `analytics.tsx` | ✅ Full | Accuracy, ROI, CLV, model contribution |
| 9 | `/subscription` | `subscription.tsx` | ✅ Full | Plan selection, Stripe checkout, upgrade |
| 10 | `/admin` | `admin.tsx` | ✅ Full | 3 000+ line mega-page, all admin tabs |
| 11 | `/ai-sources` | `ai-sources.tsx` | ✅ Full | Manual AI analysis, consensus feed |
| 12 | `/marketplace` | `marketplace.tsx` | ✅ Full | Model listing, staking, leaderboard |
| 13 | `/trust` | `trust.tsx` | ✅ Full | Trust score, fraud flags, risk events |
| 14 | `/bridge` | `bridge.tsx` | ✅ Full | Cross-chain bridge UI (pools, initiate, history) |
| 15 | `/developer` | `developer.tsx` | ✅ Full | API key management, usage, billing |
| 16 | `/governance` | `governance.tsx` | ✅ Full | Proposals, voting, config, timelock |
| 17 | `/accumulator` | `accumulator.tsx` | ✅ Full | Multi-leg accumulators, bet builder |
| 18 | `/odds` | `odds.tsx` | ✅ Full | Real-time odds, WebSocket feed |
| 19 | `/payment-callback` | `payment-callback.tsx` | ✅ Full | Stripe/Paystack redirect handler |
| 20 | `/leaderboard` | `leaderboard.tsx` | ✅ Full | User + validator leaderboards |
| 21 | `/referral` | `referral.tsx` | ✅ Full | Referral code, bonus tracking |
| 22 | `/settings` | `settings.tsx` | ✅ Full | Profile, 2FA, notifications |
| 23 | `/tasks` | `tasks.tsx` | ✅ Full | Onboarding/reward tasks |
| 24 | `/assistant` | `assistant.tsx` | ✅ Full | AI chat assistant |
| 25 | `/forgot-password` | `forgot-password.tsx` | ✅ Full | Email reset flow |
| 26 | `/reset-password` | `reset-password.tsx` | ✅ Full | Token-based reset |
| 27 | `/verify-email` | `verify-email.tsx` | ✅ Full | Email verification |
| 28 | `/offerwall` | `offerwall.tsx` | ✅ Full | Reward offers (postback) |
| 29 | `/agents` | `agents.tsx` | ✅ Full | Agent status dashboard, manual trigger |
| 30 | `/reports` | `reports.tsx` | ✅ Full | Analytics exports, CSV download |
| 31 | `/oracle` | `oracle.tsx` | ✅ Full | Oracle stats, disputes, submissions |
| 32 | `/network` | `network.tsx` | ✅ Full | Node activity, network snapshots |
| 33 | `/research` | `research.tsx` | ✅ Full | Research/news feed |
| 34 | `/smart-contracts` | `smart-contracts.tsx` | ⚠️ Partial | wagmi/Base L2 required; MetaMask dependency |
| 35 | `/treasury` | `treasury.tsx` | ✅ Full | Treasury balance, fund allocation |
| 36 | `/merit` | `merit.tsx` | ✅ Full | Merit tiers, leaderboard, history |
| 37 | `/security` | `security.tsx` | ✅ Full | Sybil eval, fraud alerts, multisig, freezes |
| 38 | `/roadmap` | `roadmap.tsx` | ✅ Full | Development roadmap viewer |
| 39 | `/identity` | `identity.tsx` | ✅ Full | VIT DID (W3C), verifiable credentials |
| 40 | `/kyc` | `kyc.tsx` | ✅ Full | KYC submission, offline + Smile Identity |
| 41 | `/id-lookup` | `id-lookup.tsx` | ✅ Full | System ID lookup |
| 42 | `/model-performance` | `model-performance.tsx` | ✅ Full | Per-model accuracy, Brier, CLV |
| 43 | `/bankroll` | `bankroll.tsx` | ✅ Full | Kelly bankroll manager |
| 44 | `/about` | `info.tsx` (InfoPage) | ✅ Full | About, terms, privacy, contact (static) |
| 45 | `/terms` | `info.tsx` | ✅ Full | Terms of service |
| 46 | `/privacy` | `info.tsx` | ✅ Full | Privacy policy |
| 47 | `/contact` | `info.tsx` | ✅ Full | Contact info |
| 48 | `/login` | `auth.tsx` | ✅ Full | JWT login + TOTP 2FA |
| 49 | `/register` | `auth.tsx` | ✅ Full | Registration |

### 3.2 Frontend Issues

| Severity | Issue |
|---|---|
| Medium | `/smart-contracts` requires MetaMask/wagmi `useAccount` — crashes without wallet extension installed |
| Medium | No `VITE_CONTRACT_ADDRESS` placeholder warning in UI if env var not set (`web3.tsx` line 84) |
| Low | No gambling age disclaimer displayed on prediction/staking pages |
| Low | Prediction page renders "No model data yet — run a prediction to populate" until first prediction is made (good UX, informational only) |
| Low | `payment-callback.tsx` handles both Paystack and Stripe — no timeout if redirect parameters are malformed |

---

## 4. Backend API Endpoints Audit

### 4.1 Router Inventory (50 routers registered in main.py)

| Module | Prefix | Key Endpoints | Auth |
|---|---|---|---|
| **Auth** | `/auth` | register, login, 2fa/*, refresh, logout, me | Public/JWT |
| **TOTP** | `/auth/totp` | setup, enable, disable, verify | JWT |
| **Prediction** | `/predict` | POST / (predict), GET /{match_id}/insights | JWT/API-key |
| **Matches** | `/matches` | upcoming, explore, live, recent, completed, /{id}, sync | JWT |
| **History** | `/history` | GET /, ticket/build, picks, results-comparison, /{match_id} | JWT |
| **Analytics** | `/analytics` | accuracy, roi, clv, model-contribution, export/csv, leaderboard/* | JWT |
| **Training** | `/training` | upload CSV/insights/models, calibration, data-sources | JWT/Admin |
| **Admin** | `/admin` | 40+ endpoints: api-keys, config, models, fixtures, users, accumulator, stream | Admin |
| **Wallet** | `/wallet` | me, transactions, deposit/*, withdraw, convert, subscribe, exchange-rates | JWT |
| **Wallet Admin** | `/wallet/admin` | withdrawals (list/approve/reject), config, plans, overview | Admin |
| **Webhooks** | `/webhooks` | /paystack, /stripe | HMAC-signed |
| **Blockchain** | `/api/blockchain` | predictions/{id}/stake, stakes/my, validators/*, economy, chain-status | JWT |
| **Oracle** | `/api/oracle` | stats (public), result (oracle-key), admin/disputes, admin/resolve | Mixed |
| **Governance** | `/api/governance` | proposals/*, vote, execute, config, stats | JWT |
| **Marketplace** | `/api/marketplace` | models/*, my-listings, call, rate, stake, leaderboard | JWT |
| **Trust** | `/api/trust` | me, me/flags, me/events, admin/stats, admin/flags, admin/recalculate | JWT |
| **KYC** | `/api/kyc` | submit, status, admin/queue, admin/{id}/approve | JWT |
| **Developer** | `/api/developer` | plans, keys, usage, bill, admin/stats | JWT |
| **Notifications** | `/api/notifications` | GET / (list), mark-read, WS /ws/{user_id} | JWT |
| **Bridge** | `/api/bridge` | pools, initiate, transactions/my, relayer/confirm, admin/* | JWT |
| **Security** | `/api/security` | dashboard, sybil/evaluate, alerts, multisig, freeze | JWT |
| **Governance** | `/api/governance` | proposals, vote, execute, config, stats | JWT |
| **Merit** | `/api/merit` | tiers, leaderboard, distribution, users/{id} | JWT |
| **Network** | `/api/network` | nodes, growth, activity, snapshot | JWT |
| **Smart Contracts** | `/api/smart-contracts` | bootstrap, deploy, /{addr}/call, /{addr}/events | JWT |
| **Identity** | `/api/identity` | me, refresh, admin/list, /{sid} | JWT |
| **DID** | `/api/did` | W3C DID operations | JWT |
| **Referral** | `/api/referral` | code, use, stats | JWT |
| **Leaderboard** | `/api/leaderboard` | users, validators | Public |
| **Agents** | `/api/agents` | status, summary, trigger/{name}, providers, priority | API-key |
| **AI Engine** | `/api/ai-engine` | model management, versions, artifacts | Admin |
| **Tasks** | `/api/tasks` | list, complete, admin/create | JWT |
| **Rewards** | `/api/rewards` | postback, offerwall | HMAC-signed |
| **Odds** | `/api/odds` | league odds, WS /ws | Public |
| **Audit** | `/api/audit` | trail, export | JWT |
| **AI Assistant** | `/api/ai-assistant` | chat, history | JWT |
| **Exports** | `/api/exports` | CSV download | JWT |
| **AI Feed/Sources** | `/api/ai-feed` | consensus, manual analysis, performance update | JWT/Admin |
| **Dashboard** | `/api/dashboard` | stats | JWT |
| **Subscription** | `/api/subscriptions` | plans, my-plan, create-checkout, upgrade | JWT |
| **Config** | `/api/config` | public config, feature flags | Public/Admin |

### 4.2 API Issues

| Severity | Issue |
|---|---|
| High | `POST /predict` requires auth — no public/anonymous demo endpoint for onboarding |
| High | Governance `GET /api/governance/stats` requires auth (returns 401) — reasonable but stats should be public |
| Medium | Oracle result submission only has API-key auth — no mutual TLS or IP whitelist for production oracle nodes |
| Medium | `DELETE /history/clear` and `DELETE /history/clear-all` both exist but are identical routes — potential ambiguity |
| Medium | `/api/agents/trigger/{agent_name}` accepts any API key (not admin-only) — lateral privilege issue |
| Low | No versioning prefix (e.g. `/api/v1/`) — breaking changes will affect all integrations |
| Low | `/api/iot` router registered but not audited — likely stub |
| Low | `GET /admin/stream-predictions` is a streaming SSE endpoint — no documented reconnect behavior |

---

## 5. ML Models & Prediction Engine

### 5.1 Model Inventory

| # | Model Name | Algorithm | Description |
|---|---|---|---|
| 1 | **PoissonGoals** | Inverse Poisson Newton solver | xG-based, full 8×8 score-matrix integration |
| 2 | **EloRating** | Live Elo tracker | Session-scoped Elo store, K=32, default=1500 |
| 3 | **DixonColes** | Dixon-Coles draw correction | rho=−0.13 (empirical), low-score τ correction |
| 4 | **BayesianNet** | Beta-prior conjugate + Dirichlet output | Bayesian update per prediction |
| 5 | **LSTM** | Recency-weighted momentum | Exponential decay over recent form |
| 6 | **Transformer** | Attention-inspired market-prior blend | Learned alpha for prior weighting |
| 7 | **LogisticReg** | Calibrated sigmoid | Market + home-advantage prior |
| 8 | **RandomForest** | Bootstrap-diversity simulation | Multiple Dirichlet draws for diversity |
| 9 | **XGBoost** | Boosted residual correction | Residuals on top of market-implied |
| 10 | **MarketImplied** | Vig-free benchmark | Near-zero noise, vig removal via over-round |
| 11 | **NeuralEnsemble** | Diversity-weighted temperature scaling | Penalty for correlated model outputs |
| 12 | **HybridStack** | Optimal convex combination | Stacked aggregation of all 11 signals |
| 13 | **LLMConsensus** | AI cascade (Gemini/Claude/OpenAI/Grok/Puter) | `multi_ai_dispatcher.py`, 20s timeout each |

### 5.2 Prediction Output Fields

Each prediction returns:
- 1X2 probabilities (home/draw/away) with confidence interval
- Over/Under 2.5 probabilities
- Both Teams To Score (BTTS)
- Asian Handicap line + ladder (±0.25 steps)
- Correct Score matrix (top 10 scores with probabilities)
- Model consensus (agreement pct, side distribution)
- Alternative bets (edge, kelly stake, odds)
- Per-model weights and insights

### 5.3 ML Issues

| Severity | Issue |
|---|---|
| Critical | No `.pkl` model weight files present in `models/` directory — all 12 algorithmic models run as pure-math skeletons; no trained calibrations loaded |
| High | Elo store is **session-scoped** in-memory (`_elo_store` dict) — resets on every server restart, losing learned ratings |
| High | `USE_REAL_ML_MODELS` env var or `ENVIRONMENT=production` required to trigger model loading, but weights don't exist |
| Medium | Calibrators directory exists (`models/calibrators/`) but is populated by training only — empty in fresh install |
| Medium | LLM Consensus (model #13) fails silently to SCIE fallback when all API keys are absent; no visible user warning |
| Medium | `training_summary.json` exists in `models/` but calibrators and weights are absent |
| Low | `_HOME_ADVANTAGE_BIAS = 0.045` is hardcoded — should be league-calibrated |
| Low | Maximum 8 goals modeled in Poisson matrix — truncated for rare high-scoring matches |

---

## 6. Database Schema Audit

### 6.1 Table Inventory (65 tables across all modules)

**Core (app/db/models.py)**

| Table | Purpose | Key Columns |
|---|---|---|
| `matches` | Football fixtures | fingerprint (dedup), source, home/away_goals, odds, status |
| `predictions` | ML prediction results | 20+ prob columns, ah_line, cs_probs, model_consensus, was_correct |
| `clv_entries` | Closing line value tracking | bet_side, entry_odds, closing_odds, clv, profit |
| `edges` | Profitable betting patterns | roi, sample_size, decay_rate, status |
| `model_performances` | Per-model accuracy tracking | accuracy_score, weight, calibration_error, sharpe_ratio |
| `bankroll_states` | Bankroll snapshots | current_balance, peak_balance, max_drawdown |
| `users` | User accounts | username, email, role, tier, totp_secret, is_verified |
| `token_blocklist` | Revoked JWT tokens | jti, user_id, expires_at |

**Wallet (app/modules/wallet/models.py)**

| Table | Purpose |
|---|---|
| `wallets` | 5-currency wallet per user |
| `wallet_transactions` | Ledger: deposit/withdrawal/conversion/earn/stake/fee |
| `withdrawal_requests` | Pending/auto-approved withdrawals with KYC gate |
| `wallet_subscription_plans` | Subscription tiers with price in each currency |
| `wallet_user_subscriptions` | Active subs with auto-renew |
| `vitcoin_price_history` | VITCoin price over time |
| `platform_config` | Key-value config for exchange rates, fee limits |

**Blockchain (app/modules/blockchain/models.py)**

| Table | Purpose |
|---|---|
| `validator_profiles` | Validator staking profiles |
| `validator_predictions` | Per-validator match predictions |
| `consensus_predictions` | Blended AI+validator final predictions |
| `oracle_results` | Oracle submissions (source, result, accepted/disputed) |
| `match_settlements` | Settlement records after oracle confirmation |
| `user_stakes` | Stakes by market (1x2/OU/BTTS/AH/correct_score) |
| `validator_slash_events` | Slash history |
| `oracle_disputes` | Disputed oracle results |
| `blockchain_transactions` | On-chain tx hash tracking |

**Other modules (partial list)**

| Table | Module |
|---|---|
| `gov_proposals`, `gov_votes`, `gov_configs` | Governance |
| `user_trust_scores`, `fraud_flags`, `risk_events` | Trust |
| `kyc_submissions`, `kyc_audit_events` | KYC |
| `marketplace_listings`, `marketplace_usage_logs`, `marketplace_ratings`, `marketplace_stakes` | Marketplace |
| `ai_agent_registrations`, `agent_performance_records` | Agent Registry |
| `model_metadata`, `ai_prediction_audit` | AI Engine |
| `vit_identities`, `verifiable_credentials` | DID |
| `dev_api_keys`, `dev_api_usage_logs`, `dev_api_plans` | Developer |
| `notifications`, `notification_preferences` | Notifications |
| `bridge_pools`, `bridge_transactions` | Bridge |
| `merit_scores`, `merit_events` | Merit |
| `node_activities`, `network_snapshots` | Network |
| `smart_contracts`, `contract_calls`, `contract_events` | Smart Contracts |
| `sybil_profiles`, `fraud_alerts`, `multisig_operations`, `wallet_freezes` | Security |
| `referral_codes`, `referral_uses` | Referral |
| `offer_completions`, `postback_audit_logs` | Rewards |
| `content_hash_registry`, `storage_proofs` | Storage Verification |
| `ai_model_attestations`, `inference_proofs` | AI Verification |

### 6.2 Schema Issues

| Severity | Issue |
|---|---|
| High | `Match.kickoff_time` has no timezone on the column definition (no `timezone=True`) — ambiguous UTC vs local storage |
| High | `Prediction.match_id` is `Integer` FK but `UserStake.match_id` is `String(100)` — type mismatch requiring `int(match_id)` cast in settlement logic (potential ValueError) |
| Medium | `Match.fingerprint` nullable — dedup breaks when fixture_gap_agent patches without computing fingerprint |
| Medium | 18 Alembic migrations but `Base.metadata.create_all` is also used at startup — risk of schema drift in production |
| Medium | No DB-level `UNIQUE` constraint on `token_blocklist.jti` — duplicate revocations possible |
| Low | `predictions` table has 20+ nullable float columns for multi-market probabilities — consider JSON column for extensibility |
| Low | `BankrollState` has no `user_id` FK — single global bankroll state, not per-user |
| Low | No soft-delete pattern on `users` table — `delete /admin/users/{id}` is hard delete |

---

## 7. Wallet & Payment System

### 7.1 Supported Currencies
`NGN` · `USD` · `USDT` · `PI` · `VITCoin`

### 7.2 Payment Processors

| Processor | Currency | Verification |
|---|---|---|
| Paystack | NGN | HMAC-SHA512 `x-paystack-signature` header |
| Stripe | USD/USDT | `stripe-signature` header (Stripe SDK verification) |
| Pi Network | PI | **Stub only** — no live Pi mainnet integration |
| USDT | USDT | Manual/on-chain (no custodial gateway) |

### 7.3 Withdrawal Logic

```
Amount ≤ auto_approve_limit (per role) → auto_approved
Amount > auto_approve_limit            → pending (admin review)
Amount > $10 USD equivalent            → KYC required (any status)
Amount > $10 AND no KYC               → 422 error
```

Withdrawal fee is currently `$0.00` (fee_amount hardcoded to Decimal("0.00")).

### 7.4 Wallet Issues

| Severity | Issue |
|---|---|
| Critical | **Pi Network integration is a stub** — `PI` currency in UI but no live payment gateway |
| High | Withdrawal fee is hardcoded to $0.00 — no fee configuration active despite `PlatformConfig` structure supporting it |
| High | VITCoin price falls back to `$0.001` if `vitcoin_price_history` table is empty — current live value is `$0.10` (from blockchain economy endpoint) but source is unclear |
| High | Exchange rates fallback to hardcoded `usd_ngn=1500, usd_pi=0.5` when `PlatformConfig['exchange_rates']` is absent |
| Medium | Currency conversion uses live price via `_get_rates_to_usd()` but no slippage protection |
| Medium | `wallet_subscription_plans` table seeded from DB; if empty, subscription endpoint returns empty plans list |
| Medium | No idempotency key on deposit initiation — double-tap on `POST /wallet/deposit/initiate` creates duplicate Paystack charges |
| Low | `GET /wallet/statement/export` produces CSV but no date-range filter |

### 7.5 VITCoin Pricing Engine

The `VITCoinPricingEngine` fetches the latest row from `vitcoin_price_history` and multiplies by rates from `PlatformConfig`. No AMM/DEX pricing — fully centralised. Price updates are manual or via agent.

---

## 8. Blockchain Economy

### 8.1 Architecture

```
User Stake (on-chain intent stored in user_stakes)
    ↓
AI Prediction (13-model ensemble → consensus_predictions)
    ↓
Validator Prediction (validator_predictions → blended 60% AI / 40% validator)
    ↓
Oracle Result (oracle_results, 2-of-3 source agreement required)
    ↓
Settlement (settle_match() → distribute rewards)
```

**Fee split on settlement:**
- 40% → validator fund
- 30% → treasury
- 20% → burn (deflationary)
- 10% → AI fund
- 2% platform fee taken first from gross pool

### 8.2 Consensus Engine

```python
final = 0.60 * ai_probs + 0.40 * validator_weighted_avg
# if < 3 validators → fallback to 100% AI probs
```

Validator weights are dynamic: `(trust_score * stake_amount / total_influence)`.

### 8.3 Markets Supported

| Market | Status | Settlement |
|---|---|---|
| 1X2 (Home/Draw/Away) | ✅ Active | Direct oracle result |
| Over/Under 2.5 | ✅ Active | Derived from home_goals + away_goals |
| Both Teams To Score | ✅ Active | Derived from goals |
| Asian Handicap | ✅ Active | AH line-adjusted with push (refund) logic |
| Correct Score | ✅ Active | Exact "hg-ag" string match |

**Market limits:** min 5 VITCoin, max 1 000 VITCoin, 5% commission.

### 8.4 Base L2 Integration

- `GET /api/blockchain/chain-status` — RPC connection check (requires `BASE_RPC_URL`)
- `GET /api/blockchain/chain-balance/{address}` — ERC-20 VIT balance
- `BLOCKCHAIN_ENABLED=false` default — on-chain operations are off unless toggled
- Frontend `smart-contracts.tsx` uses wagmi + `useAccount()` — **requires MetaMask**

### 8.5 Blockchain Issues

| Severity | Issue |
|---|---|
| Critical | `ORACLE_API_KEY` not set — oracle result submission endpoint returns 403 for all external calls |
| Critical | Oracle has 0 submissions and 0 settlements in DB — the settlement engine has never been exercised |
| High | `BASE_RPC_URL` not set — `BLOCKCHAIN_ENABLED=false`, all on-chain checks disabled |
| High | Bridge (`/api/bridge`) has 0 transactions and no real relayer configured |
| High | `smart-contracts.tsx` crashes without MetaMask — no graceful degradation |
| Medium | Elo store is in-process dict — lost on restart, affecting validator trust score calculations |
| Medium | Oracle 2-of-3 sources must be pre-configured via `ORACLE_API_KEY`; no source registration UI |
| Low | `vitcoin_circulating_supply = 10,000,000` is hardcoded in economy endpoint |

---

## 9. Governance DAO

### 9.1 Implementation

| Feature | Status |
|---|---|
| Proposal creation (5–256 char title, 20+ char description) | ✅ |
| Voting (for/against/abstain) with reason | ✅ |
| Voting power system | ✅ |
| Quorum enforcement | ✅ |
| Timelock before execution | ✅ |
| Execute passed proposals | ✅ |
| Protocol parameter config updates | ✅ |
| Admin: close expired proposals, refresh tallies | ✅ |
| Category-based proposals | ✅ |

### 9.2 Governance Issues

| Severity | Issue |
|---|---|
| Medium | `GET /api/governance/stats` requires authentication — should be public for transparency |
| Medium | No on-chain execution of governance decisions — `execute()` only updates `gov_configs` table |
| Medium | Voting power not documented — source of voting power (staked VIT, merit score, role?) is unclear from API |
| Low | `change_payload` field allows arbitrary JSON — no schema validation for what changes are applied |

---

## 10. Autonomous Agents

### 10.1 Agent Registry (22 agents registered in AgentCoordinator)

| # | Agent Name | Purpose | Interval |
|---|---|---|---|
| 1 | `performance-monitor` | Track ML model accuracy | Scheduled |
| 2 | `weight-optimizer` | Adjust model weights based on performance | Scheduled |
| 3 | `retrain-trigger` | Trigger retraining when accuracy drops | Scheduled |
| 4 | `match-scout` | Discover upcoming matches via AI | Scheduled |
| 5 | `news-sentinel` | Monitor football news for insights | Scheduled |
| 6 | `odds-anomaly` | Detect unusual odds movements | Scheduled |
| 7 | `kyc-screener` | Auto-screen KYC submissions | Scheduled |
| 8 | `fraud-review` | Review fraud flags automatically | Scheduled |
| 9 | `withdrawal-gatekeeper` | Auto-approve qualifying withdrawals | Scheduled |
| 10 | `marketplace-audit` | Audit marketplace listings | Scheduled |
| 11 | `model-promoter` | Promote high-performing marketplace models | Scheduled |
| 12 | `analytics-reporter` | Generate periodic analytics reports | Scheduled |
| 13 | `fixture-gap` | Import from TheSportsDB + AI gap-fill | 30 min |
| 14 | `accumulator-publisher` | Publish accumulator bets | Scheduled |
| 15 | `revenue-optimizer` | Optimize platform revenue | Scheduled |
| 16 | `governance-executor` | Execute passed governance proposals | Scheduled |
| 17 | `self-healing` | Detect and recover from errors | Scheduled |
| 18 | `audit-sentinel` | Monitor audit trail for anomalies | Scheduled |
| 19 | `prediction-moderator` | Review prediction quality | Scheduled |
| 20 | `live-match-tracker` | Track live match scores | Scheduled |
| 21 | `oracle-node` | Submit oracle results from external sources | Scheduled |
| 22 | `network-guardian` | Monitor network health | Scheduled |

### 10.2 Agent Runtime Status (from `/health`)

```json
{
  "agents": { "total": 6, "running": 4, "stopped": 2,
              "stopped_names": ["coordinator", "agents"] }
}
```

**Finding:** The health endpoint reports only 6 agents active at startup, not 22. The coordinator boots all 22 agent objects but background `asyncio.create_task()` only spawns 6 tasks. The remaining 16 agents are registered but not actively looping.

### 10.3 Agent Issues

| Severity | Issue |
|---|---|
| High | Only 4 of 22 agents are actively running event loops at startup |
| High | `fixture-gap` agent imports from TheSportsDB (free, no key) — but `FOOTBALL_DATA_API_KEY` missing so the fallback fixture source doesn't trigger live data |
| High | `oracle-node` agent cannot submit results without `ORACLE_API_KEY` being set |
| Medium | `news-sentinel` requires AI API key — falls back to no-op when all LLMs fail |
| Medium | Agent cycles have no circuit breaker — a failing agent retries every interval forever |
| Low | `analytics-reporter` generates reports but no Telegram/email delivery configured |

---

## 11. Notifications & Communications

### 11.1 Channels

| Channel | Implementation | Status |
|---|---|---|
| In-app WebSocket | `NotificationConnectionManager`, `/api/notifications/ws/{user_id}` | ✅ Working |
| Email | SMTP (configurable) or Resend API | ⚠️ Console fallback in dev |
| Telegram DM | Per-user link-code flow + bot token | ⚠️ Bot token not set |
| Telegram Admin | Channel alerts via `TelegramAlert` | ⚠️ Bot token not set |

### 11.2 Notification Types

`prediction_alert` · `match_result` · `wallet_activity` · `validator_reward` · `subscription_expiry` · `validator_status` · `system`

### 11.3 WebSocket Security

The notification WebSocket (SEC-01) validates JWT from `?token=` query param at handshake. Invalid/expired tokens or user_id mismatch → close code 4001. Per-user channel isolation enforced.

Odds WebSocket (`/ws`) via `OddsManager` is unauthenticated (public market data — appropriate).

### 11.4 Notification Issues

| Severity | Issue |
|---|---|
| High | `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` not configured — all Telegram alerts silently dropped |
| High | Email fallback to console in dev means no email confirmations for: registration, password reset, withdrawal approval, KYC result |
| Medium | No Telegram bot commands implemented (`/predict`, `/balance`, `/status`) — only `/start` link-code flow |
| Medium | WebSocket notification manager is in-process dict — multi-process/multi-replica deployments will lose cross-process WS delivery |
| Low | `NotificationPreference` model exists but preference-gating only partially implemented |

---

## 12. Security Audit

### 12.1 Implemented Controls

| Control | Implementation | Status |
|---|---|---|
| JWT authentication | `python-jose`, 30-min access + refresh tokens | ✅ |
| TOTP 2FA | `pyotp`, `/auth/totp/setup` → `/auth/2fa/enable` | ✅ |
| Token blocklist | `token_blocklist` table, `jti` check on every request | ✅ |
| Rate limiting | Redis sliding window + in-memory fallback (3 tiers) | ✅ |
| CORS | Wildcard origins never paired with `allow_credentials=True` (SEC-02) | ✅ |
| WebSocket JWT | Close code 4001 for invalid/expired/mismatched tokens (SEC-01) | ✅ |
| Timing-safe comparison | `hmac.compare_digest` for API key (SEC-08) | ✅ |
| Rate limit eviction | Idle buckets evicted after 120s (SEC-07) | ✅ |
| KYC gate | Withdrawals >$10 USD equivalent require KYC | ✅ |
| Paystack webhook | HMAC-SHA512 signature verified | ✅ |
| Stripe webhook | `stripe-signature` verified via Stripe SDK | ✅ |
| Oracle key | `X-Oracle-Key` header with constant-time compare | ✅ |
| Admin routes | `get_current_admin` dependency on all admin endpoints | ✅ |
| SQL injection | SQLAlchemy ORM parameterised queries throughout | ✅ |
| Password hashing | bcrypt via `passlib` (not audited directly but standard FastAPI pattern) | ✅ |
| Multisig operations | Multisig model in security module | ✅ |
| Wallet freeze | Admin wallet freeze with audit trail | ✅ |
| Sybil detection | `sybil_profiles` table + `/api/security/sybil/evaluate` | ✅ |

### 12.2 Rate Limits

| Tier | General | Predict endpoint |
|---|---|---|
| Anonymous (IP-based) | 60 req/min | 20 req/min |
| API-key | 180 req/min | 80 req/min |
| JWT user | 300 req/min | 120 req/min |

### 12.3 Security Issues

| Severity | Issue |
|---|---|
| High | `JWT_SECRET_KEY` — if not set in environment, app falls back to `SECRET_KEY`; if neither set, JWT is unsigned (no forced-non-empty check at startup) |
| High | `ADMIN_PASSWORD` blank in `.env.example` — must be set before first deploy (documented but easy to miss) |
| High | Rate limiter falls back to in-memory (single-process) when Redis is unavailable — in multi-replica deployments, limits are per-replica, not global |
| Medium | Oracle API key (`ORACLE_API_KEY`) not set in current deployment — oracle endpoint is effectively open to anyone who guesses the empty-string key |
| Medium | `/api/agents/trigger/{agent_name}` requires any API key but not admin — a user with a dev API key can trigger any agent |
| Medium | Prediction endpoint token is extracted from JWT by base64 decode in rate limiter middleware (no signature verification) — rate limit identity can be spoofed by crafting a fake JWT payload without a valid signature |
| Medium | No CSP (Content-Security-Policy) headers configured |
| Medium | No `X-Frame-Options` / `X-Content-Type-Options` headers |
| Low | `token_blocklist` table has no DB-level UNIQUE constraint on `jti` |
| Low | `TOTP_ISSUER` not verified — any TOTP secret stored as plaintext in `users.totp_secret` |
| Low | Withdrawal destination (bank account number, address) stored in plaintext in `withdrawal_requests` |

---

## 13. Admin Panel

### 13.1 Admin Feature Coverage

The admin panel (`/admin` page + `/admin` backend router) is comprehensive:

| Section | Features |
|---|---|
| System Health | CPU/memory/disk, API/DB/Redis/Football API status |
| Models | Status, version history, reload, set-active, train |
| Calibration | Fit, reload, status |
| Data Sources | Status, test connection |
| Fixtures | Manual create, backfill FT results, fetch from API, live, by-date, by-id |
| Users | List, create, edit, delete, view profile |
| Accumulator | Candidates, generate, send, place-bet |
| Leagues | List, manage weights |
| Markets | List, configure commission/limits |
| Currencies | Exchange rates, deposit/withdrawal limits |
| Subscription Plans | Create, edit, enable/disable |
| API Keys | List, update, delete (external API keys for Football data, odds, etc.) |
| Config | Runtime config toggles (WebSocket, rate limit, etc.) |
| AI Feed | Consensus, manual insights upload |
| Audit Log | Full audit trail with actor/action/status |
| Settle Results | Manual match settlement trigger |
| CLV Backfill | Backfill missing closing-line values |
| Data Quality | Missing fingerprint, missing odds diagnostic |
| Stream | SSE stream of live predictions |
| Tasks | Create onboarding tasks |

### 13.2 Admin Issues

| Severity | Issue |
|---|---|
| Medium | Admin page (`admin.tsx`) is one file with 3 000+ lines — rendering performance may degrade on lower-end devices |
| Medium | `POST /admin/matches/backfill-ft-results` updates `was_correct` on predictions but doesn't trigger CLV backfill |
| Low | `POST /admin/settle-results` and oracle `POST /api/admin/oracle/resolve/{match_id}` are two separate settlement paths — potential double-settlement |
| Low | No admin action confirmation dialogs for destructive operations (delete user, slash validator) |

---

## 14. Missing Features & Gaps

### P0 — Critical (blocking production launch)

| # | Gap | Impact |
|---|---|---|
| 1 | **No trained ML model weights** — `models/` has no `.pkl` files | All predictions run on pure math, not trained on data |
| 2 | **No live fixture data** — `FOOTBALL_DATA_API_KEY` empty, TheSportsDB fallback only | Predictions on stale/synthetic fixtures |
| 3 | **Oracle completely inactive** — `ORACLE_API_KEY` missing, 0 submissions | Staking stakes can never settle |
| 4 | **Claude and Grok failing** — `ANTHROPIC_API_KEY` and `XAI_API_KEY` not set | LLM consensus degrades to 2 of 5 providers |

### P1 — High (needed for full functionality)

| # | Gap | Impact |
|---|---|---|
| 5 | **Redis not configured** — rate limiting is per-process, not distributed | In production multi-replica deployments, rate limits can be circumvented |
| 6 | **No email configured** — SMTP/Resend keys missing | Registration confirmations, password resets, withdrawal emails not delivered |
| 7 | **Telegram not configured** — `TELEGRAM_BOT_TOKEN` missing | No admin alerts, no user DM notifications |
| 8 | **Pi Network is a stub** — no mainnet payment gateway | PI currency listed but not usable for real deposits |
| 9 | **16 of 22 agents not running** — only 4 event loops active | Gap-fill, oracle-node, live-match-tracker, governance-executor, etc. are dormant |
| 10 | **VITCoin price not seeded** — empty `vitcoin_price_history` → fallback $0.001 | Wallet conversion uses incorrect price |

### P2 — Medium (important UX gaps)

| # | Gap | Impact |
|---|---|---|
| 11 | **CLV tracking not active** — 0 CLV entries despite 57 matches | Analytics ROI and CLV pages show no data |
| 12 | **No gambling age disclaimer** on prediction/staking pages | Regulatory risk |
| 13 | **No public prediction demo** — predict endpoint requires auth | No onboarding friction reduction |
| 14 | **Smart contracts page crashes** without MetaMask | Feature gate needed |
| 15 | **Base L2 not connected** — `BASE_RPC_URL` missing | Chain balance/status endpoints return disconnected |
| 16 | **Bridge has no relayer** — no live cross-chain relay configured | Bridge UI exists but cannot process transfers |
| 17 | **Withdrawal fee = $0.00** — no fee configured | Revenue loss on all withdrawals |

### P3 — Low (polish / production hardening)

| # | Gap | Impact |
|---|---|---|
| 18 | No API versioning prefix (`/api/v1/`) | Breaking changes break all integrations |
| 19 | No database-level unique constraint on `token_blocklist.jti` | Duplicate revocations possible |
| 20 | `Match.kickoff_time` stores naive datetimes — no timezone column flag | Timezone-ambiguous fixture times |
| 21 | No Telegram bot commands (`/predict`, `/balance`, `/status`) | Missed engagement channel |
| 22 | Admin page is one 3 000+ line file | Performance issues on low-end devices |
| 23 | `ORACLE_API_KEY` defaults to empty string — oracle endpoint reachable without any key | Security gap |
| 24 | No security headers (CSP, X-Frame-Options, X-Content-Type-Options) | Browser security hygiene |
| 25 | Elo store resets on restart | Validator predictions lose historical calibration |

---

## 15. Prioritized Recommendations

### Immediate (Week 1 — Pre-launch blockers)

```
1. Set ORACLE_API_KEY in Replit Secrets to a strong random value
2. Set JWT_SECRET_KEY and ADMIN_PASSWORD in Replit Secrets
3. Add ANTHROPIC_API_KEY (Claude) and XAI_API_KEY (Grok) to restore full AI cascade
4. Configure RESEND_API_KEY or SMTP credentials for email delivery
5. Configure TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID for admin alerts
6. Run initial ML training cycle:
   a. Upload historical fixture CSV via /admin → Training
   b. Trigger model training (POST /admin/models/train)
   c. Reload calibrators (POST /admin/calibration/reload)
7. Seed VITCoin price history via admin or pricing scheduler
8. Set FOOTBALL_DATA_API_KEY or verify TheSportsDB is returning fixtures
```

### Short Term (Week 2–3 — Core functionality)

```
9.  Configure REDIS_URL for distributed rate limiting
10. Fix agent coordinator to spawn all 22 agent event loops (not just 6)
11. Register at least 2 oracle sources and submit first test result
12. Configure auto_approve_limit for each user role via wallet admin config
13. Set withdrawal fees in PlatformConfig
14. Seed subscription plans into wallet_subscription_plans table
15. Add MetaMask detection guard on /smart-contracts page
16. Add gambling / informational-only disclaimer to prediction pages
```

### Medium Term (Month 1 — Quality and production hardening)

```
17. Add /api/v1/ versioning prefix to all public API endpoints
18. Add security headers middleware: CSP, X-Frame-Options, X-Content-Type-Options
19. Add unique constraint on token_blocklist.jti in Alembic migration
20. Persist Elo store to DB or Redis to survive restarts
21. Add Match.kickoff_time timezone=True in next Alembic migration
22. Implement Telegram bot commands: /predict, /balance, /status, /stake
23. Split admin.tsx into domain-specific sub-pages for performance
24. Add idempotency key support on deposit initiation
25. Implement Pi Network mainnet gateway or remove PI currency until ready
```

### Long Term (Quarter 1 — Scaling and ecosystem)

```
26. Deploy real VITCoin ERC-20 on Base mainnet; set BASE_RPC_URL + VIT_CONTRACT_ADDRESS
27. Configure bridge relayer for cross-chain transfers
28. Add multi-replica WebSocket notification delivery (Redis pub/sub or equivalent)
29. Add API versioning with deprecation notices
30. Commission external security penetration test covering auth, wallet, and oracle flows
31. Implement per-league Elo calibration (replace global HOME_ADVANTAGE_BIAS = 0.045)
32. Add circuit breaker to agent loop (max retry before cooldown)
33. Load test with k6/locust to verify Redis rate limiting under horizontal scale
```

---

## 16. Live Endpoint Test Results

Tests performed on running dev instance (2026-05-06):

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/health` | GET | ✅ 200 | `models_loaded:13`, `db_connected:true` |
| `/matches/markets/enabled` | GET | ✅ 200 | 3 markets returned (1x2, OU2.5, BTTS) |
| `/api/blockchain/economy` | GET | ✅ 200 | `active_validators:1`, `vitcoin_price_usd:0.1` |
| `/api/oracle/stats` | GET | ✅ 200 | `total_submissions:0` — oracle never used |
| `/predict` | POST | ✅ 401 | Auth required (expected) |
| `/admin/stats` | GET | ✅ 401 | Auth required (expected) |
| `/api/governance/stats` | GET | ⚠️ 401 | Should be public |
| `/api/governance/stats` | GET (no prefix) | ❌ 404 | Router prefix mismatch |
| `/api/blockchain/chain-status` | GET | ⚠️ N/A | Depends on `BASE_RPC_URL` |

**Database state:**
- Matches: 57 (mix of synthetic and TheSportsDB)
- Settled predictions: 24
- CLV entries: 0
- Oracle submissions: 0
- Oracle settlements: 0
- Active validators: 1

---

*Audit conducted by automated code exploration and live API testing. All findings are based on source code and runtime state at time of audit.*
