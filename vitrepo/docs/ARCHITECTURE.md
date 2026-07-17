# VIT Network Architecture Overview

The VIT Network (v5.5.0) is an integrated ecosystem for AI-driven sports analytics and decentralized blockchain services. It consists of four primary layers: AI Intelligence, VIT Chain, Tachyon VESS, and the Application Layer.

## System Layers

### 1. AI Intelligence Layer (The Brain)
- **Hybrid Ensemble:** Combines ML models (XGBoost, LSTM) with the SCIE (Self-Correcting Intelligence Engine).
- **Autonomous Agents:** Independent workers for match scouting, odds anomaly detection, and news sentiment analysis.
- **Model Registry:** Manages model versions, performance weights, and lazy loading.

### 2. VIT Chain Layer (The Ledger)
- **Layer 2 (L2):** Optimized for low-latency transaction processing and on-chain prediction anchoring.
- **JSON-RPC Interface:** Standard Ethereum-compatible gateway for wallet integrations.
- **Consensus:** Proof of Storage ensures validators are actively contributing to the network's data availability.

### 3. Tachyon VESS Layer (The Storage)
- **Decentralized Swarm:** Shards data across cloud providers and edge nodes.
- **Integrity:** Reed-Solomon erasure coding and periodic storage challenges.
- **Developer API:** S3-compatible interface for unstructured data storage.

### 4. Application Layer (The Interface)
- **FastAPI Backend:** Orchestrates all services, manages custodial wallets, and serves as the API gateway.
- **React Frontend:** Professional dashboard for users, validators, and administrators.
- **SDKs:** Standalone Python and TypeScript libraries for external developers.

## Data Flow

1. **Ingestion:** IoT events and sports data feeds enter via the ETL pipeline.
2. **Analysis:** The AI Layer generates predictions and insights.
3. **Anchoring:** Critical results and storage proofs are committed to the VIT Chain.
4. **Delivery:** Users access insights via the Dashboard or API.

## Subsystem Monitoring

The platform monitors 8 critical subsystems:
- **Identity:** W3C DID and KYC status.
- **AI:** Model health and inference latency.
- **Core:** API responsiveness and database performance.
- **Database:** Transaction integrity and replication state.
- **Task:** Celery worker heartbeats and background task history.
- **Blockchain:** Block production rate and validator participation.
- **Tachyon:** Storage utilization and node availability.
- **Infrastructure:** Redis latency and system resources.
