#!/usr/bin/env bash
set -euo pipefail

# Usage: RENDER_API_KEY=... ./scripts/render_deploy_api.sh [service-name]
# If service-name is not provided, defaults to the name in render.yaml (vit-sports-intelligence)

SERVICE_NAME="${1:-vit-sports-intelligence}"
API_KEY="${RENDER_API_KEY:-}"

if [ -z "$API_KEY" ]; then
    echo "Error: RENDER_API_KEY environment variable is required." >&2
    echo "Set it and re-run: export RENDER_API_KEY=\"<key>\"" >&2
    exit 1
fi

echo "Looking up Render service ID for '$SERVICE_NAME'..."
SERVICE_JSON=$(curl -sSf -H "Authorization: Bearer $API_KEY" "https://api.render.com/v1/services" )
SERVICE_ID=$(echo "$SERVICE_JSON" | jq -r --arg NAME "$SERVICE_NAME" 'map(select(.name == $NAME) | .id) + map(select(.service.name == $NAME) | .service.id) | .[0] // empty')

if [ -z "$SERVICE_ID" ]; then
    echo "Error: service named '$SERVICE_NAME' not found in Render account." >&2
    echo "Available services:" >&2
    echo "$SERVICE_JSON" | jq -r '.[] | if has("name") then "- " + .name + " (" + .id + ")" else "- " + .service.name + " (" + .service.id + ")" end'
    exit 2
fi

echo "Found service ID: $SERVICE_ID — creating a new deploy..."
DEPLOY_RESP=$(curl -sSf -X POST "https://api.render.com/v1/services/$SERVICE_ID/deploys" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{}')

DEPLOY_ID=$(echo "$DEPLOY_RESP" | jq -r '.id')
DEPLOY_URL="https://dashboard.render.com/web/$SERVICE_ID/deploys/$DEPLOY_ID"

echo "Triggered deploy: $DEPLOY_ID"
echo "View deploy in Render dashboard: $DEPLOY_URL"

echo "Checking deploy status..."
DEPLOY_STATUS=$(curl -sSf -H "Authorization: Bearer $API_KEY" "https://api.render.com/v1/services/$SERVICE_ID/deploys/$DEPLOY_ID")
STATUS=$(echo "$DEPLOY_STATUS" | jq -r '.status // .state // "unknown"')
COMMIT_MSG=$(echo "$DEPLOY_STATUS" | jq -r '.commit.message // ""')

echo "Deploy status: $STATUS"
if [ -n "$COMMIT_MSG" ]; then
    echo "Commit: $COMMIT_MSG"
fi

echo "Full deploy details:"
echo "$DEPLOY_STATUS" | jq -r '{id, status, trigger, createdAt, startedAt, updatedAt, commit}'

echo "Done. Check the dashboard for live status." 
