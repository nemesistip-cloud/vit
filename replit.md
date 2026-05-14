# VIT Sports Intelligence Network v6.0

A 13-model AI ensemble football prediction platform with a VITCoin wallet economy, VIT-Chain sovereign ledger, 22 autonomous AI agents (all running), Telegram Mini App integration, cash-out sentinel, blockchain staking, model marketplace, and governance DAO.

## Run & Operate

```bash
bash scripts/start_fullstack.sh   # dev: frontend (5000) + backend (8000)
bash scripts/start_production.sh  # prod: builds frontend then starts gunicorn on :5000
pip install -r requirements.txt   # install backend deps
python3 -c "from main import app; print('OK')"  # test backend import
```

**Required secrets** (set in Replit Secrets):
- `JWT_SECRET_KEY`, `SECRET_KEY`, `ADMIN_PASSWORD`
- `GEMINI_API_KEY`, `OPENAI_API_KEY`, `CLAUDE_API_KEY`, `XAI_API_KEY`
- `DEEPSEEK_API_KEY` (DeepSeek — get free key at platform.deepseek.com)
- `MISTRAL_API_KEY` (Mistral AI — get free key at console.mistral.ai)
- `TELEGRAM_BOT_TOKEN`, `PAYSTACK_SECRET_KEY`, `STRIPE_SECRET_KEY`
- `DATABASE_URL` (PostgreSQL in prod)
- Optional: `REDIS_URL`, `RESEND_API_KEY`, `VAULT_MASTER_KEY` (TMA vault encryption)

## Stack

- **Backend**: Python 3.11, FastAPI 0.115, SQLAlchemy 2.0 async, Alembic, Uvicorn
- **Frontend**: React 19, TypeScript, Vite 6, TailwindCSS 4, ShadCN/Radix UI
- **Database**: SQLite (dev) / PostgreSQL (prod) via `DATABASE_URL`
- **Auth**: JWT (python-jose) + TOTP 2FA + JWT blocklist (`token_blocklist` table)
- **AI**: Gemini → Claude → OpenAI → Grok → Puter cascade, 20s per-provider timeout
- **Payments**: Stripe (USD), Paystack (NGN), USDT, Pi Network, VITCoin

## Where things live

- `main.py` — FastAPI app, 530+ routes, lifespan wires SwarmOrchestrator + VIT-Chain
- `vit_chain.py` — VIT-Chain sovereign ledger (hash-linked SQLite, PoW difficulty=4)
- `app/core/swarm_orchestrator.py` — SwarmOrchestrator: all 22 agents + 30s heartbeat
- `app/modules/betting/cash_out_sentinel.py` — momentum-based auto cash-out engine
- `app/modules/telegram_mini_app/integration.py` — TMA initData auth + vault + metering
- `app/api/middleware/auth.py` — APIKeyMiddleware with `_PUBLIC_SUBPATHS` for telemetry
- `app/db/models.py` — core ORM models
- `app/agents/` — all 22 agent implementations
- `app/modules/` — 25 feature modules
- `app/services/` — 50+ service files
- `frontend/src/pages/` — 57 React pages
- `alembic/versions/` — 17 migrations (latest: e5f6a7b8c9d0 v6 schema fixes)

## Architecture decisions

- **SwarmOrchestrator replaces AgentCoordinator** — `app/core/swarm_orchestrator.py` supervises all 22 agents with per-agent restart tracking; `app.state.agent_coordinator` kept as alias for legacy routes
- **VIT-Chain is a separate SQLite file** — `vit_chain_ledger.db` (not the main app DB); auto-mints VIT on Stripe/Paystack deposit (1 VIT per $1 USD)
- **Health endpoint reads `swarm.health_summary()`** — fixed miscounting bug that showed 2/6 instead of 22/22
- **JWT + blocklist** — revoked tokens in `token_blocklist`; checked every request via APIKeyMiddleware
- **AI cascade (chat)** — `gemini_chat.py` cascades Gemini→Claude→Grok on 429/error; each response carries `provider` field shown as badge in UI
- **AI cascade (analysis)** — `multi_ai_dispatcher.py` fans out to 4 LLM providers; `scie.py` is statistical fallback
- **Rate limiting** — Redis sliding window (when `REDIS_URL` set) with in-memory deque fallback
- **TMA vault** — AES-256-GCM credential encryption via `VAULT_MASTER_KEY`; falls back to base64 in dev
- **`/admin/client-error` is public** — listed in `_PUBLIC_SUBPATHS` in `auth.py` AND mounted on `public_router` in `admin.py` so React ErrorBoundary telemetry always works
- **Production serves SPA** — `start_production.sh` builds `frontend/dist` first; FastAPI mounts `/assets` + SPA catch-all from `main.py`; deployment target is autoscale on port 5000

## Product

- Football match predictions (13-model ensemble, per-league calibration)
- Multi-AI analysis (Gemini, Claude, OpenAI, Grok) + SCIE statistical fallback
- VITCoin economy: wallet at `/api/wallet/*`, deposits (Stripe/Paystack/USDT), auto-minting
- VIT-Chain: sovereign hash-linked ledger at `/api/chain/*` — mint/transfer/verify/stats
- Telegram Mini App: `/api/tma/*` — initData auth, AES vault, tool credit marketplace
- Cash-Out Sentinel: `/api/cashout/*` — 3 strategies (aggressive/balanced/conservative)
- 22 autonomous agents: all running, supervised with auto-restart
- Governance DAO at `/api/governance/*`, developer platform at `/api/developer/*`
- 57-page frontend covering all modules
- Match detail: `ProbabilityTrio`, `ModelInterpretation`, `OddsRow`, `FactorCard` in Analysis tab
- MatchAssistantCard: provider attribution badge (Gemini/Claude/Grok) per response
- Routes `/competitions` → `/matches` and `/social` → `/leaderboard` redirects added

## User preferences

- Iterative development with modular, functional code
- Detailed explanations for architectural decisions
- Ask before major structural changes

## Gotchas

- `main.py` is ~100KB — read in sections with offset/limit
- VIT-Chain DB is `vit_chain_ledger.db` (separate from app DB; configurable via `VIT_CHAIN_DB`)
- `VAULT_MASTER_KEY` not set → TMA vault uses base64 fallback (dev only; set for prod)
- SwarmOrchestrator spawns 22 asyncio tasks at startup — logs show all starting in sequence
- Background supervisor (etl-pipeline, odds-refresh, cache-purge, task-reset) is separate from SwarmOrchestrator
- `BLOCKCHAIN_ENABLED=false` by default — set to `true` + `BASE_RPC_URL` for Base L2 chain features
- Odds endpoints (`/odds/arbitrage`, `/odds/compare`) return 503 without an Odds API key — expected behavior
- Backend startup takes ~30-35s (22 agents + migrations + seeding) before accepting connections

## Pointers

- Audit report: `VIT_AUDIT_REPORT.md`
- Phase 3/4 notes: `PHASE_3_IMPLEMENTATION.md`
- Roadmap: `ROADMAP.md`
