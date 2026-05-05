#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../frontend"
npm install
exec npm run dev -- --host 0.0.0.0 --port "${PORT:-5000}"
