# VIT Network Ecosystem — Architecture & Roadmap

## 1. Vision
Transform VIT from a sports prediction app into a multi-vertical, Google Cloud-native ecosystem spanning Research, Education, Business, AI, and Blockchain.

## 2. Core Architecture (GCP Native)

### Compute
- **Cloud Run (vit):** Primary FastAPI/React application.
- **Cloud Run (vit-worker):** Celery agents for background tasks (scrapers, settlement, AI agents).
- **Cloud Run (vit-tachyon):** Coordination service.

### Data
- **Cloud SQL (PostgreSQL):** Relational data (Users, Identities, Matches, Transactions).
- **Memorystore (Redis):** Caching, Rate-limiting, Task Queue.
- **Cloud Storage:** ML models, Static assets, Research documents.
- **BigQuery:** Data warehouse for ecosystem-wide analytics and research datasets.

### Intelligence
- **VIT Native Ensemble (SCIE):** High-performance sports intelligence.
- **VIT Native Intelligence:** Advanced reasoning agents for Research, Education, and Governance.
- **Document AI:** Automating verification and merchant onboarding.

### Security & Identity
- **Secret Manager:** Environment secrets and API keys.
- **Google Identity Platform:** Federated login (Google, Workspace).
- **IAM:** Service-account based least-privilege access.

## 3. Implementation Roadmap

### Phase 1: Google Cloud Foundation (Standardization)
- [x] Cleanup legacy provider references.
- [ ] Centralize secret management via `app/core/secrets_loader.py` across all modules.
- [ ] Integrate Cloud Logging and Error Reporting SDKs.
- [ ] Configure Cloud Monitoring dashboards for all verticals.

### Phase 2: AI & Research Ecosystem
- [ ] Deploy Native-powered Research Agents in `app/modules/ai_core`.
- [ ] Implement MCP (Model Context Protocol) server for ecosystem interoperability.
- [ ] Create "Research Ledger" in `app/modules/academy`.

### Phase 3: Identity & Institution Ecosystem
- [ ] Expand `app/modules/identity` to support Organization/Institution accounts.
- [ ] Implement Google Workspace SSO for institutional partners.
- [ ] Federated Identity Architecture (linking Web3 DID with Web2 identities).

### Phase 4: Business & Developer Ecosystem
- [ ] Build "Business Profile" API integration in `app/modules/marketplace`.
- [ ] Merchant onboarding workflows with automated verification (Document AI).
- [ ] Developer Portal: SDK generation (TypeScript/Python) from OpenAPI specs.

## 4. Cost Estimates (Scale-to-Zero Capable)
- Development: ~$10/mo (Free tiers + minimal usage).
- Production: ~$150-300/mo (Managed DB, Redis, Reserved instances for worker).

## 5. Repository Restructuring
- `app/modules/` remains the core unit of modularity.
- `packages/` for shared SDKs and libraries.
- `infrastructure/terraform` for reproducible environment setup.
