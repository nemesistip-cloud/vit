# Dependency Certification Report

## 1. Overview
This report certifies the dependency model of the VIT ecosystem. The architecture follows a strict hierarchical model designed to prevent circular dependencies and ensure high availability of critical paths.

## 2. Dependency Classification

| Dependency | Category | Criticality | Type |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | Mandatory | Critical | Synchronous / Startup |
| **Redis** | Mandatory | Critical | Synchronous / Runtime |
| **GCP Secret Manager** | Mandatory | Critical | Synchronous / Startup |
| **iSports API** | Mandatory | High | Asynchronous / Runtime |
| **Base L2 RPC** | Mandatory | High | Asynchronous / Runtime |
| **Tachyon Swarm** | Optional | Medium | Asynchronous / Runtime |
| **Telegram Bot API** | Optional | Low | Asynchronous / Runtime |
| **Resend Email API** | Optional | Low | Asynchronous / Runtime |

## 3. Circular Dependency Audit
- **Status**: ✅ No circular dependencies detected in core domain modules.
- **Verification**:
  - `Identity` -> `Database`
  - `AI` -> `Database`, `Secrets`
  - `Wallet` -> `Database`, `Redis`
  - `Blockchain` -> `Database`, `Base L2`
- **Improvement**: Domain modules MUST communicate via `EventCatalogue.md` events rather than direct cross-module imports to maintain decoupling.

## 4. Lifecycle Dependencies

### Startup Sequence (Priority 0-1)
1. Secret Loader (Infrastructure)
2. Database Connectivity (Database)
3. Redis Connectivity (Infrastructure)
4. AI Model Registry (AI)
5. API Gateway (Core)

### Runtime Dependencies
- **Critical Path**: API Gateway -> DB -> Redis.
- **Intelligence Path**: API -> AI Inference -> DB.
- **Settlement Path**: Task System -> Oracle Bridge -> Base L2.

## 5. Certification Result
**Platform is certified as having a stable and decoupled dependency model.**
