# VIT Network (v5.5.0)
### AI Intelligence Oracle & Blockchain Super App

VIT Network is an institutional-grade intelligence layer providing verifiable, high-confidence insights across multiple verticals including sports, electoral sentiment, and macroeconomic policy. The ecosystem leverages a 13-model AI ensemble, autonomous agent coordination, and a custom Proof-of-Storage blockchain to deliver a transparent and decentralised intelligence marketplace.

---

## 🏛️ Leadership & Architecture

VIT Network is architected and led by **Anselem Anyigor Chijioke**, focusing on the integration of institutional-grade AI, decentralized storage (Tachyon), and blockchain-anchored intelligence. The platform follows a "Mission Control" design philosophy, prioritizing high-density data and verifiable trust.

For a deep-dive into the architectural vision, see the [Technical Portfolio](./portfolio/README.md).

---

## 🌐 Live Services

| Service | URL | Status |
|---------|-----|--------|
| **VIT Network** (main app) | https://vitnetwork-nls4.onrender.com | ✅ Live |
| **vit-ai** (AI Oracle) | https://vit-ai.onrender.com | ✅ Live |
| **vit-chain** (Blockchain Node) | https://vit-chain.onrender.com | ✅ Live |
| **vit-storage** (Tachyon Fabric) | https://vit-storage-4trt.onrender.com | ✅ Live |

---

## 🏗️ System Architecture

- **Intelligence Layer**: 13-model ML ensemble (LSTM, XGBoost, Transformers) with autonomous re-weighting. Verified: `models_loaded: 13`.
- **Agentic Swarm**: 22 specialised agents for live-data ingestion, anomaly detection, and risk assessment (APScheduler-managed).
- **Financial Rails**: Multi-currency wallet (USD, NGN, USDT, VITCoin) with Paystack and Flutterwave integration.
- **Blockchain Layer**: VIT Chain (Chain ID 7764) — custom Proof-of-Storage L1 node. Base L2 (chain_id 8453) integration is the settlement migration target (see roadmap).
- **Tachyon Fabric**: Parallelized swarm storage with 4 active cloud providers and Reed-Solomon Erasure Coding (EEC).
- **Frontend SPA**: React 19 + Vite + Tailwind CSS v4 high-performance interface.

---

## 📦 Core Deliverables

| Product | Status | Functionality |
|---------|--------|---------------|
| **Sports Oracle** | ✅ GA | Verifiable match predictions with CLV tracking and model accountability. |
| **Sentiment Engine** | ✅ Beta | Real-time electoral and policy sentiment analysis using native AI reasoning. |
| **Marketplace** | ✅ GA | Peer-to-peer intelligence trading with accuracy-based slashing mechanisms. |
| **Identity (DID)** | 🔄 Beta | W3C-compliant decentralised identity — TRACK-020 active, credential NFTs in development. |
| **Tachyon Storage** | ✅ Live | High-availability multi-cloud swarm storage (4 providers, quantum_stable). |
| **Remittance** | ✅ Beta | Cross-border financial rails utilizing blockchain liquidity. |
| **VIT Chain** | ✅ Testnet | Standalone PoS L1 node — block height 1845+, 15s epochs, live at vit-chain.onrender.com. |

---

## 🛠️ Technical Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Alembic.
- **Database**: PostgreSQL (Production), SQLite (Dev), Redis (Cache/Rate-limiting).
- **Machine Learning**: PyTorch, Scikit-learn, XGBoost, Statsmodels — 13 models loaded.
- **Blockchain**: VIT Chain (custom PoS, Chain ID 7764) + Web3.py, Viem, Wagmi, WalletConnect (Base L2 migration target).
- **Deployment**: Render (Docker, current production) — GCP Cloud Run (migration target per ADR-011).

---

## 🚀 Deployment & Development

### Local Setup
```bash
git clone https://github.com/nemesistip-cloud/vit.git
pip install -r requirements.txt
cd frontend && npm install && npm run build
```

### Environment Configuration
The system uses `app/config.py` as the single source of trust for all configuration. Required keys include `JWT_SECRET_KEY`, `DATABASE_URL`, and relevant AI/Payment provider keys. See `.env.example` for the full list.

### Production
Currently deployed on **Render** (Docker). Migration to **Google Cloud Run** is planned per ADR-011. Deployment triggers automatically on push to `main` via `render.yaml`.

---

## 📊 Track Status (as of 2026-08-04)

| Phase | Tracks | Status |
|-------|--------|--------|
| Phase 1 — Core Infrastructure | TRACK-001 to 005 | ✅ Complete |
| Phase 2 — Intelligence & Storage | TRACK-006 to 009 | 🔄 Active (TRACK-007 agent scheduling, TRACK-008 Tachyon hardening) |
| Phase 3 — Financial & Legal | TRACK-010 to 013 | ✅ Complete |
| Phase 4 — Vertical Expansion | TRACK-014 to 017 | 🔄 Active (Sports Terminal, Electoral, Academy, DID) |
| Phase 5 — Distribution & Scale | TRACK-018 to 020 | 🚧 In Progress |

See [`.engineering/state/state.json`](.engineering/state/state.json) for machine-readable status and [`.engineering/roadmaps/`](.engineering/roadmaps/) for full plans.

---

## 📈 Next Phase Highlights

- **vit-explorer**: Block explorer UI for VIT Chain (TRACK-021, immediate priority).
- **vit-sdk**: TypeScript SDK for third-party developer access.
- **Base L2 Settlement**: Connect VIT Chain treasury operations to Base mainnet.
- **Multi-Validator Network**: Expand vit-chain beyond genesis validator.
- **Mobile / Telegram Mini App**: Wallet, predictions, and Academic Passport credentials.

See [`NEXT_PHASE.md`](NEXT_PHASE.md) for the full next-phase plan with verified claims.

---

*VIT Network — Verifiable Intelligence. Universal Trust.*
