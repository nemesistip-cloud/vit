# VIT Deployment Status Audit

**Date**: 2026-07-08
**Type**: Infrastructure & Pipeline Verification

## 1. Environment Inventory

| Provider | Purpose | Status | Region | Scale |
| :--- | :--- | :---: | :--- | :--- |
| **Render** | Main Web Service | **Broken** | Ohio (US) | Free Tier (1 Instance) |
| **Render** | Redis Cache | **Healthy** | Ohio (US) | Free Tier |
| **Render** | Postgres DB | **Healthy** | Ohio (US) | Free Tier |
| **Google Cloud Run** | API Gateway | **Inactive** | europe-west1 | Managed (1-10 Instances) |
| **Google Cloud Run** | Background Worker| **Inactive** | europe-west1 | Managed (1-3 Instances) |
| **Artifact Registry**| Docker Images | **Active** | europe-west1 | N/A |

## 2. Pipeline Verification

### A. Render Workflow (`render-deploy.yml`)
- **Trigger**: Automated on every push to `main`.
- **Observation**: Recent deployments are failing due to the Kernel initialization regression (`AttributeError`).

### B. GCP Workflow (`cloudbuild.yaml`)
- **Complexity**: High (Multi-step build, push, migrate, deploy API, deploy Worker).
- **Health Check**: Uses `curl -sf /health` to verify the deployment.
- **Status**: Manual trigger/Active.

## 3. Docker Configuration

- **Base Image**: `python:3.11-slim` with Node.js 20 installed.
- **Labels**: Synchronized with version `5.5.0`.
- **Health Checks**: `main.py` exposes `/ping` (used by Render) and `/health` (used by GCP).

## 4. Configuration Health

- **Environment Variables**: Managed via `render.yaml` and GCP Secret Manager.
- **Database Migrations**: Handled as a GCP Cloud Run job (`vit-migrate`) in the pipeline.
- **Secrets Drift**: Multiple API keys (Football Data, Odds, Paystack) are marked `sync: false` in `render.yaml`, requiring manual entry in the dashboard.

## 5. Critical Deployment Gaps

1. **Boot Crash**: The current codebase cannot boot in production due to the `get_subsystem` regression.
2. **Frontend Deployment**: No evidence of a dedicated CDN or Static Site deployment for the frontend; it is likely served as static files by the Python backend in the current Docker configuration.
3. **Regional Mismatch**: Render is configured for `ohio`, while GCP is configured for `europe-west1`. This may lead to latency issues for cross-cloud components.

---
**Confidence Level**: High (Verified via `render.yaml`, `cloudbuild.yaml`, and `Dockerfile`).
