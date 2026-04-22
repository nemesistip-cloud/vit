# VIT Sports Intelligence Network

## Overview
Institutional-grade football prediction platform combining a 12-model AI ensemble, a VITCoin wallet economy, blockchain-verified staking, a model marketplace, governance DAO, and multi-tier subscriptions (Free / Pro $49/mo / Elite $199/mo).

## Architecture
- **Backend:** Python 3.11, FastAPI, SQLAlchemy (async), Alembic, Uvicorn on port 5000
- **Database:** SQLite (development) / PostgreSQL (production via `VIT_DATABASE_URL`)
- **Frontend:** React 18 + TypeScript, Vite, TailwindCSS, ShadCN UI — built to `frontend/dist/` and served by FastAPI
- **Entry point:** `main.py` → `python main.py`
- **Workflow:** "Start application" runs `python main.py` on port 5000

## Module Map
| Module | Path | Status |
|--------|------|--------|
| AI Orchestrator (12 models) | `app/modules/ai/` | ✅ Running (synthetic mode) |
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
- `USE_REAL_ML_MODELS` — false (synthetic model data)

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
