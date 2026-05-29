# VIT Sports Intelligence Network

[![Status: Production Ready](https://img.shields.io/badge/Status-Production--Ready-brightgreen)](https://render.com)
[![Version](https://img.shields.io/badge/Version-5.0.0-blue)](main.py)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Frontend-React-61DAFB)](https://reactjs.org/)

The **VIT Sports Intelligence Network** is a high-performance, AI-driven sports prediction and analytics platform. Built with a modular "Agent Swarm" architecture, it provides real-time match insights, automated bankroll management, and a decentralized governance ecosystem.

---

## 🚀 Key Features

### 🧠 Advanced AI & ML
- **Multi-Model Ensemble**: Combines XGBoost, Poisson, Dixon-Coles, and PyTorch LSTMs for market-leading accuracy.
- **VIT Brain**: Internal AI orchestration using Mistral/Ollama for natural language insights and tool-calling.
- **Predictive Markets**: Covers Soccer, Tennis, Basketball, Cricket, and American Football with markets for 1x2, Asian Handicap, Over/Under, and Correct Score.
- **RAG Memory**: Persistent vector storage (ChromaDB) for historical match context and model fine-tuning.

### 🤖 Autonomous Agent Swarm
- **Match Scout**: Real-time fixture discovery and data ingestion.
- **Performance Monitor**: Continuous tracking of model accuracy and drift.
- **News Sentinel**: Sentiment analysis on global sports news to adjust prediction weights.
- **Audit Sentinel**: Real-time fraud detection and transaction monitoring.

### 💼 Wealth & Bankroll Management
- **Kelly Criterion**: Automated stake sizing recommendations based on win probability and odds value.
- **Profit/Loss Tracking**: Detailed ROI analytics and historical performance reporting.
- **Merit System**: Rewards users for high-quality predictions and ecosystem participation.

### 🏛️ Decentralized Ecosystem
- **DAO Governance**: Token-weighted voting on platform upgrades and fee structures.
- **Trust Protocol**: On-chain verification of prediction results and model performance.
- **Cross-Chain Bridge**: Asset mobility between internal VIT network and external chains.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (Async), PostgreSQL (Render), Redis, Celery.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS, Framer Motion, Recharts.
- **ML/AI**: Scikit-learn, XGBoost, PyTorch, Sentence-Transformers, ChromaDB.
- **Infrastructure**: Docker, Gunicorn/Uvicorn, Render Cloud.

---

## 📦 Project Structure

```text
├── app/                  # Main Python package
│   ├── agents/           # Autonomous agent implementations
│   ├── api/              # FastAPI routes and middleware
│   ├── core/             # Core logic (Auth, Seeding, Orchestrator)
│   ├── db/               # Database models and migrations
│   ├── modules/          # Business logic (KYC, Wallet, DAO, etc.)
│   └── services/         # External integrations and AI clients
├── frontend/             # React application (Vite)
├── scripts/              # Build and deployment automation
├── services/             # Specialized ML and data microservices
├── tests/                # Pytest suite
└── main.py               # Application entry point
```

---

## ⚙️ Local Development

### Prerequisites
- Python 3.12+
- Node.js & pnpm
- PostgreSQL (or SQLite for local testing)
- Redis

### 1. Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your local DB and API keys

# Run database migrations
alembic upgrade head

# Start the application
gunicorn app:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. Frontend Setup
```bash
cd frontend
pnpm install
pnpm run dev
```

---

## 🚢 Deployment (Render)

1. **Build Command**: `bash scripts/build.sh`
2. **Start Command**: `bash scripts/start_production.sh`
3. **Environment Variables**:
   - `DATABASE_URL`: Your Render Postgres URL.
   - `REDIS_URL`: Your Redis instance URL.
   - `VIT_DATABASE_URL`: Same as `DATABASE_URL`.
   - `JWT_SECRET`: For authentication.

---

## 🧪 Testing

```bash
# Run backend tests
pytest tests/ -v

# Run frontend tests
cd frontend && pnpm run test
```

---

## 📜 License

Internal Use Only - VIT Sports Network © 2024.
