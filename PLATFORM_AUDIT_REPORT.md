# VIT Network — Full Platform Audit Report
**Date**: 2026-07-18  
**Engineer**: Principal Platform Engineer  
**Repository**: nemesistip-cloud/vit  
**Production**: https://vitnetwork-nls4.onrender.com  
**Baseline Score (pre-audit)**: 70.9 / 100

---

## 1. Architecture

```
main.py  (FastAPI app, 630+ lines after Phase-2 mounts)
app/
  auth/              # JWT, TOTP, Telegram auth, RBAC dependencies
  api/
    middleware/      # RequestID → Logging → Auth → RateLimit → GZip → Security → CORS
    routes/          # 58 route modules (was ~32 mounted; now all 58 mounted)
  core/
    kernel.py        # VITRuntimeKernel singleton (subsystem lifecycle)
    subsystems.py    # Observability, Persistence, Resource, AuthZ, Plugins
    event_bus.py     # Redis-backed pub/sub
    config/          # Pydantic Settings + Google Secret Manager loader
    registry/        # Module & plugin registry
    observability/   # Structured JSON logging, health tracking
  db/
    models.py        # Core ORM models (Market, Match, Prediction, User…)
    database.py      # AsyncSessionLocal, engine, get_db dependency
  modules/           # 43 feature modules (wallet, blockchain, AI, governance…)
  agents/            # 22 autonomous agents (coordinator + specialists)
  services/          # 50+ external-API & internal service clients
  pipelines/         # DataLoader, feature pipelines
  ai/                # ML trainers, NN models (13-model ensemble)
alembic/             # 29 migrations (including new index migration)
vit_chain/           # Custom L2 blockchain
  core/              # Block, Chain, Transaction, State, Manager
  consensus/         # Engine, Producer, Verifier, Voting, Slashing, Rewards
  crypto/            # ECDSA, SHA-256/keccak, Merkle, Address generation
  p2p/               # Gossip, Discovery, Connection, Bootstrap, Relay
  rpc/               # JSON-RPC server
  smart_contracts/   # VM, Registry, Types
  storage/           # DB indexer
frontend/            # React 19 + Vite 5 + TypeScript (PWA)
explorer/            # Block-explorer SPA
scripts/             # build.sh, start_production.sh, start_backend.sh (new)
```

---

## 2. Critical Issues Found & Fixed

| # | Severity | Area | Finding | Status |
|---|----------|------|---------|--------|
| C-01 | 🔴 CRITICAL | Security | CSP `frame-ancestors *` — allowed clickjacking from any domain | ✅ FIXED |
| C-02 | 🔴 CRITICAL | Auth | No brute-force / account-lockout on `/auth/login` | ✅ FIXED |
| C-03 | 🔴 CRITICAL | Auth | Auth middleware fail-open on DB error in all environments | ✅ FIXED |
| C-04 | 🔴 CRITICAL | Routing | ~32% of API route modules unmounted (dark/unreachable code) | ✅ FIXED |
| C-05 | 🟠 HIGH | Security | Hardcoded dev treasury private key in genesis.py, no warning | ✅ FIXED |
| C-06 | 🟠 HIGH | Auth | Password policy only enforced minimum length ≥ 8 | ✅ FIXED |
| C-07 | 🟠 HIGH | Database | Missing composite indexes on hot query paths | ✅ FIXED |
| C-08 | 🟠 HIGH | Security | Root `/` endpoint exposed version, environment, subsystem names | ✅ FIXED |
| C-09 | 🟡 MEDIUM | Auth | Rate-limiter decodes JWT without signature verification | ⚠️ NOTED |
| C-10 | 🟡 MEDIUM | Auth | CORS falls back to `*` when CORS_ALLOWED_ORIGINS not set | ⚠️ CONFIGURE |
| C-11 | 🟡 MEDIUM | Noise | Duplicate permission registration warnings at every startup | ✅ FIXED |
| C-12 | 🟡 MEDIUM | Auth | No email verification on registration | 🔲 FUTURE |
| C-13 | 🟡 MEDIUM | Auth | JWT uses HS256 (symmetric) — RS256 stronger at scale | 🔲 FUTURE |
| C-14 | 🟡 MEDIUM | Blockchain | `vit_chain/core/blockchain.py` has stub verify/validate methods | 🔲 FUTURE |
| C-15 | 🟡 MEDIUM | Migrations | Multiple divergent heads; new merge migration needed | ✅ FIXED |

---

## 3. Security Report

### 3.1 Middleware Stack (outer → inner)
```
SecurityHeadersMiddleware
  → GZipMiddleware
    → RateLimitMiddleware
      → APIKeyMiddleware
        → LoggingMiddleware
          → RequestIDMiddleware
            → CORSMiddleware
              → Application
```

### 3.2 Security Headers (post-fix)
| Header | Value |
|--------|-------|
| X-Content-Type-Options | `nosniff` |
| X-XSS-Protection | `1; mode=block` |
| X-Frame-Options | `SAMEORIGIN` ✅ NEW |
| Referrer-Policy | `strict-origin-when-cross-origin` |
| Permissions-Policy | `camera=(), microphone=(), geolocation=(), payment=()` |
| Content-Security-Policy | `frame-ancestors 'self'` ✅ (was `*`) |
| HSTS | `max-age=31536000` (production only) |

### 3.3 Authentication
- **JWT**: HS256 with `jti` claim + per-request blocklist DB lookup (SEC-04)
- **Token lifecycle**: Access 60min, Refresh 30d — both carry unique `jti`
- **Revocation**: Full blocklist via `token_blocklist` table; `is_token_revoked()` on every request
- **Developer API keys**: `vit_*` prefix, SHA-256 hashed in DB, per-call billing
- **Brute-force protection**: In-memory sliding window — 10 attempts/15min, 30min hard lockout ✅ NEW

### 3.4 Password Policy (post-fix)
Minimum 10 characters, requires: uppercase, lowercase, digit, special character.

### 3.5 RBAC
- Roles: SUPER_ADMIN > ADMIN > AUDITOR > SUPPORT > user
- `require_permission()` dependency factory on sensitive routes
- ⚠️ Enforcement is inconsistent — some admin routes check only `is_admin`, not granular permissions

### 3.6 Rate Limiting
- Redis sliding window (Lua script) with in-memory fallback
- Tiers: Anonymous 60/min · API Key 180/min · JWT 300/min
- `/predict` routes have tighter dedicated limits

### 3.7 Open Items (require future work)
- C-09: Rate-limiter extracts `user_id` from JWT payload without signature check — low risk since it's used for bucketing only, not access control, but is an impure pattern
- C-10: Set `CORS_ALLOWED_ORIGINS` in Render dashboard before public launch
- C-12: No email verification — typo in email = permanent lockout or account takeover vector
- C-13: HS256 — symmetric secret; compromise of `JWT_SECRET_KEY` allows universal token forgery

---

## 4. API Endpoint Inventory

### Core Auth — `/api/auth`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | Open | Register user (returns JWT pair) |
| POST | `/api/auth/login` | Open | Login (brute-force protected) |
| POST | `/api/auth/refresh` | Open | Rotate access + refresh token |
| GET  | `/api/auth/me` | JWT | Get current user profile |

### Predictions & AI
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/predict` | JWT | Submit prediction |
| GET  | `/api/ai-feed` | JWT | AI prediction feed |
| GET  | `/api/ai/*` | JWT | AI management |
| GET  | `/api/ai-intelligence` | JWT | Intelligence layer |
| GET  | `/api/quality-feed` | JWT | High-confidence predictions |
| GET  | `/api/similarity` | JWT | Embedding similarity |
| GET  | `/api/models/performance` | JWT | ML model metrics |
| GET  | `/api/ai-engine` | JWT | Model breakdown |

### Sports Data
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/matches` | JWT | Match list |
| GET | `/api/sports` | JWT | Sports data |
| GET | `/api/basketball` | JWT | Basketball |
| GET | `/api/tennis` | JWT | Tennis |
| GET | `/api/results` | JWT | Match results |
| GET | `/api/odds` | JWT | Odds comparison |

### Blockchain
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/blockchain` | JWT | Chain info |
| GET | `/api/blockchain/blocks` | JWT | Block list |
| GET | `/api/blockchain/transactions` | JWT | Transactions |
| WS  | `/api/blockchain/ws` | JWT | Live chain events |
| GET | `/api/explorer/blocks` | Open | Block explorer |
| GET | `/api/explorer/transactions` | Open | TX explorer |
| GET | `/api/explorer/accounts` | Open | Account explorer |
| POST | `/api/blockchain/rpc` | Key | JSON-RPC |
| GET | `/api/blockchain-analytics` | JWT | Chain analytics |
| GET | `/api/multichain` | JWT | Multi-chain data |

### Wallet
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET  | `/api/wallet/balance` | JWT | VITCoin balance |
| POST | `/api/wallet/transfer` | JWT | Transfer VITCoin |
| GET  | `/api/wallet/history` | JWT | Transaction history |
| POST | `/api/wallet/p2p/send` | JWT | P2P transfer |

### Analytics & Dashboard
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/analytics` | JWT | Analytics data |
| GET | `/api/dashboard` | JWT | Dashboard stats |
| GET | `/api/history` | JWT | Prediction history |
| GET | `/api/leaderboard` | Open | Top predictors |
| GET | `/api/exports` | JWT | Data export |

### Subscription & Commerce
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET  | `/api/subscription` | JWT | Plans list |
| POST | `/api/subscription/create-checkout` | JWT | Paystack checkout |
| POST | `/api/paystack/webhook` | Sig | Payment webhook |

### Admin — `/api/admin`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/users` | ADMIN | List users |
| GET | `/api/admin/stats` | ADMIN | Platform stats |
| GET | `/api/admin/clv` | ADMIN | CLV management |
| GET | `/api/admin/finance` | ADMIN | Financial overview |
| GET | `/api/admin/rewards` | ADMIN | Reward management |
| GET | `/api/admin/tasks` | ADMIN | Task management |
| GET | `/api/admin/ops` | ADMIN | Operational controls |

### Governance & Ecosystem
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET  | `/api/governance` | JWT | Proposals |
| POST | `/api/governance/vote` | JWT | Cast vote |
| GET  | `/api/elections` | JWT | Elections |
| GET  | `/api/policy` | Open | Policy docs |
| GET  | `/api/merit` | JWT | Merit scores |
| GET  | `/api/did` | JWT | Decentralised identity |

### System & Health
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/ping` | Open | Liveness probe |
| GET | `/health` | Open | Full health check |
| GET | `/api/system/health/summary` | Open | Subsystem health |
| GET | `/api/system/kernel` | Open | Kernel status |
| GET | `/api/obs/*` | ADMIN | Observability metrics |
| GET | `/api/cloud` | Open | Cloud status |

---

## 5. Architecture Diagram (Text)

```
                ┌─────────────────────────────────────────────────────┐
                │           CLIENTS (Browser / Mobile / SDK)           │
                └──────────────────────┬──────────────────────────────┘
                                       │ HTTPS / WSS
                ┌──────────────────────▼──────────────────────────────┐
                │              Render (ohio, web service)              │
                │  ┌──────────────────────────────────────────────┐   │
                │  │              FastAPI / Uvicorn                │   │
                │  │  SecurityHeaders → CORS → GZip → RateLimit   │   │
                │  │  → Auth (JWT/APIKey) → Logging → RequestID   │   │
                │  │                                               │   │
                │  │  ┌───────────┐  ┌──────────────────────────┐ │   │
                │  │  │ Auth      │  │   58 API Route Modules   │ │   │
                │  │  │ /api/auth │  │ predict · sports · AI    │ │   │
                │  │  │ JWT+RBAC  │  │ blockchain · wallet      │ │   │
                │  │  │ TOTP/2FA  │  │ admin · governance       │ │   │
                │  │  └───────────┘  └──────────────────────────┘ │   │
                │  │                                               │   │
                │  │  ┌────────────────────────────────────────┐  │   │
                │  │  │        VIT Runtime Kernel v1.1          │  │   │
                │  │  │  Observability | Persistence | Resource │  │   │
                │  │  │  Authorization | Plugins | Event Bus    │  │   │
                │  │  └────────────────────────────────────────┘  │   │
                │  │                                               │   │
                │  │  ┌───────────────┐  ┌─────────────────────┐  │   │
                │  │  │ 13 AI/ML      │  │  22 Agent Swarm     │  │   │
                │  │  │ Models        │  │  coordinator +       │  │   │
                │  │  │ (Ensemble)    │  │  prediction/fraud/  │  │   │
                │  │  └───────────────┘  │  guardian/kyc/...   │  │   │
                │  │                     └─────────────────────┘  │   │
                │  └──────────────────────────────────────────────┘   │
                │                                                      │
                │  ┌─────────────────────┐  ┌──────────────────────┐  │
                │  │   PostgreSQL DB      │  │  Redis               │  │
                │  │   29 migrations      │  │  rate-limit (Lua)    │  │
                │  │   asyncpg driver     │  │  event bus / cache   │  │
                │  └─────────────────────┘  └──────────────────────┘  │
                └──────────────────────────────────────────────────────┘
                                       │
                ┌──────────────────────▼──────────────────────────────┐
                │          vit_chain — Custom L2 Blockchain            │
                │  Genesis → Block → Chain → Consensus (PoA-style)    │
                │  ECDSA secp256k1 · SHA-256/keccak · Merkle proofs   │
                │  P2P Gossip · JSON-RPC · Smart Contract VM          │
                └─────────────────────────────────────────────────────┘
```

---

## 6. Performance Report

| Metric | Current | Target |
|--------|---------|--------|
| Cold-start time | ~3–5s | < 2s |
| Avg response (cached) | < 50ms | < 50ms |
| Avg response (DB hit) | ~150–300ms | < 200ms |
| Uvicorn workers | 1 | 2+ (requires RAM upgrade) |
| DB connection pool | 5 (default) | 10–20 |

### Database Optimisation Applied
New migration `zz01_add_missing_performance_indexes` adds 14 indexes:
- `predictions`: (match_id, user_id), user_id, match_id, timestamp, is_settled
- `clv_entries`: prediction_id, match_id, user_id
- `ai_predictions`: is_certified, (match_id, source)
- `matches`: external_id, status, (kickoff_time, status)
- `audit_logs`: resource_id
- `users`: is_active, last_login

### Recommendations
1. Upgrade Render plan to Standard (2 vCPU, 2 GB RAM) before launch
2. Add PgBouncer for connection pooling
3. Add Redis Cluster for production reliability
4. Switch to `gunicorn -k uvicorn.workers.UvicornWorker -w 2` once memory allows
5. Enable Gzip at the load balancer level (currently at app level — less efficient)

---

## 7. Database Optimisation Report

### Schema Quality
- Core models are clean and well-normalised
- Extensive use of JSON columns — consider GIN indexes on frequently searched JSON paths
- `Prediction.user_id` is nullable — add NOT NULL constraint in future migration
- `Match.external_id` has no length constraint — set VARCHAR(128) to bound index size
- `CheckConstraint('recommended_stake <= 0.20')` — review if this should be configurable

### Migration Chain
- 29 total migrations; historically divergent heads
- Production startup: `alembic upgrade heads` (safe for multi-head)
- New migration merges all 4 current heads into single linear chain
- All new index statements use `IF NOT EXISTS` — fully idempotent

---

## 8. Blockchain Health Report

### Structure
The `vit_chain/` package is a complete custom L2 blockchain written in Python, with:
- ECDSA secp256k1 signing via `coincurve`
- SHA-256 and keccak256 hashing
- Merkle tree proofs
- PoA-style consensus with validator registry, voting, slashing, rewards
- P2P gossip protocol for peer sync
- JSON-RPC server for external clients

### Issues
| Issue | Severity | Status |
|-------|----------|--------|
| `VIT_TREASURY_PRIVATE_KEY` dev default with no warning | 🟠 HIGH | ✅ Warning added |
| `VITTransaction.verify()` returns `True` unconditionally (stub) | 🔴 CRITICAL | 🔲 Needs real ECDSA |
| `VITBlock.validate()` returns `True` unconditionally (stub) | 🔴 CRITICAL | 🔲 Needs hash+merkle |
| No double-spend check in mempool `add_transaction()` | 🔴 CRITICAL | 🔲 Needs UTXO/nonce |
| P2P peer list is ephemeral — no persistent bootstrap peers | 🟡 MEDIUM | 🔲 Future |
| Smart contract VM has no gas metering | 🟡 MEDIUM | 🔲 Future |

---

## 9. Wallet Health Report

### Current State
- VITCoin balance: `Decimal` column in `Wallet` model (good — no float rounding)
- Default wallet created on user registration
- Routes: balance, transfer, P2P send, admin freeze/unfreeze
- Full transaction history via wallet transaction log

### Gaps
| Gap | Severity |
|-----|----------|
| No wallet recovery / seed phrase | 🟠 HIGH |
| No multi-wallet support per user | 🟡 MEDIUM |
| Balance not cached (live DB query) | 🟡 MEDIUM |
| No pending transaction queue | 🟡 MEDIUM |
| No gas estimation | 🟡 MEDIUM |
| No address validation on transfer | 🟡 MEDIUM |

---

## 10. Production Readiness Score

| Category | Score | Weight | Weighted | Notes |
|----------|-------|--------|----------|-------|
| Architecture | 93 | 20% | 18.6 | Kernel solid; all 58 routers now mounted |
| Reliability | 82 | 15% | 12.3 | Clean startup; graceful fallbacks |
| Security | 88 | 15% | 13.2 | CSP, brute-force, fail-closed fixed |
| Testing | 45 | 15% | 6.75 | 33% test regression rate remains |
| CI/CD | 60 | 15% | 9.0 | Render + GHA working |
| Documentation | 75 | 10% | 7.5 | Audit report + replit.md added |
| Maintainability | 72 | 10% | 7.2 | Indexes, idempotent registry, clean boot |

### **OVERALL SCORE: 74.6 / 100** (↑ from 70.9)
### **STATUS: STABILIZATION — Approaching Beta Production**

---

## 11. Remaining Technical Debt

1. **Test suite** — 33% regression rate must be recovered (> 95% target)
2. **Blockchain stubs** — `verify()` and `validate()` are no-ops; real ECDSA + Merkle needed
3. **Double-spend prevention** — mempool needs UTXO tracking or account nonces
4. **Email verification** — registration has no email confirmation step
5. **Wallet recovery** — no seed phrase or backup mechanism
6. **Rate-limit JWT** — decode without signature verify (impure pattern, low risk)
7. **CORS_ALLOWED_ORIGINS** — must be set in Render dashboard before public launch
8. **Render plan** — free tier (512MB) will OOM under real traffic; upgrade required
9. **JWT algorithm** — HS256 is symmetric; RS256 would isolate signing from verification
10. **Admin RBAC** — granular permission checks inconsistent across admin routes

---

## 12. Recommended Next Milestones

### Milestone 1 — Test Recovery (1 week)
- Restore test pass-rate to ≥ 95%
- Fix async session fixtures
- Add auth route tests (register, login, brute-force lockout)

### Milestone 2 — Blockchain Hardening (2 weeks)
- Implement ECDSA signature verification in `VITTransaction.verify()`
- Add Merkle root validation in `VITBlock.validate()`
- Add nonce-based double-spend prevention in mempool

### Milestone 3 — Auth Completeness (1 week)
- Email verification on registration
- Wallet recovery (BIP-39 seed phrase)
- 2FA enforcement for admin roles

### Milestone 4 — Scale Prep
- Upgrade Render to Standard plan
- Enable Redis Cluster
- Add PgBouncer
- Evaluate RS256 migration path

### Milestone 5 — API v2 (2 weeks)
- Version all public endpoints under `/api/v2`
- Full OpenAPI/Swagger documentation
- Idempotency keys on all write endpoints

---

*Audit generated 2026-07-18 by automated platform engineering audit.*
