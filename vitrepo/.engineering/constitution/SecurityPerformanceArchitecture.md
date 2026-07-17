# Security & Performance Architecture

## 1. Security Architecture

### Trust Boundaries
- **External**: Public Internet -> Cloud Run HTTPS (TLS 1.3).
- **Internal**: Cloud Run -> Cloud SQL / Memorystore (VPC Peering + IAM).
- **Storage**: Sharded data (Tachyon) encrypted via AES-256-GCM.

### Identity & Access
- **Authentication**: JWT (Access/Refresh) via Social OAuth (Google/Telegram).
- **Authorization**: Role-Based Access Control (RBAC) with specific admin roles.
- **Secrets Management**: GCP Secret Manager with restricted IAM access.

### Threat Model
- **DDoS**: Mitigation via Cloud Armor / Load Balancer.
- **Injection**: Pydantic validation + SQLAlchemy ORM parameterized queries.
- **Session Hijacking**: Secure HttpOnly cookies + Blocklist revokation.

## 2. Performance Architecture

### Critical Path Optimization
- **Caching**: Redis for hot data (Odds, active predictions).
- **Lazy Loading**: AI models loaded on-demand with a memory budget (400MB).
- **Asynchronous Tasks**: Payouts and Telegram alerts handled by Celery/Redis.

### Latency Targets (Constitution v1.1 Alignment)
- **p99 Standard API**: < 200ms.
- **p99 DB Query**: < 50ms.
- **Scaling Strategy**: Cloud Run horizontal autoscaling (0 to N instances).
