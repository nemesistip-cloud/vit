# Failure Analysis Report

## 1. Subsystem Failure Impact & Recovery

| Subsystem | Failure Impact | Recovery Procedure | Fallback Strategy |
| :--- | :--- | :--- | :--- |
| **API Gateway** | Total System Outage | Auto-restart (Cloud Run) | Status page + Load balancer redirect |
| **Database** | Read/Write Outage | Cloud SQL Failover (HA) | Read-only mode (if replica available) |
| **Redis** | Task/Cache Failure | Memorystore Auto-restart | Local in-process caching (fallback) |
| **AI Inference**| Intelligence Gaps | Model Registry Reload | Deterministic/Historical insights |
| **Tachyon Swarm**| Storage Gaps | Shard Reconstruction | Cloud Storage backup (mirrored) |
| **Base L2 RPC** | Settlement Delay | Switch to Secondary RPC | Queue transactions in Task System |

## 2. Graceful Degradation
- **Level 1 (Degraded AI)**: Ensemble falls back to a single baseline model if heavy models time out.
- **Level 2 (No Notifications)**: System continues to operate; alerts are queued until service (Telegram/Resend) returns.
- **Level 3 (Read-Only)**: Database locks or high latency trigger a UI banner and disable mutating actions.

## 3. Monitoring & Alerts
- **Alert Thresholds**:
  - API Error Rate > 1% (5m)
  - DB Connections > 80%
  - Shard Availability < 75%
- **Heartbeat**: 45s self-ping (`ping_service_loop`) monitors platform availability.
