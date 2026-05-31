# VIT Network: Africa's AI Intelligence Oracle & Blockchain Super App

[![Build Status](https://img.shields.io/badge/Version-5.1.0-blue.svg)](https://github.com/vit-network/vit-blockchain)
[![Ecosystem](https://img.shields.io/badge/Blockchain-Base_L2-emerald.svg)](https://base.org)
[![Intelligence](https://img.shields.io/badge/AI-Ensemble_Swarm-orange.svg)](app/ai)

VIT is the premier intelligence layer for the African digital economy. By combining a multi-model AI ensemble with a decentralized agent swarm and Base L2 settlement, VIT provides verifiable, high-confidence insights for sports, elections, policy, and marketplace intelligence.

---

## 🌟 Vision
To build Africa's largest digital super network, empowering 100 million users with verifiable intelligence, seamless financial inclusion, and a decentralized marketplace for the next generation of the African economy.

## 🚀 The Real System (Audit Summary)
Unlike traditional platforms, VIT is a living ecosystem built on three core layers:
1.  **Intelligence Tier**: 13+ ML models (LSTM, XGBoost, Transformer) orchestrated by an autonomous agent swarm.
2.  **Infrastructure Tier**: High-speed decentralized storage (Tachyon Fabric) and persistent PostgreSQL state.
3.  **Settlement Tier**: Gasless transactions via Biconomy and smart contract oracles on Base L2.

---

## 📦 Core Products

### 🏆 Sports Intelligence (Production Ready)
- **AI Ensemble**: Real-time predictions across major football leagues with 60/40 weight distribution between Scikit-learn and PyTorch LSTM models.
- **VIT Score**: A proprietary high-confidence metric for signal reliability.
- **Smart Settlements**: Automated on-chain result verification via `UniversalOracle.sol`.

### 🤖 Autonomous Agent Swarm (Production Ready)
- **22+ Specialized Agents**: Including Audit Sentinels, Fraud Reviewers, and Market Scouts.
- **Lazy-Loading Architecture**: Optimized for memory-constrained environments (512MB RAM).

### 💳 Wallet & Financial Services (Production Ready)
- **Regional Payments**: Support for OPay, PalmPay, and MTN MoMo.
- **Gasless UX**: Biconomy account abstraction for seamless user onboarding.
- **Loyalty Vault**: Automated yield and rewards for ecosystem participants.

### 🏪 Signal Marketplace (Beta)
- **Peer-to-Peer Intelligence**: Users can list and subscribe to custom AI models.
- **Staking & Slashing**: Protocol-level incentives for signal accuracy.

### 🌌 Tachyon Fabric (Beta)
- **Swarm Storage**: Parallel burst transfers across aggregated cloud providers (Gdrive, etc.).
- **Quantum-Safe**: EEC-based erasure coding for high-speed fragmentation.

### 🏛️ Elections & Policy (In Development)
- **Sentiment Engine**: Real-time analysis of citizen sentiment and electoral polling.
- **Policy Simulator**: Verifiable forecasts for regional economic and political shifts.

---

## 🏗️ Architecture

```mermaid
graph TD
    User((User App)) -->|React 19| Frontend[Frontend / Dashboard]
    Frontend -->|FastAPI| API[API Gateway]

    subgraph "Intelligence Tier"
        API -->|Orchestrator| Agents[Agent Swarm]
        Agents -->|Ensemble| ML[ML Service]
        ML -->|Predictions| DB[(PostgreSQL)]
    end

    subgraph "Infrastructure Tier"
        Agents -->|Verification| Storage[Tachyon Fabric]
        API -->|Oracle| Chain[Base L2 / Smart Contracts]
    end

    subgraph "External"
        Chain -->|Biconomy| Auth[Passkey Auth]
        API -->|Payments| MobileMoney[OPay / PalmPay / MoMo]
    end
```

---

## 🛠️ Technology Stack
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy, Uvicorn.
- **Frontend**: React 19, Vite, Tailwind CSS, Lucide React.
- **AI/ML**: Scikit-learn, XGBoost, PyTorch, Ollama (Internal VIT Brain).
- **Blockchain**: Solidity 0.8.28, Foundry, Viem, Biconomy SDK.
- **Database**: PostgreSQL (Production), Redis (Caching), ChromaDB (RAG).
- **Storage**: Tachyon Fabric (Fragmentation + EEC).

---

## 📂 Repository Structure
- `app/`: Core FastAPI application and agent logic.
- `frontend/`: React 19 single-page application.
- `packages/contracts/`: Smart contracts (Foundry).
- `packages/sdk/`: TypeScript SDK for ecosystem integrations.
- `services/ml_service/`: Decentralized ML orchestrator.
- `tachyon/`: Parallel swarm storage coordination service.
- `scripts/`: Deployment, training, and maintenance utilities.

---

## 🏁 Getting Started

### Quick Start
```bash
# Install dependencies
npm install && pnpm install --filter "./frontend"

# Start the full stack (Development)
./scripts/start_fullstack.sh
```

### Backend Setup
```bash
# Configure environment
cp .env.example .env

# Run backend
./scripts/start_backend.sh
```

### Frontend Setup
```bash
cd frontend
pnpm install
pnpm dev
```

---

## 🆕 What's New in v5.1.0 (2026-05-31)

**Stability & Test-Suite Hardening Release** — zero failing tests, no regressions.

| Area | Change |
|------|--------|
| `predict.py` | Fixed `TypeError` — `data_quality` was passed as the 4th positional arg (mapped to `sport`). |
| `ai_assistant.py` | Fixed `AttributeError` — missing `await` on async `provider_status()`. |
| `errors.py` + `request_id.py` | Fixed duplicate `X-Request-ID` response header. Middleware now skips headers already set by `error_response()`. |
| `worker.py` test | Fixed false-positive: `REDIS_URL` env var leaked into test that expects Celery to be unavailable. |
| `isports` test | Replaced deprecated `asyncio.get_event_loop().time()` with `time.time()`; added skip for live-network integration test. |
| `test_ml_models.py` | Fixture now sets `USE_REAL_ML_MODELS=false` + `FeatureFlags.reset()` before building the orchestrator. |
| `test_predictions_functional.py` | Odds payload corrected to `market_odds: {home, draw, away}` object format. |
| Test DB | Deleted stale/corrupt `vit.db`; session fixture cleanly recreates it. |

**Test results**: 267 passed, 1 skipped (integration-only), 0 failed (was 252/0/16).

Full details in [docs/CHANGELOG.md](docs/CHANGELOG.md).

---

## 🗺️ Roadmap
- **Q4 2024**: Full migration to Base L2 and Tachyon Beta launch. (Completed)
- **Q1 2025**: Electoral Oracle integration and Agent Recruitment Portal.
- **Q2 2025**: Cross-border remittance rails via .
- **Q3 2025**: Expansion to Kenya and Ghana ecosystems.

See [ROADMAP.md](ROADMAP.md) for the detailed strategic plan.

---

## 🤝 Contributing
We welcome contributors from all backgrounds. Please see our [Integration Guide](INTEGRATION_GUIDE.md) for technical standards.

## 🛡️ Security
For security disclosures, please refer to our internal security team via the [Security Dashboard](frontend/src/pages/security.tsx).

## 📄 License
Check individual modules for licensing. A root LICENSE file is pending (See Gap Analysis).

---

Built with ⚡ by the VIT Network Foundation.

## ☁️ Deployment (Google Cloud Platform)

VIT Network is production-ready for Google Cloud Platform.

### Quick Start
1. Ensure you have the [Google Cloud SDK](https://cloud.google.com/sdk) installed.
2. Run the deployment script:
   ```bash
   gcloud builds submit --config cloudbuild.yaml .
   ```

Refer to the [GCP Deployment Guide](DEPLOYMENT_GCP.md) for detailed instructions on setting up Cloud Run, Cloud SQL, and Secret Manager.

### Docker Support
You can also run VIT locally using Docker Compose:
```bash
docker-compose up --build
```
