#!/usr/bin/env bash
# This script grants the necessary permissions to the Cloud Run service account
# to access secrets in Secret Manager.

PROJECT_ID=$(gcloud config get-value project)

# Use the service account from the error message as default, or allow override
DEFAULT_SA="firebase-adminsdk-fbsvc@$PROJECT_ID.iam.gserviceaccount.com"
SERVICE_ACCOUNT="${1:-$DEFAULT_SA}"

echo "Project ID: $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT"
echo "Granting Secret Manager Secret Accessor role..."

# Grant access to the project so the service account can read any secret
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

echo "----------------------------------------------------------------"
echo "Permissions granted. If you still see errors, ensure that:"
echo "1. The secret 'JWT_SECRET_KEY' exists in Secret Manager."
echo "2. The Cloud Run service is actually using $SERVICE_ACCOUNT."
echo "----------------------------------------------------------------"
