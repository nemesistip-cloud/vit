FROM python:3.11-slim

LABEL org.opencontainers.image.title="VIT Network"
LABEL org.opencontainers.image.description="AI-powered sports intelligence platform — Python/FastAPI backend"
LABEL org.opencontainers.image.version="5.5.0"
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

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/
RUN cd frontend && pnpm install --frozen-lockfile

COPY frontend/ frontend/
RUN cd frontend && pnpm run build

COPY . .

ENV PORT=8080
ENV ENVIRONMENT=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=".:$PYTHONPATH"

EXPOSE 8080

CMD ["bash", "scripts/start_production.sh"]
