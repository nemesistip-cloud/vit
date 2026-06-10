FROM python:3.11-slim

LABEL org.opencontainers.image.title="VIT Network"
LABEL org.opencontainers.image.description="AI-powered sports intelligence platform — Python/FastAPI backend"
LABEL org.opencontainers.image.version="5.5.0"
LABEL org.opencontainers.image.licenses="AGPL-3.0-only"
LABEL org.opencontainers.image.source="https://github.com/nemesistip-cloud/vit"
LABEL org.opencontainers.image.url="https://vitnetwork.io"
LABEL org.opencontainers.image.vendor="VIT Network"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY frontend/package.json frontend/
RUN cd frontend && npm install --no-audit --no-fund

COPY frontend/ frontend/
RUN cd frontend && npm run build

COPY . .

ENV PORT=8080
ENV ENVIRONMENT=production
ENV USE_REAL_ML_MODELS=true
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["bash", "scripts/start_production.sh"]
