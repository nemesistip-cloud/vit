#!/usr/bin/env bash
set -euo pipefail

if [ -z "${GH_TOKEN:-}" ]; then
  echo "Error: GH_TOKEN environment variable is not set." >&2
  echo "Set it with your GitHub personal access token before running this script." >&2
  exit 1
fi

BRANCH="${1:-main}"

ORIGIN_URL="$(git remote get-url origin)"
AUTHENTICATED_URL="$(echo "${ORIGIN_URL}" | sed 's|https://|https://'"${GH_TOKEN}"'@|')"

echo "Pushing branch '${BRANCH}' to GitHub..."
git push "${AUTHENTICATED_URL}" "${BRANCH}:${BRANCH}"
echo "Done. Branch '${BRANCH}' is now in sync with GitHub."
