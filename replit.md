# VIT Network — Backend Platform

## Project overview

VIT Network is an AI-powered, decentralised sports-intelligence platform built
on FastAPI (Python) with a React/Vite frontend and a custom blockchain layer.
The production deployment is at **https://vitnetwork-nls4.onrender.com**.

### Repository layout
```
main.py               # FastAPI application entry point
app/
  auth/               # JWT, routes, TOTP, telegram auth
  api/
    middleware/       # Auth, rate-limit, security headers, logging
    routes/           # ~58 API route modules
  core/               # Kernel, registry, event bus, observability
  db/                 # SQLAlchemy models, async session
  modules/            # Feature modules (wallet, blockchain, AI, etc.)
  agents/             # 22-agent swarm
  services/           # External-API clients, email, storage
  pipelines/          # Data-loading and feature pipelines
  ai/                 # ML model training helpers
alembic/              # Database migrations
vit_chain/            # Custom L2 blockchain (consensus, p2p, crypto)
vit_node/             # Node daemon
frontend/             # React 19 + Vite SPA
explorer/             # Block-explorer frontend
scripts/              # Build, start, seed, migration helpers
```

### Tech stack
- **Backend**: FastAPI 0.110+, SQLAlchemy 2 (async), Alembic, Uvicorn
- **Database**: PostgreSQL (asyncpg driver) + Redis (rate-limiting/cache)
- **AI / ML**: scikit-learn, XGBoost, SciPy, NumPy, Pandas, 13 ensemble models
- **Blockchain**: Custom ECDSA/SHA-256 chain (vit_chain), Web3 Base L2 bridge
- **Auth**: JWT (HS256, jti blocklist), bcrypt, TOTP (2FA), RBAC
- **Frontend**: React 19, Vite 5, TypeScript, TailwindCSS
- **Deployment**: Render (web + worker services), Docker, GitHub Actions CI

## Running in Replit (dev)

The configured workflow `Start application` launches the **Vite dev server** on
port 5000. The FastAPI backend requires environment secrets; run it separately:

```bash
bash scripts/start_backend.sh   # starts uvicorn on port 8000
```

Required secrets (set in Replit Secrets panel):
- `SESSION_SECRET` — session signing key
- `JWT_SECRET_KEY` — (optional override; falls back to SESSION_SECRET)

For full functionality you also need:
- `DATABASE_URL` — PostgreSQL connection string (async, `postgresql+asyncpg://`)
- `REDIS_URL` — Redis connection string

## User preferences

- Senior engineer tone: explain *why* a change is needed, show files touched.
- Preserve backward compatibility unless a breaking change is justified and documented.
- Always add a `**Why:**` rationale when writing decisions to memory.
- Use `async/await` throughout — no synchronous DB calls in FastAPI handlers.
- Follow existing patterns: structured error responses via `error_response()`.
