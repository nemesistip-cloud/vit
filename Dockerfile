FROM python:3.11-slim

    # Version label aligned with APP_VERSION in app/config.py.
    # Keep these in sync: bump here when APP_VERSION changes.
    LABEL org.opencontainers.image.title="VIT Network"
    LABEL org.opencontainers.image.description="AI-powered sports intelligence platform — Python/FastAPI backend"
    LABEL org.opencontainers.image.version="1.1.0"
    LABEL org.opencontainers.image.licenses="AGPL-3.0-only"
    LABEL org.opencontainers.image.source="https://github.com/nemesistip-cloud/vit"
    LABEL org.opencontainers.image.url="https://vitnetwork-nls4.onrender.com"
    LABEL org.opencontainers.image.vendor="VIT Network"

    WORKDIR /app

    RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      g++ \
      libpq-dev \
      curl \
      && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
      && apt-get install -y --no-install-recommends nodejs \
      && rm -rf /var/lib/apt/lists/* \
      && npm install -g pnpm@9

    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt

    # frontend is a pnpm workspace member: the lockfile and workspace manifest
    # live at the repo root (pnpm-workspace.yaml), not inside frontend/.
    COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
    COPY frontend/package.json frontend/
    RUN pnpm install --frozen-lockfile

    # Inject build-time Vite env vars so the frontend bundle bakes in the correct
    # production service URLs.  Defaults match the live Render deployment.
    # Override at docker build time with --build-arg VITE_GATEWAY_URL=...
    ARG VITE_GATEWAY_URL=https://vitnetwork-nls4.onrender.com
    ARG VITE_AI_URL=https://vit-ai.onrender.com
    ARG VITE_STORAGE_URL=https://vit-storage-4trt.onrender.com
    ARG VITE_CHAIN_URL=https://vit-chain.onrender.com
    # Promote ARGs to ENV so Vite reads them from the Node.js process environment.
    ENV VITE_GATEWAY_URL=$VITE_GATEWAY_URL \
        VITE_AI_URL=$VITE_AI_URL \
        VITE_STORAGE_URL=$VITE_STORAGE_URL \
        VITE_CHAIN_URL=$VITE_CHAIN_URL

    COPY frontend/ frontend/
    RUN cd frontend && pnpm run build

    COPY explorer/package.json explorer/package-lock.json* explorer/
    RUN cd explorer && npm install

    COPY explorer/ explorer/
    RUN cd explorer && npm run build

    COPY . .

    ENV PORT=8000
    ENV ENVIRONMENT=production
    ENV PYTHONUNBUFFERED=1
    ENV PYTHONPATH=".:$PYTHONPATH"

    EXPOSE 8000

    CMD ["bash", "scripts/start_production.sh"]
    