# 02 System Blueprint

## 1. Execution Foundation (The Kernel)
- **VIT Runtime Kernel**: The single authoritative entry point for the platform. It orchestrates all subsystem lifecycles, manages dependencies, and provides runtime supervision.

## 2. System Layers

### AI Intelligence Layer (The Brain)
- **Hybrid Ensemble**: Combines ML models (XGBoost, LSTM) with the Self-Correcting Intelligence Engine (SCIE).
- **Autonomous Agents**: Independent workers for match scouting and news sentiment analysis.

### VIT Chain Layer (The Ledger)
- **Layer 2 (L2)**: Optimized for low-latency transaction processing on Base.
- **JSON-RPC Interface**: Ethereum-compatible gateway.

### Tachyon VESS Layer (The Storage)
- **Decentralized Swarm**: Shards data across cloud providers and edge nodes.
- **Integrity**: Reed-Solomon erasure coding and periodic storage challenges.

### Application Layer (The Interface)
- **FastAPI Backend**: Orchestrates services and serves as the API gateway.
- **React Frontend**: High-density "Mission Control" terminal.

## 3. Infrastructure (GCP Native)
- **Compute**: Cloud Run (API, Worker, Tachyon).
- **Data**: Cloud SQL (PostgreSQL), Memorystore (Redis), BigQuery.
- **Storage**: Cloud Storage (Models, Assets).
- **Security**: Secret Manager, Google Identity Platform.

## 4. Validator System
Validators provide human-in-the-loop verification for AI signals and participate in the Proof of Storage consensus.
