#!/usr/bin/env bash
# Build-phase script: installs Python deps, frontend deps, and builds the bundle.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[build] Installing Python dependencies..."
pip install --quiet \
  aiohttp aiosqlite alembic asyncpg "bcrypt==5.0.0" beautifulsoup4 \
  celery cryptography "email-validator>=2.0" "fastapi==0.115.6" \
  firebase-admin fpdf2 greenlet gunicorn httpx itsdangerous joblib \
  lxml numpy pandas passlib pillow psutil psycopg2-binary \
  pydantic pydantic-settings pyotp python-dotenv "python-jose[cryptography]" \
  python-multipart qrcode redis reportlab scikit-learn scipy \
  "SQLAlchemy[asyncio]" starlette stripe tenacity \
  "uvicorn[standard]" xgboost \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  "torch==2.2.2+cpu" 2>&1 | tail -5

echo "[build] Installing frontend dependencies..."
cd frontend
npm install --prefer-offline --silent 2>/dev/null || npm install

echo "[build] Building frontend..."
npm run build
echo "[build] Done — frontend bundle written to frontend/dist"
