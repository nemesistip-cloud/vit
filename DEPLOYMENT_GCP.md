# VIT Network: Google Cloud Platform Deployment Guide

This guide provides instructions for deploying the VIT Network to Google Cloud Platform using Cloud Run, Cloud SQL, and Secret Manager.

## Architecture Overview

- **VIT API**: Main backend service (FastAPI) running on Cloud Run.
- **VIT Worker**: Celery background worker running on Cloud Run (configured with a non-terminating command).
- **VIT Tachyon**: Coordination service running on Cloud Run.
- **Database**: Managed PostgreSQL on Cloud SQL.
- **Cache/Queue**: Managed Redis on Memorystore.
- **Storage**: Cloud Storage for media and ML models.
- **Secrets**: Google Secret Manager.

## 1. Prerequisites

- Google Cloud Project with billing enabled.
- Google Cloud SDK (\`gcloud\`) installed and authenticated.
- Enable necessary APIs:
  \`\`\`bash
  gcloud services enable run.googleapis.com \
                         sqladmin.googleapis.com \
                         secretmanager.googleapis.com \
                         artifactregistry.googleapis.com \
                         cloudbuild.googleapis.com \
                         vpcaccess.googleapis.com \
                         redis.googleapis.com
  \`\`\`

## 2. Infrastructure Setup

### Cloud SQL (PostgreSQL)
1. Create a Cloud SQL instance:
   \`\`\`bash
   gcloud sql instances create vit-postgres \
       --database-version=POSTGRES_15 \
       --tier=db-f1-micro \
       --region=us-central1
   \`\`\`
2. Set the database password and create the database \`vit_db\`.

### Secret Manager
Store critical secrets:
- \`DATABASE_URL\` (Postgres connection string)
- \`REDIS_URL\` (Redis connection string)
- \`JWT_SECRET_KEY\`
- AI API keys (OpenAI, Gemini, etc.)

**Important: Permissions**
The Cloud Run service account must have the \`Secret Manager Secret Accessor\` role to access these secrets. You can grant this using the provided script:
\`\`\`bash
./scripts/fix_gcp_permissions.sh
\`\`\`
Or manually:
\`\`\`bash
gcloud projects add-iam-policy-binding "[PROJECT_ID]" \
    --member="serviceAccount:[SERVICE_ACCOUNT_EMAIL]" \
    --role="roles/secretmanager.secretAccessor"
\`\`\`

### Artifact Registry
Create a repository for Docker images:
\`\`\`bash
gcloud artifacts repositories create vit-repo \
    --repository-format=docker \
    --location=us-central1
\`\`\`

## 3. Automated Deployment (Cloud Build)

The project includes a \`cloudbuild.yaml\` file. You can trigger a build and deploy manually:
\`\`\`bash
gcloud builds submit --config cloudbuild.yaml .
\`\`\`

## 4. GitHub Actions Integration

The repository is configured with a GitHub Actions workflow (\`.github/workflows/deploy.yml\`).
To enable it:
1. Create a Service Account with \`Cloud Build Editor\`, \`Cloud Run Admin\`, and \`Storage Admin\` roles.
2. Download the JSON key and add it as a GitHub Secret named \`GCP_SA_KEY\`.

## 5. Environment Variables

Ensure the following environment variables are set in Cloud Run:
- \`ENVIRONMENT=production\`
- \`DATABASE_URL\` (Reference from Secret Manager)
- \`JWT_SECRET_KEY\` (Reference from Secret Manager)
- \`REDIS_URL\` (Optional, for Celery/Rate limiting)

## 6. Troubleshooting

- **Permission Denied on Secret**: If deployment fails with a secret access error, ensure the Cloud Run service account has the \`roles/secretmanager.secretAccessor\` role.
- **Health Checks**: VIT API exposes \`/health\` and \`/readiness\`.
- **Logs**: View logs in the Google Cloud Console under Cloud Run -> [Service Name] -> Logs.
- **Database Migrations**: Initial schema setup is performed automatically on startup by \`main.py\`.
