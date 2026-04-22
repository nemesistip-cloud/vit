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

## Recent Changes — Staking Hardening (Apr 22 2026)
All VITCoin balance changes in the staking subsystem now flow through `WalletService.credit/debit`, which:
- Locks the wallet row with `SELECT … FOR UPDATE` (no more double-spend race)
- Records a `WalletTransaction` for every move (full audit trail using existing `STAKE`/`REWARD`/`SLASH` types)
- Honors `is_frozen` and validates balance atomically

Settlement (`settlement.py`) now:
- Refunds (status `REFUNDED`) stakes whose market the oracle could not resolve, instead of marking them LOST
- Accumulates `ValidatorProfile.reward_earned` (was overwriting per-match)
- Batch-loads all involved wallets (no N+1)
- Sends per-stake `MATCH_RESULT` notifications (won / lost / refunded) with PnL

Stake placement (`/predictions/{match_id}/stake`) now:
- Enforces `MIN_STAKE=1`, `MAX_STAKE=100000` VIT
- Blocks staking once `Match.kickoff_time` has passed
- Locks the wallet row before the debit

Validator endpoints (`apply`, `withdraw`, admin `reject`, admin `slash`) all use the same locked, audited path.

## Recent Changes — Per-Route Code Splitting (Apr 22 2026)
`frontend/src/App.tsx` now imports every authenticated/secondary page through `React.lazy` with a single `<Suspense>` boundary around `<Switch>`. Eager pages: landing, auth, info (legal), not-found.

Bundle results (gzip in parens):
- **Main bundle: 814 KB → 412 KB (122 KB gz)** — 49% reduction
- `vendor-charts` (394 KB / 108 KB gz) is no longer in the critical path; only loaded by chart-using pages (dashboard, analytics, admin, training)
- Each route is its own chunk — heaviest are admin (63 KB / 13 KB gz), training (30 KB / 8 KB gz), predictions (28 KB / 9 KB gz)
- 24 route chunks total, fetched on demand

## Recent Changes — Accumulator Auto-Relax (Apr 22 2026)
The accumulator engine now refuses to leave the user with a 1-candidate scan (which can't form an accumulator).

`GET /admin/accumulator/candidates` (`app/api/routes/admin.py`):
- Scores every fixture once, then filters; new params `auto_relax=True` and `target_min=4`
- If fewer than `target_min` candidates pass the user's filters, edge is dropped first in 0.005 steps to 0, then confidence in 0.05 steps to 0.50, until enough candidates emerge
- Response now includes `applied_filters`, `relaxed`, `relax_steps`, `scored`

`frontend/src/pages/accumulator.tsx`:
- Default Min Legs raised from 1 → 2 (an accumulator is by definition multi-leg)
- Yellow "auto-loosened" banner shows the actually-applied filters when they differ from requested
- Orange single-candidate banner with one-tap "Loosen & rescan" button (drops edge to 0, drops confidence by 0.10, scans 10 more fixtures)
- Pluralization fix ("1 candidate" / "N candidates")
