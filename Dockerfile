# --- Stage 1: Build Frontend ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
COPY frontend/pnpm-lock.yaml* ./
COPY frontend/pnpm-workspace.yaml* ./
# Install pnpm if needed
RUN if [ -f "pnpm-lock.yaml" ]; then npm install -g pnpm; pnpm install --frozen-lockfile; else npm install; fi
COPY frontend/ ./
RUN if [ -f "pnpm-lock.yaml" ]; then pnpm run build; else npm run build; fi

# --- Stage 2: Python Backend ---
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     libpq-dev     curl     && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uvicorn gunicorn celery

# Copy application code
COPY . .

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PORT=8080

# Expose port (Cloud Run will override this via PORT env var)
EXPOSE 8080

# Default entrypoint (can be overridden for worker/tachyon)
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]
