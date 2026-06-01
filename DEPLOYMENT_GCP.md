# VIT — Google Cloud Deployment Guide

This guide covers the production deployment of VIT on Google Cloud Platform.

## Architecture

- **Compute**: Cloud Run (API + Frontend) & Cloud Run Worker (Background Tasks)
- **Database**: Cloud SQL (PostgreSQL 15)
- **Cache**: Memorystore (Redis 7)
- **CI/CD**: Cloud Build & GitHub Actions
- **Security**: Secret Manager

## Deployment Steps

### 1. Project Setup
Enable required APIs and bootstrap service accounts:
```bash
bash infrastructure/scripts/bootstrap.sh
```

### 2. Infrastructure
Apply Terraform configurations:
```bash
cd infrastructure/terraform
terraform apply
```

### 3. CI/CD Integration
Connect your GitHub repository to Cloud Build to enable automatic deployments on push to `main`.

## Environment Variables
Ensure all required secrets are populated in Secret Manager:
- `JWT_SECRET_KEY`
- `DATABASE_URL`
- `FOOTBALL_DATA_API_KEY`
- `STRIPE_SECRET_KEY`

---
For troubleshooting, see the [README.md](README.md) or check the Cloud Run logs.
