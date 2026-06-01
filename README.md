# VIT Network — Africa's AI Intelligence Oracle & Blockchain Super App

[![Version](https://img.shields.io/badge/Version-5.1.0-blue.svg)](https://github.com/nemesistip-cloud/vit)
[![Blockchain](https://img.shields.io/badge/Blockchain-Base_L2-emerald.svg)](https://base.org)
[![AI](https://img.shields.io/badge/AI-13_Model_Ensemble-orange.svg)](app/modules/ai)
[![Deployment](https://img.shields.io/badge/Deploy-Google_Cloud_Run-4285F4.svg)](https://cloud.google.com/run)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

VIT is Africa's premier intelligence layer — combining a 13-model AI ensemble, an autonomous 22-agent swarm, and Base L2 blockchain settlement to deliver verifiable, high-confidence insights for sports, elections, policy, and marketplace intelligence.

---

## 🌟 Vision

To build Africa's largest digital super network, empowering 100 million users with verifiable intelligence, seamless financial inclusion, and a decentralised marketplace for the next generation of the African digital economy.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    User / Client                            │
│            React 19 + Vite + Tailwind CSS v4               │
└───────────────────────────┬────────────────────────────────┘
                            │ HTTPS / WebSocket
┌───────────────────────────▼────────────────────────────────┐
│            FastAPI Gateway   (Python 3.11)                  │
│   JWT Auth · TOTP · Google OAuth · Telegram Mini App       │
│   Rate Limiting · CORS · Request-ID tracing                │
└──────┬──────────────────────┬───────────────┬──────────────┘
       │                      │               │
┌──────▼──────┐   ┌───────────▼─────┐  ┌──────▼──────────────┐
│ Intelligence │   │  Wallet &       │  │  Blockchain Layer   │
│    Tier      │   │  Payments       │  │  Base L2 / Oracles  │
│ 13 ML models │   │ NGN·USD·USDT    │  │  VITCoin · DID      │
│ 22 AI agents │   │ Paystack·Stripe │  │  Smart Contracts    │
└──────┬───────┘   └─────────────────┘  └─────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────┐
│                  Data & Storage Layer                        │
│  PostgreSQL (prod) │ SQLite (dev) │ Redis (cache/streaks)   │
│  TheSportsDB · Football-Data.org · The Odds API             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Core Modules

| Module | Status | Description |
|--------|--------|-------------|
| **Sports Intelligence** | ✅ Production | 13-model ensemble (LSTM, XGBoost, Transformer, Logistic, Poisson, Elo, Dixon-Coles, Bayesian) with CLV streak tracking |
| **Autonomous Agents** | ✅ Production | 22 specialised agents — live-match tracker, weight optimiser, oracle, KYC screener, fraud reviewer, and more |
| **Wallet & Payments** | ✅ Production | Multi-currency (NGN/USD/USDT/VITCoin/PI) with Paystack, Stripe, and blockchain settlement |
| **Signal Marketplace** | ✅ Production | Peer-to-peer intelligence trading with staking and accuracy-based slashing |
| **VIT DID Identity** | ✅ Production | W3C-compliant decentralised identity for African users |
| **Tachyon Fabric** | 🔶 Beta | Swarm storage coordination across cloud providers with EEC erasure coding |
| **Elections & Policy** | 🔶 Beta | Electoral sentiment engine and verifiable policy simulation |
| **Academy** | ✅ Production | Gamified learning paths with XP, streaks, and on-chain credentials |

---

## 🛠️ Technology Stack

### Backend
- **Runtime**: Python 3.11+
- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL (production) / SQLite (development)
- **Cache**: Redis (distributed rate-limiting, CLV streaks, session)
- **Auth**: JWT (HS256) + TOTP 2FA + Google OAuth + Telegram Mini App
- **ML**: Scikit-learn, XGBoost, PyTorch, Statsmodels (13-model ensemble)
- **Blockchain**: Web3.py, Viem, Wagmi (Base L2 / chain_id = 8453)
- **Migrations**: Alembic (21 migration files)

### Frontend
- **Framework**: React 19 + Vite 6 + TypeScript
- **Styling**: Tailwind CSS v4 + Radix UI primitives
- **State**: TanStack Query v5
- **Routing**: Wouter
- **Web3**: Viem + Wagmi + WalletConnect

---

## 🚀 Quick Start (Development)

### Prerequisites
- Python 3.11+
- Node.js 20+

### Setup

```bash
# Clone the repository
git clone https://github.com/nemesistip-cloud/vit.git
cd vit

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# Start full stack (backend + frontend dev server)
bash scripts/start_fullstack.sh
```

The app will be available at `http://localhost:5000`.
API health check: `http://localhost:8000/health`

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | ✅ | JWT signing secret (min 32 chars) |
| `DATABASE_URL` | ✅ | PostgreSQL URL (SQLite used if unset in dev) |
| `ADMIN_PASSWORD` | ✅ | Initial admin account password |
| `FOOTBALL_DATA_API_KEY` | ⭐ | Football-Data.org API key |
| `THE_ODDS_API_KEY` | ⭐ | The Odds API key |
| `GEMINI_API_KEY` | ⭐ | Google Gemini AI key |
| `ANTHROPIC_API_KEY` | ⭐ | Anthropic Claude API key |
| `OPENAI_API_KEY` | ⭐ | OpenAI API key |
| `PAYSTACK_SECRET_KEY` | 💳 | Paystack (NGN payments) |
| `STRIPE_SECRET_KEY` | 💳 | Stripe (USD payments) |
| `RESEND_API_KEY` | 📧 | Transactional email |
| `TELEGRAM_BOT_TOKEN` | 📱 | Telegram bot integration |
| `REDIS_URL` | 🔧 | Redis for distributed caching |

> Without optional keys the app runs in degraded mode — predictions fall back to TheSportsDB (free), AI uses Puter browser fallback, and payments are disabled.

---

## ☁️ Production Deployment — Google Cloud Run

### Build & Deploy

```bash
# Build and push the Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/vit-network:latest

# Deploy to Cloud Run
gcloud run deploy vit-network \
  --image gcr.io/YOUR_PROJECT/vit-network:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets JWT_SECRET_KEY=jwt-secret:latest,DATABASE_URL=db-url:latest
```

The `Dockerfile` at the repository root handles:
1. Installing Python + Node.js dependencies
2. Building the React frontend (`frontend/dist/`)
3. Running database migrations via Alembic
4. Starting FastAPI with Uvicorn on `$PORT`

### Replit Deploy

Click the **Deploy** button in the Replit workspace. The `.replit` file is pre-configured with `deploymentTarget = "cloudrun"`.

---

## 📁 Repository Structure

```
vit/
├── main.py                      # FastAPI application entry point
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Cloud Run container build
├── alembic.ini                  # Alembic migration config
├── alembic/versions/            # 21 database migration files
├── app/
│   ├── config.py                # All environment variable config
│   ├── agents/                  # 22 autonomous agent implementations
│   ├── api/                     # FastAPI routers and middleware
│   ├── auth/                    # JWT · TOTP · OAuth · Telegram auth
│   ├── core/                    # Logging · error handling · rate limiting
│   ├── data/                    # ETL pipeline and DB models
│   ├── db/                      # SQLAlchemy session management
│   ├── modules/                 # Feature modules (20+)
│   │   ├── ai/                  # ML orchestration
│   │   ├── blockchain/          # Base L2 integration
│   │   ├── wallet/              # Multi-currency wallet
│   │   ├── marketplace/         # Signal marketplace
│   │   ├── identity/ & did/     # W3C DID identity
│   │   ├── governance/          # DAO governance
│   │   ├── rewards/             # Loyalty and staking
│   │   ├── trust/               # Trust scoring
│   │   ├── academy/             # Gamified learning
│   │   └── …                    # bridge, quant, kyc, subchain, iot …
│   ├── pipelines/               # Data ingestion pipeline
│   └── services/                # Business logic (50+ service files)
├── frontend/                    # React 19 SPA
│   ├── src/components/          # UI components
│   ├── src/pages/               # Route-level pages
│   └── vite.config.ts           # Dev server with API proxy
├── models/                      # Trained ML model weights (.pkl)
│   └── calibrators/             # Probability calibrators
├── scripts/                     # Operational & seeding scripts
│   ├── start_fullstack.sh       # Dev startup (backend + frontend)
│   ├── start_production.sh      # Production startup (Cloud Run)
│   └── seed_*.py                # Database seeding utilities
├── tachyon/                     # Tachyon Fabric storage service
└── packages/
    ├── contracts/               # Solidity smart contracts (Foundry)
    └── sdk/                     # TypeScript SDK
```

---

## 🆕 What's New in v5.1.0 (2026-05-31)

**Stability & Deployment Release**

| Area | Change |
|------|--------|
| `clv_streak_monitor.py` | Fixed UTC timezone crash — SQLite returns timezone-naive datetimes; normalised with `.replace(tzinfo=utc)` before comparison |
| `wallet/services.py` | Added `seed_wallet_subscription_plans()` — seeds Free / Analyst / Pro / Elite plan tiers on startup |
| `Dockerfile` | New — Google Cloud Run multi-stage build (Python 3.11 + Node 20, builds frontend, runs migrations, serves unified app) |
| `predict.py` | Fixed `TypeError` — `data_quality` was passed as wrong positional arg |
| `ai_assistant.py` | Fixed `AttributeError` — missing `await` on async `provider_status()` |
| `errors.py` + `request_id.py` | Fixed duplicate `X-Request-ID` response header — middleware now guards before appending |
| `worker.py` test | Fixed false-positive: `REDIS_URL` env var leaked across test isolation |
| `test_ml_models.py` | Fixture now sets `USE_REAL_ML_MODELS=false` + `FeatureFlags.reset()` before ML orchestrator init |
| `test_predictions_functional.py` | Odds payload corrected to `market_odds: {home, draw, away}` object format |
| Test DB | Deleted stale corrupt `vit.db`; session fixture cleanly recreates from schema |

**Test results**: 267 passed · 1 skipped · 0 failed (was 252 passed · 0 skipped · 16 failed)

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## 🗺️ Roadmap

- **Q1 2026**: Cloud Run deployment · CLV streak hardening · Test-suite 100% pass rate ✅
- **Q2 2026**: Electoral Oracle integration · Agent Recruitment Portal
- **Q3 2026**: Cross-border remittance rails · Kenya & Ghana ecosystem expansion
- **Q4 2026**: Tachyon Fabric v1 GA · Full Base L2 migration

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes following [Conventional Commits](https://www.conventionalcommits.org/)
4. Push and open a Pull Request against `main`

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

*VIT Network — Where Value, Intelligence, and Trust Converge.*
*Built for Africa 🌍*
