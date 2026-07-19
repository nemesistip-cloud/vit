# ── Stage 1: Python dependency builder ───────────────────────────────────────
    # gcc/g++ compile C extensions (psycopg2, cryptography, etc.).
    # Build tools are NOT carried into the runtime image.
    FROM python:3.11-slim AS python-builder

    RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ libpq-dev \
      && rm -rf /var/lib/apt/lists/*

    WORKDIR /build
    COPY requirements.txt .
    # --user installs into /root/.local, copied verbatim into runtime stage
    RUN pip install --no-cache-dir --user -r requirements.txt

    # ── Stage 2: Frontend builder (React + pnpm workspace) ────────────────────────
    FROM node:20-slim AS frontend-builder

    WORKDIR /build
    RUN npm install -g pnpm@9

    COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
    COPY frontend/package.json frontend/
    RUN pnpm install --frozen-lockfile

    COPY frontend/ frontend/
    RUN cd frontend && pnpm run build

    # ── Stage 3: Explorer builder ─────────────────────────────────────────────────
    FROM node:20-slim AS explorer-builder

    WORKDIR /build
    COPY explorer/package.json explorer/package-lock.json* explorer/
    RUN cd explorer && npm install --no-audit --no-fund
    COPY explorer/ explorer/
    RUN cd explorer && npm run build

    # ── Stage 4: Production runtime ───────────────────────────────────────────────
    # Slim Python only — no build tools, no Node.js.
    # Render free plan: 512 MB RAM. Multi-stage keeps the runtime image lean.
    FROM python:3.11-slim AS runtime

    LABEL org.opencontainers.image.title="VIT Network"
    LABEL org.opencontainers.image.description="AI-powered sports intelligence platform — Python/FastAPI backend"
    LABEL org.opencontainers.image.version="1.1.0"
    LABEL org.opencontainers.image.licenses="AGPL-3.0-only"
    LABEL org.opencontainers.image.source="https://github.com/nemesistip-cloud/vit"
    LABEL org.opencontainers.image.url="https://vitnetwork-nls4.onrender.com"
    LABEL org.opencontainers.image.vendor="VIT Network"

    # libpq5 is the only native runtime dep (asyncpg / psycopg2-binary)
    RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 curl \
      && rm -rf /var/lib/apt/lists/*

    WORKDIR /app

    # Python packages from builder — no pip or gcc at runtime
    COPY --from=python-builder /root/.local /root/.local

    # Application source (node_modules excluded by .dockerignore)
    COPY . .

    # Overwrite with freshly-built production artifacts
    COPY --from=frontend-builder /build/frontend/dist frontend/dist
    COPY --from=explorer-builder /build/explorer/dist explorer/dist

    ENV PATH="/root/.local/bin:$PATH"
    ENV PORT=8000
    ENV ENVIRONMENT=production
    ENV PYTHONUNBUFFERED=1
    ENV PYTHONPATH=".:$PYTHONPATH"
    # Render free plan (512 MB RAM): 1 worker prevents OOM.
    # Raise WEB_CONCURRENCY on a paid plan.
    ENV WEB_CONCURRENCY=1

    EXPOSE 8000

    CMD ["bash", "scripts/start_production.sh"]
    