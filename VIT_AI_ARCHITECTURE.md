# VIT AI: Platform Architecture (v6.0.0)

This document details the software engineering and design patterns behind the **VIT AI Platform Integration**.

---

## 🏛️ Multi-Layer System Design

The architecture is divided into three distinct operational layers:

```
+─────────────────────────────────────────────────────────────+
|                     1. React SPA UI                         |
|      Overview HUD  |  Playground  |  Chat  |  Admin Panel   |
+──────────────────────────────┬──────────────────────────────+
                               │ HTTP / WebSocket
                               ▼
+─────────────────────────────────────────────────────────────+
|                  2. Central Platform Gateway                |
|      AI Gateway  |  Model Registry  |  Copilot Controllers  |
+──────────────────────────────┬──────────────────────────────+
                               │ HTTP / GCS / S3
                               ▼
+─────────────────────────────────────────────────────────────+
|               3. VIT AI Microservice Engine                 |
|     13-Model ML Ensemble  |  Tachyon Distributed Storage    |
+─────────────────────────────────────────────────────────────+
```

### 1. Presentation Layer (React 18 SPA)
The frontend serves as an institutional Dashboard. It utilizes **React Query (v5)** for resilient live polling and synchronizes metadata instantly. It exposes distinct tabs:
- **Status & Models**: Visualizes live telemetry (Memory, CPU, GPU, Cache hit ratios) and standardizes parsing across flat model list payloads.
- **Playground**: Allows developers to adjust temperature, token limits, and system roles with full streaming response emulation.
- **Chat & Copilot**: Combines conversational context with specialized blockchain/transaction utility parsers.
- **Admin Center**: Grants control over ensemble weights, hot toggles, and cache flushes.

### 2. Coordination Layer (Platform Gateway)
Located inside the backend API codebase:
- **`app/services/vit_ai_client.py`**: Controls outbound connections to the `vit-ai` microservice. Employs connection pools (`httpx.AsyncClient`), exp-backoff retries, local Redis caching, and circuit-breaker switches.
- **`app/modules/ai/gateway.py`**: Directs traffic across several strategies:
  - `Fastest`: Chooses local direct model instances.
  - `Cheapest`: Maximizes local prediction routines.
  - `Highest Accuracy`: Routes to LLM Consensus microservices.
  - `Ensemble`: Parallelized vote aggregation.

### 3. Execution Layer (Inference Engine)
Consists of the 13 specialized algorithmic and transformer models (e.g. `xgb_v2`, `lstm_v2`, `llm_consensus_v1`).

---

## ⚡ Performance Optimization
- **Redis Output Caching**: Repeat queries or identical matching context are hashed and saved under `vit:ai:cache:*` with a 5-minute TTL.
- **Async Execution**: I/O tasks are non-blocking and fully awaited to prevent Postgres pool starvation.
- **Connection Pools**: Kept alive globally with a keepalive of 50 connections to eliminate handshake overheads.
