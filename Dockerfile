FROM python:3.11-slim

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

COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm ci --prefer-offline --no-audit --no-fund

COPY frontend/ frontend/
RUN cd frontend && npm run build

COPY . .

ENV PORT=8080
ENV ENVIRONMENT=production
ENV USE_REAL_ML_MODELS=true
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["bash", "scripts/start_production.sh"]
