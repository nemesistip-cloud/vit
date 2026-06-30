# 20 Master Dependency Map

## 1. System Classification

### Core Services (Critical)
- **VIT Runtime Kernel**: The foundational execution and orchestration layer.
- **FastAPI Application**: The central orchestrator and API Gateway.
- **PostgreSQL (Cloud SQL)**: Primary relational data store.
- **Redis (Memorystore)**: Distributed cache and task broker.

### Infrastructure Services (Critical)
- **GCP IAM & Secret Manager**: Security and identity foundation.
- **Cloud Run**: Serverless compute environment.
- **Tachyon VESS Swarm**: Decentralized storage backbone.

### Domain Modules
- **Identity**: Auth, KYC, and DID logic.
- **AI**: Models, inference, and agent reasoning.
- **Blockchain**: Wallet, treasury, and L2 settlement.
- **Sports**: Fixture sync, market mapping, and settlement.
- **Task**: Background job processing (Celery/Workers).

### External Integrations
- **Base L2**: Primary settlement chain.
- **Sports Providers**: iSports, Football-Data.org, TheSportsDB.
- **Payment Gateways**: Paystack, Flutterwave, Pi Network.
- **Communications**: Resend (Email), Telegram (Alerts).

## 2. Dependency Model

| Module | Dependencies | Dependents | Startup Priority | Failure Impact | Health Requirements |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **VIT Runtime Kernel** | Infrastructure, Secrets | All Modules | 0 (Foundational) | Total System Outage | Config Loaded, Secrets Active |
| **API Gateway (Core)** | Kernel, DB, Redis | Frontend, Tachyon | 1 (Primary) | Total System Outage | DB Connected, Redis Ping |
| **Database** | Infrastructure | API, AI, Tachyon | 0 (Foundational) | Total System Outage | Connectivity, < 100ms Latency |
| **Redis** | Infrastructure | API, Task System | 0 (Foundational) | Degraded Performance | Connectivity |
| **AI Module** | Kernel, API, Secrets | Core (Sports/Niche) | 2 | Intelligence Gaps | Model Loaded, GPU/CPU Ready |
| **Tachyon Swarm** | Kernel, API, DB | Blockchain, AI | 3 | Storage Loss | > 50% Shard Availability |
| **Blockchain** | Kernel, API, Base L2 | Wallet, Core | 3 | Settlement Delay | RPC Endpoint Active |
| **Task System** | Kernel, Redis, API | All Domains | 2 | Async Failures | Worker Alive, Queue Depth < 1k |
| **Frontend** | API Gateway | Users | 4 | User Unreachable | App Loaded, Gateway 200 OK |

## 3. Dependency Rules
1. **Unidirectional Flow**: High-level modules (Frontend) MUST NOT be depended on by low-level modules (Core).
2. **Circular Prevention**: Domain modules SHOULD NOT have circular dependencies. Use events or contracts to decouple.
3. **Graceful Degradation**: Optional integrations (e.g., Telegram) MUST NOT block the startup or operation of Core services.
4. **Contractual Binding**: All cross-domain dependencies MUST be defined in `contracts.json`.
