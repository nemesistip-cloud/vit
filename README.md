# VIT Network (v5.5.0)
### AI Intelligence Oracle & Blockchain Super App

VIT Network is an institutional-grade intelligence layer providing verifiable, high-confidence insights across multiple verticals including sports, electoral sentiment, and macroeconomic policy. The ecosystem leverages a 13-model AI ensemble, autonomous agent coordination, and Base L2 blockchain settlement to deliver a transparent and decentralised intelligence marketplace.

---

## 🏗️ System Architecture

- **Intelligence Layer**: 13-model ML ensemble (LSTM, XGBoost, Transformers) with autonomous re-weighting.
- **Agentic Swarm**: 22 specialised agents for live-data ingestion, anomaly detection, and risk assessment.
- **Financial Rails**: Multi-currency wallet (USD, NGN, USDT, VITCoin) with Paystack and Stripe integration.
- **Blockchain Layer**: Base L2 (chain_id 8453) for verifiable on-chain credentials, staking, and settlement.
- **Tachyon Fabric**: Parallelized swarm storage coordination with Reed-Solomon Erasure Coding (EEC).
- **Frontend SPA**: React 19 + Vite + Tailwind CSS v4 high-performance interface.

---

## 📦 Core Deliverables

| Product | Status | Functionality |
|---------|--------|---------------|
| **Sports Oracle** | ✅ GA | Verifiable match predictions with CLV tracking and model accountability. |
| **Sentiment Engine** | ✅ Beta | Real-time electoral and policy sentiment analysis using native AI reasoning. |
| **Marketplace** | ✅ GA | Peer-to-peer intelligence trading with accuracy-based slashing mechanisms. |
| **Identity (DID)** | ✅ GA | W3C-compliant decentralised identity for verifiable user reputation. |
| **Tachyon Storage** | ✅ Beta | High-availability multi-cloud swarm storage coordination. |
| **Remittance** | ✅ Beta | Cross-border financial rails utilizing blockchain liquidity. |

---

## 🛠️ Technical Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Alembic.
- **Database**: PostgreSQL (Production), SQLite (Dev), Redis (Cache/Rate-limiting).
- **Machine Learning**: PyTorch, Scikit-learn, XGBoost, Statsmodels.
- **Blockchain**: Web3.py, Viem, Wagmi, WalletConnect (Base L2).
- **Deployment**: Google Cloud Run, Cloud SQL, Secret Manager, GCS.

---

## 🚀 Deployment & Development

### Local Setup
```bash
git clone https://github.com/nemesistip-cloud/vit.git
pip install -r requirements.txt
cd frontend && npm install && npm run build
```

### Environment Configuration
The system uses `app/config.py` as the single source of trust for all configuration. Required keys include `JWT_SECRET_KEY`, `DATABASE_URL`, and relevant AI/Payment provider keys.

### Production
Optimized for **Google Cloud Run**. Deployment is managed via `cloudbuild.yaml` or directly through the GCR console.

---

## 📈 Roadmap & Deliveries

- **Current (v5.2.0)**: EEC-upgraded storage, AI-powered election sentiment, and unified ecosystem identity.
- **Next Phase**: Full Base L2 migration for all treasury operations and expansion into Western & Eastern African corridors.

---

*VIT Network — Verifiable Intelligence. Universal Trust.*
