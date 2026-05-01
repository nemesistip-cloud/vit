# VIT Sports Intelligence Network — v4.7.5

## Overview
The VIT Sports Intelligence Network is an institutional-grade football prediction platform. It leverages a 12-model AI ensemble for predictions, integrates a VITCoin wallet economy, supports blockchain-verified staking, features a model marketplace, and includes a governance DAO. The platform offers multi-tier subscriptions (Free, Pro, Elite) and aims to provide advanced sports analytics and prediction capabilities.

## Changelog — Security & Feature Upgrade (2026-05-01, sessions 2 & 3)

### Security Hardening (Phase 1 & 2)
- **SEC-01**: WebSocket JWT auth at handshake — backend rejects with 4001, frontend passes `?token=<jwt>`
- **SEC-02**: CORS wildcard fix — never pairs `allow_origins=*` with `allow_credentials=True`
- **SEC-03**: Email/reset tokens moved to DB (`email_tokens` table, hashed, with expiry)
- **SEC-04**: JWT jti revocation blocklist — logout adds jti to `token_blocklist`; middleware checks blocklist on every request
- **SEC-06**: HSTS header only set when `ENVIRONMENT=production`
- **SEC-07**: Rate limiter LRU eviction prevents unbounded memory growth
- **SEC-10**: DB-backed per-account login brute-force — 5 failures triggers 15-min `locked_until` column on User (survives restarts); `Retry-After` header returned on 429
- **ENG-01**: requirements.txt deduplicated from 421 → 38 lines

### Feature Completion (Phase 3)
- **ENG-11**: Frontend notification bell passes `?token=<jwt>` in WebSocket URL
- **ENG-12**: Referral commission distribution — `process_deposit_commission()` and `process_subscription_commission()` credit referrer 10% VITCoin on each confirmed deposit or subscription; wired into `/deposit/verify` and `/wallet/subscribe`
- **ENG-06 (T009)**: Training jobs already DB-backed via `ModuleTrainingJob` — confirmed working
- **Fixture import**: 179 fixtures from CSV imported into DB (`scripts/import_fixtures.py`); total 447 fixtures in DB
- **2FA UI (T013)**: Settings page already had full 2FA flow; added missing backend endpoints (`GET /auth/2fa/status`, `POST /auth/2fa/setup`, `POST /auth/2fa/enable`, `POST /auth/2fa/disable`) with QR code data-URI generation; `totp_secret`/`totp_enabled` columns added to User model via Alembic migration

### Payments & Revenue (Phase 4)
- **T014**: Stripe subscription checkout (`POST /subscription/create-checkout`) and webhook (`POST /webhooks/stripe`) already implemented and mounted — confirmed working
- **T015**: Paystack NGN deposits (`POST /wallet/deposit/initiate` + `/deposit/verify`) already implemented — confirmed working
- **T016 (Offerwall)**: Created `app/modules/rewards/routes.py` with `/api/rewards/offers`, `/api/rewards/history`, `/api/rewards/summary` endpoints; created `frontend/src/pages/offerwall.tsx` dashboard with offer cards, earn history table, and summary stats; added "Offers" nav link to sidebar under Earn group; routed at `/earn`

### Database Migrations
- `b1a2c3d4e5f6_sec04_sec10_hardening`: adds `failed_login_count`, `locked_until`, `email_tokens`, `token_blocklist` tables
- `c2d3e4f5a6b7_add_totp_columns`: adds `totp_secret`, `totp_enabled` to users table

## Changelog — v4.7.5 (2026-05-01)
- **Version bump**: 4.6.0 → 4.7.5 (app/config.py single source of truth)
- **Session expiry toast**: apiClient.ts now shows a visible toast + clears both tokens on 401 refresh failure
- **Error boundary telemetry**: `componentDidCatch` posts JS crashes to `POST /admin/client-error` (fire-and-forget)
- **Backend — client-error endpoint**: `POST /admin/client-error` logs frontend crashes server-side
- **Backend — fixture health**: `GET /admin/fixture-health` scans matches for unsettled past fixtures, missing odds, duplicate fingerprints, and incomplete dedup keys
- **Admin UI — Fixture Ecosystem Health card**: live scan card in SystemTab with %-health score, per-category drill-down, and sample rows
- **Predictions UX**: replaced "Coming soon" pill with informative "Model coverage expanding" notice with amber indicator dot
- **Fixed /admin/matches/manual**: source="manual_upload", status="upcoming", fingerprint dedup before request_hash
- **Fixed /admin/upload/csv CRITICAL**: endpoint now persists matches to DB (was returning predictions only); returns match_id per row
- **Expanded COMPETITIONS**: 10 → 22 leagues (Turkish, Brazilian, MLS, Liga MX, UCL, UEL, UECL, League One/Two, Segunda, Serie B, Bundesliga 2)
- **Fixed AIInsightComparison.tsx**: endpoint corrected from /predict/${id}/insights → /ai/multi-insights/${id}; risk_level badges, insight_tags, value_assessment, recommendation, cache indicator, resolveInsight() helper
- **Enhanced Gemini prompt**: 4-role analyst system (Tactical, Value, Risk, Model Interpreter); recommendation field; implied probability context; system_instruction parameter
- **insight_store TTL**: cache entries older than 6 hours are treated as stale; dispatcher persists freshly generated insights to disk with generated_at timestamp
- **GET /training/insight-report**: per-model accuracy breakdown, weight distribution, health status heuristics, actionable recommendations
- **Admin ModelsTab — TrainingInsightCard**: ensemble summary strip, model breakdown table, per-model accuracy/weight/status, recommendations panel
- **Admin SystemTab — CSVUploadCard**: file picker, upload button, result table with match_id links and per-row status badges, format hint

## User Preferences
I prefer iterative development with a focus on clear, modular code. Please use functional programming paradigms where appropriate and provide detailed explanations for significant architectural decisions or complex algorithms. Ask before making major changes to the project structure or core functionalities.

## System Architecture
The platform is built with a microservices-oriented approach.
- **Backend**: Python 3.11 with FastAPI, utilizing SQLAlchemy for asynchronous ORM operations and Alembic for database migrations. Uvicorn serves the application on port 5000.
- **Database**: SQLite is used for development, with PostgreSQL as the production database, configured via `VIT_DATABASE_URL`.
- **Frontend**: Developed using React 18, TypeScript, Vite, TailwindCSS, and ShadCN UI. The build output is located in `frontend/dist/` and served by the FastAPI application.
- **AI Orchestrator**: Manages a 12-model AI ensemble that uses trained `.pkl` weights and per-model calibrators.
- **Authentication**: Implements JWT and TOTP for secure authentication, enforcing 2FA.
- **Wallet & Blockchain**: Includes a VITCoin wallet system and supports blockchain-based staking, though the blockchain features can be optionally disabled.
- **Marketplace**: Features a UI for a model marketplace.
- **Developer API**: Provides key management for external integrations.
- **Notifications**: Uses WebSockets for real-time notifications with exponential reconnect logic.
- **UI/UX**: Frontend components are built with ShadCN UI, utilizing TailwindCSS for styling, ensuring a modern and responsive design.
- **AI Model Calibration**: Employs isotonic calibration for per-model probability adjustments, using fitted calibrators from historical data.
- **Model Weight Adjustment**: A CLV-blended weight adjuster is used for AI models, combining log-loss and Closing Line Value (CLV) signals to dynamically update model contributions.
- **AI Assistant**: A conversational AI assistant is integrated into match-detail pages, providing context-aware answers based on pre-loaded prediction data.
- **Module Map**:
    - AI Orchestrator: Running with trained models and calibrators.
    - Auth (JWT + TOTP): Complete with 2FA.
    - Wallet + VITCoin: Core functionality complete.
    - Predictions: Working.
    - Blockchain / Staking: Disabled by flag.
    - Cross-Chain Bridge: Simulation only.
    - Governance DAO: Partial implementation.
    - Marketplace: UI live.
    - Developer API: Key management done.
    - Notifications + WS: WS toasts + exponential reconnect.
    - Referral: No reward distribution.
    - Trust Engine: Partial.
    - Training Pipeline: Colab-only.

## External Dependencies
- **Football Data API**: Used for fetching football match data.
- **Gemini API**: Integrated for the conversational AI Assistant.
- **Stripe**: Used for subscription management and payments (webhook activated).
- **Paystack**: Enabled for NGN deposits.
- **SMTP Host**: Required for email functionalities (currently stubbed to console).
- **Redis**: Planned for advanced rate limiting (currently in-memory).
- **Anthropic API**: Planned for Claude insights (currently disabled).