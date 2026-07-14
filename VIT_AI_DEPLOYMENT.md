# VIT AI Platform: Deployment & Environment Specification (v6.0.0)

This document provides deployment guidelines and runtime configurations for the **VIT AI Platform**.

---

## ⚙️ Environment Variables (`.env`)

Add the following environment variables to your deployment profile to enable advanced features:

```bash
# ── Vit AI microservice configuration ──
VIT_AI_URL=https://vit-ai.onrender.com
USE_REAL_ML_MODELS=true
ML_MODEL_CACHE_ENABLED=true

# ── Redis Cache Engine ──
REDIS_URL=redis://localhost:6379

# ── Circuit Breaker limits ──
VIT_AI_FAILURE_THRESHOLD=5
VIT_AI_RECOVERY_TIMEOUT=30
```

---

## 🚀 Deployment Profiles

### 1. Local Development Launch
To start the fullstack platform locally:
```bash
# 1. Install workspace dependencies
pnpm install

# 2. Build the production React frontend
pnpm --filter @workspace/vit-network-frontend build

# 3. Start the FastAPI backend server
uvicorn main:app --host 0.0.0.0 --port 10000 --reload
```

### 2. Render Deployment
The gateway backend and React frontend are bundled dynamically during startup.
- **Service Type**: Web Service
- **Build Command**: `pnpm install && pnpm --filter @workspace/vit-network-frontend build`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Google Cloud Run Deployment
For GCP configurations, refer to the root `cloudbuild.yaml` file. The server automatically starts as a Docker container.
- Ensure the Secret Manager keys are accessible by the Service Account.
