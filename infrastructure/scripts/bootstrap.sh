#!/usr/bin/env bash
# VIT Network — GCP Infrastructure Bootstrap
# Run once to set up the project before Terraform apply.
#
# Usage:
#   export PROJECT_ID=<your-gcp-project-id>
#   export REGION=europe-west1
#   bash infrastructure/scripts/bootstrap.sh
#
# Prerequisites: gcloud SDK installed and authenticated as Owner.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-europe-west1}"
BILLING_ACCOUNT="${BILLING_ACCOUNT:-}"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   VIT Network — GCP Infrastructure Bootstrap    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Project : $PROJECT_ID"
echo "  Region  : $REGION"
echo ""

# ── 0. Link billing (if provided) ────────────────────────────────────────────
if [ -n "$BILLING_ACCOUNT" ]; then
  echo "▶ Linking billing account..."
  gcloud billing projects link "$PROJECT_ID" --billing-account="$BILLING_ACCOUNT"
fi

# ── 1. Enable APIs ────────────────────────────────────────────────────────────
echo "▶ Enabling required GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  vpcaccess.googleapis.com \
  redis.googleapis.com \
  cloudscheduler.googleapis.com \
  iam.googleapis.com \
  compute.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudtrace.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT_ID"

# ── 2. Artifact Registry ──────────────────────────────────────────────────────
echo "▶ Creating Artifact Registry repository..."
gcloud artifacts repositories create vit-repo \
  --repository-format=docker \
  --location="$REGION" \
  --description="VIT Network Docker images" \
  --project="$PROJECT_ID" 2>/dev/null || echo "  (already exists)"

# ── 3. Terraform state bucket ─────────────────────────────────────────────────
echo "▶ Creating Terraform state bucket..."
gcloud storage buckets create "gs://vit-terraform-state" \
  --location="$REGION" \
  --uniform-bucket-level-access \
  --project="$PROJECT_ID" 2>/dev/null || echo "  (already exists)"

gcloud storage buckets update "gs://vit-terraform-state" \
  --versioning \
  --project="$PROJECT_ID"

# ── 4. Service accounts ───────────────────────────────────────────────────────
echo "▶ Creating service accounts..."
for SA in "vit-api" "vit-api-worker" "vit-cloudbuild"; do
  gcloud iam service-accounts create "$SA" \
    --display-name="VIT ${SA} Service Account" \
    --project="$PROJECT_ID" 2>/dev/null || echo "  $SA already exists"
done

# ── 5. Cloud Build trigger ────────────────────────────────────────────────────
echo "▶ Creating Cloud Build trigger (GitHub → main)..."
gcloud builds triggers create github \
  --name="vit-deploy-on-push" \
  --repo-name="vit" \
  --repo-owner="nemesistip-cloud" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --service-account="projects/$PROJECT_ID/serviceAccounts/vit-cloudbuild@$PROJECT_ID.iam.gserviceaccount.com" \
  --project="$PROJECT_ID" 2>/dev/null || echo "  Trigger already exists or needs manual GitHub connection"

# ── 6. Initial secrets (placeholder values) ──────────────────────────────────
echo "▶ Creating Secret Manager secrets (placeholder — update values manually)..."
for SECRET in vit-jwt-secret vit-secret-key vit-database-url vit-redis-url vit-admin-password; do
  echo -n "PLACEHOLDER-change-me-$(date +%s)" | \
    gcloud secrets create "$SECRET" \
      --data-file=- \
      --project="$PROJECT_ID" 2>/dev/null || echo "  $SECRET already exists"
done

# ── 7. Print next steps ───────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Bootstrap complete — next steps:              ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  1. Update Secret Manager values:"
echo "     gcloud secrets versions add vit-jwt-secret --data-file=- <<< 'your-jwt-secret'"
echo "     gcloud secrets versions add vit-secret-key --data-file=- <<< 'your-secret-key'"
echo "     gcloud secrets versions add vit-database-url --data-file=- <<< 'postgresql+asyncpg://vit_app:PASSWORD@/vit_db?host=/cloudsql/PROJECT:REGION:vit-postgres'"
echo "     gcloud secrets versions add vit-redis-url --data-file=- <<< 'redis://REDIS_HOST:6379/0'"
echo ""
echo "  2. Run Terraform:"
echo "     cd infrastructure/terraform"
echo "     terraform init"
echo "     terraform plan -var project_id=$PROJECT_ID"
echo "     terraform apply -var project_id=$PROJECT_ID"
echo ""
echo "  3. Connect GitHub repo to Cloud Build trigger in Console:"
echo "     https://console.cloud.google.com/cloud-build/triggers"
echo ""
echo "  4. Push to main to trigger first deployment:"
echo "     git push origin main"
echo ""
echo "  5. Verify at: https://vit-897838355273.europe-west1.run.app/health"
echo ""
