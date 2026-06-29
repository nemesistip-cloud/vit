# 07 Performance Standards

## 1. Latency Targets
- **API Response**: < 200ms for 95th percentile.
- **AI Inference**: < 2s for standard agents.
- **Tachyon Retrieval**: < 500ms for sharded data.

## 2. Resource Management
- **Scale-to-Zero**: Application must be compatible with Cloud Run's scale-to-zero model.
- **Memory Optimization**: Backend must operate within a 512MB RAM constraint where possible.
- **Lazy Loading**: AI models must be lazily loaded to conserve memory during startup.

## 3. Scalability
- System must support horizontal scaling of workers.
- Redis caching must be used to minimize database load for high-frequency reads.
