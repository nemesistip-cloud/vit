# VIT Network — Next Phase Plan
**Date:** 2026-08-04  
**Current Version:** v5.5.0  
**Status baseline:** Live API probes + full GitHub audit

---

## Ecosystem Reality Check

### ✅ Verified Live (Aug 4, 2026)

| Service | Endpoint | Verified Fact |
|---------|----------|---------------|
| VIT Network main app | `vitnetwork-nls4.onrender.com` | `/ping → {status: ok}`, React SPA served |
| vit-ai | `vit-ai.onrender.com` | `models_loaded: 13`, HMAC auth, Redis persistence |
| vit-chain | `vit-chain.onrender.com` | Block height 1845+, Chain ID 7764, 15s epochs |
| vit-storage | `vit-storage-4trt.onrender.com` | `quantum_stable`, 4 active providers |

### ⚠️ Claims Requiring Correction

| Claim | Reality | Fix |
|-------|---------|-----|
| "Base L2 (chain_id 8453)" in README | Running custom VIT Chain (ID 7764). Base L2 is a **future** settlement target | README updated ✅ |
| "Identity (DID) ✅ GA" | TRACK-020 is ACTIVE, not complete | Updated to Beta ✅ |
| "22 specialised agents" active | `agents: null` in health — APScheduler wired 2026-08-04, needs verification | Monitor post-deploy |
| "Google Cloud Run" deployment | Currently on Render Docker (free tier). GCR is the migration target per ADR-011 | README updated ✅ |
| `storage_proofs: []` in all blocks | Proof-of-Storage challenges not producing on-chain storage proofs yet | TRACK-022 |
| `consensus_votes: []` in all blocks | Single genesis validator — no voting quorum exists yet | TRACK-021a |

### 🚧 Repos Scaffolded But Unimplemented

These GitHub repos exist with descriptions but contain no real code (no language detected):

- `vitnetwork/vit-explorer` — Block explorer UI
- `vitnetwork/vit-sdk` — TypeScript/JS SDK  
- `vitnetwork/vit-governance` — DAO tooling
- `vitnetwork/vit-prophecy` — Long-range forecasting engine
- `vitnetwork/vit-agents` — Agent swarm (22 agents)
- `vitnetwork/vit-docs` — Developer documentation site

---

## Next Phase: Active Tracks

### 🔴 Critical — Complete These First

#### TRACK-007: Agent Workflow Manager
- **Gap**: APScheduler wired on 2026-08-04. Verify 22 agents are scheduled and running.
- **Success metric**: `/health` returns `agents: {active: 22, scheduled: true}` (not null).
- **Owner**: AI System

#### TRACK-008: Tachyon Swarm Hardening
- **Gap**: Redis not configured on `vit-storage`. No cross-restart session continuity.
- **Gap**: Periodic storage challenges not yet triggering (storage_proofs empty in vit-chain blocks).
- **Actions**:
  1. Add `REDIS_URL` to vit-storage Render env
  2. Implement challenge broadcast from vit-storage → vit-chain
  3. Validate EEC reconstruction end-to-end
- **Owner**: Tachyon System

#### TRACK-020: DID v1
- **Gap**: Claimed GA in old README but TRACK-020 still ACTIVE.
- **Actions**: Complete W3C DID document generation, credential NFT issuance, and Academic Passport flow.
- **Success metric**: User can register, receive DID, and mint a credential NFT on vit-chain.
- **Owner**: Identity System

---

### 🟡 High Priority — Next 30 Days

#### TRACK-021a: Multi-Validator Expansion ✅ SHIPPED 2026-08-04
- **Built**: `POST /api/validators/register` — open registration on testnet; signature-enforced on mainnet. Returns node_id, stake, bootstrap peer hint.
- **To add a second validator**: generate a new key pair → derive 0x address → POST to `/api/validators/register` → deploy a second vit-chain instance with `VIT_VALIDATOR_KEY=<new key>` and `VIT_BOOTSTRAP_HTTP_URL=https://vit-chain.onrender.com`.
- **Was**: VIT Chain is a single-node testnet. `active_validators: 1`. No real decentralization.
- **Actions**:
  1. Document validator onboarding process
  2. Create a second validator node (can be another Render service initially)
  3. Verify consensus votes appear in blocks (`consensus_votes: [...]`)
  4. Update MetaMask setup guide with bootstrap peer URL
- **Owner**: Blockchain System

#### TRACK-021b: Block Explorer (vit-explorer) ✅ SHIPPED 2026-08-04
- **URL**: https://vit-explorer.onrender.com (first deploy in progress)
- **Built**: React 18 + Vite + TypeScript — Overview, Blocks, Validators, Search tabs; 15s auto-refresh; block detail modal; MetaMask setup card.
- **Was**: Zero-code repo. Without a block explorer, the chain has no credibility or usability.
- **Actions**: Build a React/Next.js frontend in `vitnetwork/vit-explorer` that:
  - Shows live block feed (polls `/api/blocks`)
  - Shows validator stats (`/api/validators`)
  - Shows transaction lookup (`/api/txs`)
  - Shows account balances (`/api/accounts`)
  - Deploy to Render alongside the chain
- **Owner**: Frontend System

#### TRACK-014: Sports Intelligence Terminal
- **Gap**: Module exists in `app/modules/sports` but the Analytics Studio had stub endpoints (fixed 2026-08-04).
- **Actions**: Verify all 7 analytics endpoints return real DB data. Add live fixture sync cadence.
- **Owner**: Core System

---

### 🟢 Medium Priority — Next 60 Days

#### TRACK-015: Electoral & Policy Simulator
- **Actions**: Wire `app/modules/elections` sentiment engine to the AI Oracle. Surface polling/sentiment on dashboard.
- **Owner**: Core System / AI System

#### TRACK-016: Academy & Research Portal
- **Actions**: Build `app/modules/academy` reasoning interface. Integrate with AI ensemble for simulation queries.
- **Owner**: Core System

#### TRACK-022: On-Chain Storage Proofs ✅ SHIPPED 2026-08-04
- **Built**: `vit-chain/api/challenges.py` — `GET /api/challenges/pending` + `POST /api/challenges/{id}/respond`; responding to a challenge patches the latest block's `storage_proofs[]` array so proofs are on-chain immediately.
- `vit-storage/tachyon/proof_reporter.py` — ProofReporter background task polls vit-chain each epoch and submits proofs. Auto-enabled when `VIT_STORAGE_VALIDATOR_ADDRESS` env var is set.
- **To activate**: set `VIT_STORAGE_VALIDATOR_ADDRESS=<0x addr>` on the vit-storage Render service, register via `POST https://vit-chain.onrender.com/api/validators/register`.
- **Was**: Proof-of-Storage consensus currently produces blocks with `storage_proofs: []`. The PoS mechanism exists in code but isn't generating real proofs.
- **Actions**:
  1. Connect `vit-storage` proof generation → vit-chain challenge/response cycle
  2. Validator should submit a real `StorageProof` struct per epoch
  3. Block finalizer must reject blocks missing proofs from active storage validators
- **Owner**: Blockchain System + Tachyon System

#### TypeScript SDK (vit-sdk)
- **Actions**: Implement core SDK in `vitnetwork/vit-sdk`:
  - `VITChainClient` — JSON-RPC wrapper (chain queries, tx submission)
  - `VITOracleClient` — AI prediction fetch
  - `TachyonClient` — file upload/download
  - Publish to npm
- **Owner**: Docs System / Core System

---

### 🔵 Longer Term — Next 90+ Days

#### TRACK-017: Affiliate Execution Hub
- Auto deep-link generation and CLV attribution for Sports Oracle predictions.

#### TRACK-018: Multi-Cloud Orchestration (GCP migration per ADR-011)
- Move from Render free tier to GCP Cloud Run + Cloud SQL + Memorystore.
- Eliminates cold start spin-downs on all 4 services.

#### TRACK-019: Mobile Native / Telegram Mini App
- Implement `vitnetwork/vit-mobile`:
  - Wallet view (VITCoin balance, deposit/withdraw)
  - Predictions feed (Sports Oracle)
  - Academic Passport credential display

#### Base L2 Settlement Migration
- Deploy VITCoin ERC-20 and credential NFT contracts to Base Sepolia testnet first.
- Wire treasury operations from vit-chain → Base L2 bridge.
- Chain ID 8453 becomes the settlement layer; Chain ID 7764 remains the PoS execution layer.

---

## Technical Debt & Infrastructure Fixes

| Item | Severity | Action |
|------|----------|--------|
| 1.4MB frontend JS bundle | Medium | Add `manualChunks` in `vite.config.ts` — split vendor, AI, blockchain chunks |
| Render free tier cold starts | High | Upgrade to Render Starter ($7/mo) or migrate to GCP Cloud Run |
| Redis not on vit-storage | High | Add `REDIS_URL` env var to vit-storage Render service |
| Single vit-chain validator | High | TRACK-021a — second validator required for real PoS |
| Empty storage_proofs in blocks | High | TRACK-022 — real PoS proofs must be on-chain |
| `pnpm-lock.yaml` format drift | Low | Regenerate with pnpm 9 in a Docker container |
| npm audit warnings | Low | `npm audit fix` pass on transitive deps |

---

## Success Metrics for Next Phase

| Metric | Current | Target |
|--------|---------|--------|
| Active validators on vit-chain | 1 | ≥ 3 |
| Storage proofs per block | 0 | ≥ 1 |
| Agent scheduler health | `null` | `{active: 22}` |
| Block explorer live | ❌ | ✅ |
| TypeScript SDK published | ❌ | ✅ on npm |
| TRACK-020 DID complete | 🔄 Active | ✅ Complete |
| Frontend bundle size | 1.4 MB | < 600 KB (gzip) |
| Render → GCP migration | ❌ | ✅ at least main app |

---

*Next Phase Plan — VIT Network Engineering. Last verified: 2026-08-04.*
