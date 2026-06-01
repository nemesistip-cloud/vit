# VIT Network — Google Cloud Platform Deployment Guide

**Production URL:** https://vit-897838355273.europe-west1.run.app  
**Region:** `europe-west1` (Belgium)  
**Project type:** Pay-as-you-go

---

## Architecture

```
GitHub (main branch)
        │
        ▼  push triggers
GitHub Actions CI/CD
        │
        ├─── pytest (test suite)
        │
        └─── Cloud Build
              │
              ├─ Artifact Registry  ←── Docker image
              │   europe-west1-docker.pkg.dev/<PROJECT>/vit-repo/vit-network
              │
              ├─ Cloud Run: vit        ← FastAPI API + React frontend
              │   https://vit-897838355273.europe-west1.run.app
              │
              └─ Cloud Run: vit-worker ← Celery background agents

Cloud SQL (PostgreSQL 15)  ← persistent database (europe-west1)
Memorystore Redis 7        ← rate-limit store, task queue
Cloud Storage              ← ML models, static assets
Secret Manager             ← JWT key, DB URL, API keys
Cloud Monitoring           ← alerts, dashboards, uptime checks
Cloud Scheduler            ← CLV monitor (04:00 UTC), model accountability (*/6h)
```

---

## Quick-start: first-time setup

### Prerequisites
- `gcloud` SDK installed and authenticated as Owner of the GCP project
- Docker installed locally
- `terraform` ≥ 1.5

### Step 1 — Bootstrap GCP project

```bash
export PROJECT_ID=<your-gcp-project-id>
export REGION=europe-west1

bash infrastructure/scripts/bootstrap.sh
```

This enables all required APIs, creates the Artifact Registry repository, Terraform
state bucket, service accounts, Cloud Build trigger, and Secret Manager secrets.

### Step 2 — Populate secrets

```bash
# PostgreSQL connection string (Cloud SQL via Unix socket)
gcloud secrets versions add vit-database-url --data-file=- <<< \
  "postgresql+asyncpg://vit_app:PASSWORD@/vit_db?host=/cloudsql/${PROJECT_ID}:europe-west1:vit-postgres"

# JWT and app secret keys (generate strong random values)
openssl rand -hex 32 | gcloud secrets versions add vit-jwt-secret --data-file=-
openssl rand -hex 32 | gcloud secrets versions add vit-secret-key --data-file=-

# Redis (from Terraform output after apply)
gcloud secrets versions add vit-redis-url --data-file=- <<< "redis://REDIS_HOST:6379/0"
```

### Step 3 — Apply Terraform infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform plan -var project_id=$PROJECT_ID -var ops_email=admin@vit.network
terraform apply -var project_id=$PROJECT_ID -var ops_email=admin@vit.network
```

### Step 4 — Connect GitHub → Cloud Build

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Open the `vit-deploy-on-push` trigger → **Connect repository**
3. Authenticate with GitHub and select `nemesistip-cloud/vit`

### Step 5 — Add GitHub Actions secrets

In **nemesistip-cloud/vit → Settings → Secrets → Actions**, add:

| Secret | Value |
|--------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_SA_KEY` | JSON key for `vit-cloudbuild@<PROJECT>.iam.gserviceaccount.com` |

Generate the service account key:
```bash
gcloud iam service-accounts keys create /tmp/vit-cloudbuild-key.json \
  --iam-account=vit-cloudbuild@${PROJECT_ID}.iam.gserviceaccount.com
cat /tmp/vit-cloudbuild-key.json  # paste into GCP_SA_KEY secret
rm /tmp/vit-cloudbuild-key.json
```

### Step 6 — Deploy

Push to `main` — GitHub Actions will run tests, build the Docker image,
push to Artifact Registry, and deploy to Cloud Run automatically:

```bash
git push origin main
```

---

## Manual deploy (without GitHub Actions)

```bash
# Authenticate
gcloud auth configure-docker europe-west1-docker.pkg.dev

# Build & push
docker build -t europe-west1-docker.pkg.dev/${PROJECT_ID}/vit-repo/vit-network:latest .
docker push europe-west1-docker.pkg.dev/${PROJECT_ID}/vit-repo/vit-network:latest

# Deploy
gcloud run deploy vit \
  --image europe-west1-docker.pkg.dev/${PROJECT_ID}/vit-repo/vit-network:latest \
  --region europe-west1 \
  --allow-unauthenticated
```

Or via Cloud Build:
```bash
gcloud builds submit --config cloudbuild.yaml --project=$PROJECT_ID .
```

---

## GCP Services & estimated costs (pay-as-you-go)

| Service | Tier | Est. monthly |
|---------|------|-------------|
| Cloud Run (vit API) | 2 vCPU / 2 GiB, min-1 | ~$15–30 |
| Cloud Run (vit-worker) | 2 vCPU / 4 GiB, min-1 | ~$20–40 |
| Cloud SQL PostgreSQL 15 | db-g1-small, HA | ~$25–35 |
| Memorystore Redis 7 | 1 GiB Standard HA | ~$40 |
| Artifact Registry | Docker images | ~$1–3 |
| Cloud Storage | Assets + ML models | ~$1–5 |
| Cloud Build | Per build minute | ~$1–5 |
| Cloud Scheduler | 2 jobs | < $1 |
| Secret Manager | Secrets + accesses | < $1 |
| Cloud Monitoring | Alerts + dashboards | Free tier |
| **Total estimate** | | **~$103–160/month** |

---

## Service accounts

| Account | Purpose | Key roles |
|---------|---------|-----------|
| `vit-api@<PROJECT>.iam.gserviceaccount.com` | Cloud Run API | secretmanager.secretAccessor, cloudsql.client, storage.objectViewer |
| `vit-api-worker@<PROJECT>.iam.gserviceaccount.com` | Worker/Celery | secretmanager.secretAccessor, cloudsql.client, storage.objectAdmin |
| `vit-cloudbuild@<PROJECT>.iam.gserviceaccount.com` | CI/CD | run.admin, artifactregistry.writer, iam.serviceAccountUser |

---

## Health & monitoring

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness check — returns `{"status":"ok"}` |
| `GET /readiness` | Readiness check — verifies DB connection |
| `GET /metrics` | Prometheus metrics |

**Cloud Monitoring dashboards:**
- [Cloud Run — Request count & latency](https://console.cloud.google.com/monitoring)
- [Cloud SQL — CPU/memory/connections](https://console.cloud.google.com/sql)

**Alerts configured:**
- Error rate > 5% → email to ops
- p95 latency > 5s → email to ops

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Permission denied on secret` | Add `roles/secretmanager.secretAccessor` to `vit-api` SA |
| Cold-start latency | `min-instances 1` keeps one instance warm (already configured) |
| DB connection refused | Check Cloud SQL proxy socket path in `DATABASE_URL` secret |
| Image build fails | Run `gcloud builds submit` locally to see full build output |
| Health check fails after deploy | Check Cloud Run logs: `gcloud run services logs read vit --region europe-west1` |

**View live logs:**
```bash
gcloud run services logs tail vit --region europe-west1
```

**Connect to production DB:**
```bash
gcloud sql connect vit-postgres --user=vit_app --database=vit_db
```
