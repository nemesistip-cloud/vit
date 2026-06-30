# 07 Performance Standards

## 1. Latency Targets (p99)
- **Standard API Response**: < 200ms.
- **Critical Path (Auth/Wallet)**: < 150ms.
- **AI Inference**: < 2s for standard agents; < 5s for complex reasoning.
- **Tachyon Retrieval**: < 500ms for sharded data.
- **Database Query**: Individual query execution time MUST be < 50ms.

## 2. Resource Management
- **Scale-to-Zero**: Application MUST be compatible with Cloud Run's scale-to-zero model (statelessness).
- **Memory Optimization**: Backend MUST operate within a 512MB RAM constraint where possible.
- **Lazy Loading**: AI models MUST be lazily loaded to conserve memory during startup.
- **Connection Pooling**: Use `AsyncSessionLocal` with a pool size of 20 (max 50) to prevent DB exhaustion.

## 3. Scalability
- **Horizontal Scaling**: All services MUST support horizontal scaling without shared local state.
- **Caching**:
  - Hot data (e.g., active match odds) MUST be cached in Redis with a TTL < 60s.
  - Global configuration MUST be cached in-process with a TTL of 300s.
