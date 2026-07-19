# VIT Network Strategic Roadmap
_Last updated: 2026-07-19 — Phase 1 Hardening Sprint, Session 2_

---

## Platform Status

| Dimension | Before Session 1 | After Session 2 |
|---|---|---|
| Phase 1 gate items closed | 0 / 7 | **5 / 7** |
| Hardened services | 0 | 3 (vitnetwork · vit-ai · vit-storage) |
| Frontend bug (405 login) | 🔴 broken | ✅ fixed |
| DB models for chain | 0 | 4 (Block · ValidatorStake · SlashEvent · SlashAppeal) |
| Alembic migration | not present | ✅ zz02 committed |
| Slashing in code (not only docs) | 0% | ✅ SlashingManager wired |
| Genesis seeding wired | not wired | ✅ GenesisSubsystem |

---

## 🔴 Phase 0: Platform Stabilisation (target: 2026-08-02)

- [x] Engineering audit v6.0 completed (2026-07-19)
- [x] VIT_AI_URL + TACHYON_URL wired into vitnetwork service
- [x] vit-ai: config hardened — pydantic field_validator, no hardcoded URLs
- [x] vit-ai: ensemble.py — deterministic Poisson math, no random.uniform
- [x] vit-ai: Dockerfile — curl installed in final stage (healthcheck fix)
- [x] vit-ai: .env.example created
- [x] vit-storage: VIT_SWARM_COORDINATOR_ADDRESS env-var wired in config + router
- [x] nemesistip-cloud/vit: 3 hardcoded Render/GCP URLs removed from app/config.py
- [x] settlement_task.py: supervised asyncio task with named handle + done-callback
- [x] vitnetwork org: README, org profile, all 15 repo descriptions updated
- [x] Frontend login bug fixed: /api/auth/auth/login → /api/auth/login
- [x] Frontend: Login, Matches, Navbar, Footer, index.css redesigned
- [ ] **MANUAL — Render shell**: `alembic upgrade heads` against production Postgres
- [ ] **MANUAL — Render dashboard**: Set VIT_AI_API_KEY, ORACLE_PRIVATE_KEY, UNIVERSAL_ORACLE_ADDRESS
- [ ] Confirm kernel reaches RUNNING state
- [ ] Verify vit-ai /health returns models_loaded > 0 after redeploy

---

## 🟡 Phase 1: Consensus Hardening (target: 2026-09-30)

### ✅ Closed this sprint

- [x] **Genesis seeding idempotent** — `vit_chain/core/genesis.py` with `block_height == 0` guard
- [x] **Genesis wired into startup** — `GenesisSubsystem` registered in kernel (no main.py touch)
- [x] **Slashing enforced in code** — `SlashingManager`: DOUBLE_SIGN (10%), DOWNTIME (1%), INVALID_BLOCK (5%)
- [x] **Slashing wired into ConsensusEngine** — `on_new_block`, `validate_block`, `record_validator_miss`
- [x] **DOUBLE_SIGN detection** — per-height proposal tracker in ConsensusManager
- [x] **DOWNTIME detection** — consecutive miss streak tracker with configurable threshold
- [x] **DB models created** — `Block`, `ValidatorStake`, `SlashEvent`, `SlashAppeal` in `app/db/models.py`
- [x] **Alembic migration** — `zz02_add_chain_and_slash_tables` (idempotent, IF NOT EXISTS)
- [x] **Appeal path** — `SlashAppeal` table + `submit_appeal()` with PENDING status

### 🔴 Open gates

- [ ] **Render env vars** — Set `GENESIS_VALIDATORS`, `SLASHING_DOWNTIME_SLOTS`, `SLASHING_APPEAL_WINDOW_SLOTS` in vitnetwork Render dashboard; `VIT_SWARM_COORDINATOR_ADDRESS` in vit-storage
- [ ] **Block explorer live data** — `/recent-blocks`, `/tx/{hash}` returning real chain data (not 404/503)
- [ ] **Chain-state auto-snapshots** — automated pg_dump → S3/GCP backup task
- [ ] **Validator self-service join** — P2P staking-to-validator promotion path (no admin intervention)
- [ ] **`alembic upgrade heads`** — run on production Postgres to apply zz02 migration

---

## 🟡 Phase 2: Modern Betting Shops (target: Q4 2026)

_Re-estimated against current velocity._

- [ ] Agent Recruitment Portal — UI + backend
- [ ] ShopManager.sol deployment for commission tracking
- [ ] Commission tracking API + dashboard
- [ ] SDK distribution (Python + TypeScript)
- [ ] Offline terminal integration for low-bandwidth environments

---

## 🟡 Phase 3: Electoral & Policy Analytics (target: Q1 2027)

- [ ] ElectoralOracle.sol smart contract
- [ ] Citizen sentiment analytics — live feed integration
- [ ] Policy Simulator v1.0
- [ ] Real-time polling data ingestion

---

## 🟡 Phase 4: E-Commerce & Remittances (target: Q2 2027)

- [ ] Marketplace P2P intelligence trading (exchange engine built, needs wiring)
- [ ] Cross-border remittance via $VIT (Paystack + Stripe present)
- [ ] OPay / PalmPay / MoMo integration
- [ ] Accuracy-based slashing (smart contract + oracle)
- [ ] W3C DID production deployment

---

## ⬜ Phase 5: Continental Scale (target: 2028+)

- [ ] Kenya, Ghana, South Africa, Egypt market corridors
- [ ] $VIT as continental analytics standard
- [ ] Decentralised governance (DAO)
- [ ] Full Proof-of-Storage validator network
- [ ] 1M+ active wallets target

---

## Phase 1 Gate Tracker

| Gate | Status | Evidence |
|---|---|---|
| Genesis seeding idempotent | ✅ | `vit_chain/core/genesis.py` — block_height==0 guard |
| Genesis wired to startup | ✅ | `GenesisSubsystem` in `app/core/subsystems.py` |
| Slashing enforced in code | ✅ | `SlashingManager` — all 3 conditions + rates |
| Slashing wired to consensus | ✅ | `ConsensusManager.on_new_block`, `validate_block`, `record_validator_miss` |
| SlashEvent/SlashAppeal DB tables | ✅ | `app/db/models.py` + Alembic `zz02` |
| Block explorer returning live data | 🔴 | Routes exist; data not verified |
| Chain-state auto-snapshots | 🔴 | No automated backup task |
| Validator self-service join | 🔴 | P2P bootstrapping not implemented |
| Render env vars applied | 🟡 | Committed to codebase; Render dashboard needs manual update |

---

_VIT Network — Verifiable Intelligence. Universal Trust._
_Built on VIT Chain · Chain ID 7764 · Africa's sovereign intelligence layer_
