# VIT Sports Intelligence Network

A 13-model AI ensemble football prediction platform with a VITCoin wallet economy, blockchain staking, model marketplace, governance DAO, and 22 autonomous AI agents.

## Run & Operate

```bash
bash scripts/start_fullstack.sh   # starts both frontend (5000) and backend (8000)
pip install -r requirements.txt   # install backend deps
cd frontend && npm install        # install frontend deps
cd frontend && npm run build      # production frontend build
python3 -c "from main import app; print('OK')"  # test backend import
```

**Required secrets** (set in Replit Secrets):
- `JWT_SECRET_KEY` — required for auth
- `SECRET_KEY` — fallback signing key
- `ADMIN_PASSWORD` — set before first deploy
- Optional: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `PAYSTACK_SECRET_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` / `CLAUDE_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`, `RESEND_API_KEY`, `REDIS_URL`

## Stack

- **Backend**: Python 3.11, FastAPI 0.115, SQLAlchemy 2.0 async, Alembic, Uvicorn
- **Frontend**: React 19, TypeScript, Vite 6, TailwindCSS 4, ShadCN/Radix UI
- **Database**: SQLite (dev) / PostgreSQL (prod) via `VIT_DATABASE_URL`
- **Auth**: JWT (python-jose) + TOTP 2FA (pyotp) + JWT blocklist (token_blocklist table)
- **AI**: Gemini → Claude → OpenAI → Grok → Puter cascade with 20s per-provider timeout
- **Payments**: Stripe (USD), Paystack (NGN), USDT, Pi Network, VITCoin

## Where things live

- `main.py` — FastAPI app, 559 routes, all background tasks wired (100KB, do not read all at once)
- `app/db/models.py` — all core ORM models (User, Match, Prediction, TokenBlocklist, etc.)
- `app/modules/` — 25 feature modules (wallet, blockchain, governance, trust, DID, etc.)
- `app/services/` — 50+ service files (AI providers, data pipelines, email, etc.)
- `app/auth/` — JWT, TOTP, verification routes
- `frontend/src/pages/` — 57 React pages, all lazy-loaded and routed in App.tsx
- `frontend/src/` — components, hooks, lib
- `.env.example` — full env var reference
- `alembic/versions/` — 16 DB migrations
- `scripts/` — startup, training, data pipeline scripts

## Architecture decisions

- **SQLite in dev, PostgreSQL in prod** — `VIT_DATABASE_URL` switches dialect; `aiosqlite` + `asyncpg` both installed
- **JWT + blocklist** — revoked tokens stored in `token_blocklist` table (jti column); checked on every request via `is_token_revoked()`
- **13 ML models** deferred in dev, activated via `USE_REAL_ML_MODELS=true` or in production; `.pkl` weights go in `models/`
- **AI cascade** — `multi_ai_dispatcher.py` fans out to up to 4 LLM providers with 20s per-provider `asyncio.wait_for` timeout; `app/services/scie.py` is the zero-API statistical fallback
- **Rate limiting** — Redis sliding window (when `REDIS_URL` set) with in-memory deque fallback; SEC-07 idle bucket eviction
- **CORS** — wildcard origins never paired with `allow_credentials=True` (SEC-02)
- **Timing-safe auth** — legacy API key comparison uses `hmac.compare_digest` (SEC-08)
- **TOTP DDL** — columns defined in `app/db/models.py`, created at startup via `Base.metadata.create_all`; no runtime ALTER TABLE

## Product

- Football match predictions (13-model ensemble, per-league calibration)
- Multi-AI analysis (Gemini, Claude, OpenAI, Grok, Puter) with SCIE statistical fallback
- VITCoin economy: wallet, deposits (Stripe/Paystack/USDT), withdrawals, subscriptions
- Blockchain: Base L2 oracle, VIT DID (W3C), bridge, staking validators
- Governance DAO with quorum + timelock enforcement
- Trust engine: composite scoring, fraud detection, auto-suspension
- 22 autonomous agents: fixture gap, KYC screening, model promoter, etc.
- 57-page frontend covering all modules
- Developer API marketplace with per-call VITCoin billing

## User preferences

- Iterative development with modular, functional code
- Detailed explanations for architectural decisions
- Ask before major structural changes

## Gotchas

- `main.py` is ~100KB — read in sections with offset/limit
- `torch>=2.0.0` is in requirements but heavy — install may be slow; ML models only load in production
- `BLOCKCHAIN_ENABLED=false` by default — set to `true` + provide `BASE_RPC_URL` for chain features
- `ADMIN_PASSWORD` blank in `.env.example` — must set before first deploy
- `requirements.txt` had 4× duplicate entries — now cleaned to single canonical list (41 packages)
- Background tasks (6 `asyncio.create_task` + supervisor) start in `lifespan`; check `/health` `agents` field to verify

## Pointers

- Security audit plan: `attached_assets/vit_debug_scan_plan.jsx_1778008560901.txt`
- Phase 3/4 implementation notes: `PHASE_3_IMPLEMENTATION.md`
- Roadmap: `ROADMAP.md`
