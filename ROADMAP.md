# VIT Sports Intelligence Network — Implementation Roadmap

> Generated: April 22, 2026 | Version: 4.0.0

---

## Project Overview

**VIT_OS** is an institutional-grade sports prediction platform built on FastAPI (Python) + React (TypeScript).  
It features a 12-model AI ensemble, a VITCoin wallet economy, blockchain-verified staking, an AI model marketplace, governance DAO, and multi-tier subscriptions.

**Stack:** Python 3.11 · FastAPI · SQLAlchemy (async) · SQLite/PostgreSQL · React 18 · Vite · TailwindCSS · ShadCN UI

**Current Status:** App is live and serving. Core prediction, auth, wallet, and admin flows are functional. Several advanced modules are flagged, stubbed, or partially wired.

---

## Incomplete Features Audit

### 🔴 Critical (Blocking Revenue / Core UX)

| # | Feature | Location | Issue |
|---|---------|----------|-------|
| 1 | **Real ML Models** | `app/modules/ai/` | ✅ **Partial fix (Apr 2026)**: All 12 models in `services/ml_service/models/model_orchestrator.py` now have per-model `train()` overrides that fit genuine learned state (logistic home-advantage prior, RF Dirichlet concentration, XGBoost boost target, Poisson team strengths, Elo replay, Dixon-Coles ρ grid-search, LSTM momentum coef, Transformer attention weights, Ensemble entropy-scaled σ, Bayes Dirichlet prior, Hybrid stack weights). Training now produces **distinct real metrics per model** (verified: Bayes & Elo ~70% acc / 0.174 Brier; Hybrid 66%; XGB 21%; vs. previous hard-coded 0.54). For full production accuracy, still requires real-data Colab training run + `.pkl` upload via Admin panel with `USE_REAL_ML_MODELS=true`. |
| 2 | **Stripe Subscription Payments** | `app/api/routes/subscription.py` | `STRIPE_SECRET_KEY` missing from env. Upgrade checkout sessions return 503. Pro ($49/mo) and Elite ($199/mo) plans cannot be purchased. |
| 3 | **Paystack NGN Payments** | `app/modules/wallet/routes.py` | `PAYSTACK_SECRET_KEY` missing. NGN wallet deposits silently fail. |
| 4 | **Email Sending** | `app/auth/verification.py` | `_send_email()` is a stub — logs to console only. Email verification and password-reset links are never actually delivered unless `SMTP_HOST` is set. |
| 5 | **WebSocket Frontend Connection** | `app/modules/notifications/websocket.py` | Server-side WebSocket manager is complete, but the frontend notification bell does not connect to `/ws/{user_id}`. Real-time push never arrives in the browser. |

---

### 🟠 High Priority (Core Platform Features)

| # | Feature | Location | Issue |
|---|---------|----------|-------|
| 6 | **KYC Verification** | `app/modules/wallet/routes.py` | Submit sets status to "pending" but there is no document upload, no automated ID-verification provider (Onfido/Jumio/Smile Identity), and no admin review UI to approve/reject. Withdrawal limits cannot be lifted. |
| 7 | **Redis / Celery Task Queue** | `app/worker.py`, `app/tasks/` | No Redis URL configured. Rate limiting falls back to in-memory (lost on restart). Celery background jobs (model retraining, scheduled odds refresh, CLV recalculation) do not queue. |
| 8 | **Claude / Grok AI Insights** | `app/services/claude_insights.py`, `grok_insights.py` | `ANTHROPIC_API_KEY` and `XAI_API_KEY` missing. Multi-AI dispatcher falls back to Gemini only. AI insight comparison panel shows one provider. |
| 9 | **Blockchain Settlement** | `app/modules/blockchain/` | `BLOCKCHAIN_ENABLED=false`. Full validator network, on-chain staking, consensus engine, and settlement logic is coded but behind a disabled flag. No real chain connection exists. |
| 10 | **TOTP / 2FA** | `app/auth/totp.py` | Backend TOTP endpoints and QR code generation are complete. Frontend settings page has no 2FA setup flow wired up. |

---

### 🟡 Medium Priority (Platform Completeness)

| # | Feature | Location | Issue |
|---|---------|----------|-------|
| 11 | **Cross-Chain Bridge** | `app/modules/bridge/` | Module routes and models are complete but there is no real blockchain/EVM connection. All bridge transactions are internal VITCoin simulation only. |
| 12 | **Referral Rewards Distribution** | `app/modules/referral/` | Referral code generation and usage tracking works. No commission/reward distribution tied to real payments or subscription upgrades. |
| 13 | **Governance DAO Execution** | `app/modules/governance/` | Proposals and voting are coded. No token-gated quorum enforcement, no on-chain execution of approved proposals, no time-lock mechanism. |
| 14 | **Trust & Reputation Engine** | `app/modules/trust/` | Score calculation and flagging exist. Automated trust-score actions (e.g., auto-suspend low-trust accounts), appeals workflow, and trust badge display in the UI are incomplete. |
| 15 | **Training Pipeline (In-App)** | `app/api/routes/training.py` | ✅ **Partial fix (Apr 2026)**: In-app trigger now actually trains all 12 models with differentiated learned state and reports real per-model metrics (accuracy, log-loss, Brier, over/under) computed by `_evaluate_model_on_history()`. Remaining gap: training status is still stored in-memory only — wiped on restart. No persistent job tracking yet. The referenced `colab/train_real_match_models.py` script does not exist; use `scripts/train_models.py` for offline training. |
| 16 | **CSV Upload (Elite Tier)** | `app/api/routes/admin.py` | Backend CSV upload endpoint exists. No frontend UI for Elite users to upload custom match data CSVs. |
| 17 | **Developer API Marketplace** | `app/modules/developer/` | API key management works. No live API documentation portal, no per-key usage metering/billing, no webhook delivery receipts. |

---

### 🟢 Low Priority / Polish

| # | Feature | Location | Issue |
|---|---------|----------|-------|
| 18 | **Pi Network Wallet Deposits** | `app/modules/wallet/routes.py` | `method: "pi"` referenced in schema but no Pi Network SDK integration implemented. |
| 19 | **Telegram Per-User Alerts** | `app/services/alerts.py` | Platform-level Telegram alerts work. Per-user Telegram linking (connect own chat ID) has no frontend settings flow. |
| 20 | **Prediction Accumulators** | `frontend/src/pages/accumulator.tsx` | Frontend page exists. Some market types show "Coming soon" notice. Backend accumulator odds calculation may not cover all market combinations. |
| 21 | **Font CDN / CSP** | `frontend/dist/index.html` | Google Fonts stylesheet blocked by Content Security Policy. Inter font falls back to system font. |
| 22 | **PostgreSQL Production DB** | `alembic/` | App runs on SQLite by default. Alembic migrations are written for Postgres. For production scale, `VIT_DATABASE_URL` must point to a Postgres instance and `alembic upgrade head` must be run. |

---

## Integration Roadmap

### Phase 1 — Revenue Activation (Week 1–2)

**Goal: Make the platform capable of processing real payments and delivering real predictions.**

1. **Add Stripe secret key** → set `STRIPE_SECRET_KEY=sk_live_...` in Replit Secrets  
   Enables: Pro/Elite subscription checkout, Stripe webhooks for subscription lifecycle
2. **Add Paystack secret key** → set `PAYSTACK_SECRET_KEY=sk_live_...`  
   Enables: NGN wallet deposits for African users
3. **Configure SMTP** → set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`  
   (or swap `_send_email()` for SendGrid/Resend SDK)  
   Enables: email verification, password reset, transactional alerts
4. **Train real ML models** → run `colab/train_real_match_models.py` on Google Colab with historical match CSV, upload `vit_models.zip` via Admin > Model Weights Upload → set `USE_REAL_ML_MODELS=true`

---

### Phase 2 — Real-Time & Reliability (Week 3–4)

**Goal: Eliminate in-memory state and enable real-time features.**

5. **Provision Redis** → set `REDIS_URL=redis://...`  
   Enables: persistent rate limiting, Celery task queue, result caching
6. **Wire WebSocket to frontend** → connect notification bell to `wss://{domain}/notifications/ws/{user_id}` using a JWT token handshake  
   Enables: real-time prediction alerts, score updates, wallet events
7. **Add Claude API key** → set `ANTHROPIC_API_KEY=sk-ant-...`  
   Enables: multi-AI comparison panel (Claude vs Gemini), richer match insight narratives
8. **Migrate to PostgreSQL** → provision Replit PostgreSQL DB, set `VIT_DATABASE_URL`, run `alembic upgrade head`  
   Enables: concurrent users, production-grade query performance

---

### Phase 3 — KYC & Compliance (Week 5–6)

**Goal: Enable compliant withdrawals and trust-gated features.**

9. **Integrate KYC provider** (Smile Identity for Africa, or Onfido globally)  
   → Add KYC webhook endpoint → admin approval UI in `/admin` panel  
   Enables: withdrawal limits lifted for verified users, validator eligibility
10. **Implement 2FA frontend flow** → wire `/settings` page to `/auth/totp/setup` and `/auth/totp/verify`  
    Enables: account security for high-value users

---

### Phase 4 — Blockchain & Economy (Week 7–10)

**Goal: Activate on-chain VITCoin economy.**

11. **Choose and connect a chain** (Polygon, BSC, or Solana recommended for low fees)  
    → Implement VITCoin ERC-20 or SPL token contract  
    → Set `BLOCKCHAIN_ENABLED=true` and `ORACLE_API_KEY`  
    Enables: real staking, validator rewards, on-chain settlement
12. **Build cross-chain bridge** → connect bridge module to a bridge SDK (LayerZero or Wormhole)  
    Enables: USDT/ETH ↔ VITCoin swaps
13. **Governance quorum & execution** → add minimum voting power check, time-lock contract, automated parameter changes on proposal pass

---

### Phase 5 — Growth & Ecosystem (Week 11–14)

**Goal: Expand the platform's reach and developer ecosystem.**

14. **Referral reward distribution** → tie referral use events to payment webhooks → auto-credit referrer wallet on first paid subscription
15. **Developer API portal** → add per-key usage metering (count requests, enforce plan limits), generate API docs from OpenAPI spec
16. **In-app training trigger** → persist training job status to DB → allow Elite users to trigger model re-training on new match data without Colab
17. **Telegram per-user linking** → add `/settings/notifications` page → let users link their Telegram chat ID for personalized alerts
18. **Pi Network integration** → integrate Pi Network SDK for Pi wallet deposits

---

## Environment Variables Needed

| Variable | Purpose | Priority |
|----------|---------|----------|
| `STRIPE_SECRET_KEY` | Subscription payments | 🔴 Critical |
| `STRIPE_WEBHOOK_SECRET` | Stripe event validation | 🔴 Critical |
| `PAYSTACK_SECRET_KEY` | NGN deposits | 🔴 Critical |
| `PAYSTACK_WEBHOOK_SECRET` | Paystack event validation | 🔴 Critical |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | Email delivery | 🔴 Critical |
| `ANTHROPIC_API_KEY` | Claude AI insights | 🟠 High |
| `XAI_API_KEY` | Grok AI insights | 🟡 Medium |
| `REDIS_URL` | Task queue + caching | 🟠 High |
| `ORACLE_API_KEY` | Blockchain oracle | 🟡 Medium |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Platform alerts (already partial) | 🟡 Medium |

---

## What's Working Now ✅

- Landing page with live stats ticker
- User registration, login, JWT auth, email verification (console-mode)
- 12-model AI ensemble (synthetic data mode)
- Match predictions with confidence scores
- Prediction history and CLV tracking
- VITCoin wallet (create, view balance, internal transfers)
- Admin panel (model management, fixture management, user management, feature flags)
- Subscription plan display (Free / Pro / Elite)
- Leaderboard and analytics dashboards
- Telegram platform startup alert
- Odds comparison module
- Accumulator builder (basic markets)
- Governance proposal/voting UI
- Marketplace listing UI
- Developer API key management UI
- Trust scoring and flagging system
- Background ETL pipeline (match data refresh)
- Rate limiting (in-memory)
- RBAC (free / analyst / pro / validator / admin / super_admin)
