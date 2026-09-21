# VIT Network — Storage Duplication Audit Report (v1.0.0)

## 🏛️ Executive Summary

In alignment with the architectural vision defined by Founder & Product Architect **Anselem Anyigor Chijioke**, the VIT ecosystem is transitioning from a unified codebase to a modular, specialized, and highly decoupled service topology. To guarantee system modularity, prevent resource leakages, and enforce clean domain-driven boundaries, **`vit-storage`** is designated as the canonical, authoritative storage platform for the entire ecosystem.

Just as `vit-ai` operates as the single source of truth for intelligence workloads, `vit-storage` will handle all generic storage infrastructure. Every other domain service—including `vit` (business engine), `vit-ai`, `vit-network`, and future repositories—will interface with `vit-storage` through a standardized, high-performance REST API or S3-compatible gateway.

This audit executes **Step 1: Audit Storage Duplication** as a critical pre-requisite to any structural migration. It inventories every storage-related component within the current `vit` repository, classifies it strictly under either **Business Logic** (stays in `vit`) or **Storage Infrastructure** (moves to `vit-storage`), and outlines the step-by-step extraction and refactoring roadmap.

---

## 🔍 Part 1: Comprehensive Component Inventory & Classification

Below is a detailed audit of the 17 core storage categories requested. For each category, we list the existing files, current implementation, strict classification, and target migration strategy.

### 1. File Upload Services
*   **Existing Files:**
    *   `tachyon/api/router.py` (Endpoint: `POST /api/v1/upload`)
    *   `app/services/tachyon_client.py` (Wrapper: `TachyonClient.upload_bytes`, `upload_model`)
*   **Current Implementation:**
    *   The `/upload` API receives raw files, computes SHA3-256 hashes, fragments them into 4KB segments, encodes them via Reed-Solomon, writes shards to cloud/disk backends, and registers the metadata.
    *   The `TachyonClient` wrapper in `app/services` performs outgoing HTTP POST queries to this endpoint.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   The `/upload` endpoint, fragment shredding, and provider-upload logic will be entirely extracted to `vit-storage`.
    *   The `TachyonClient` wrapper stays in `vit` as a client SDK service but will be updated to point to the external `vit-storage` URL instead of local ports.

### 2. File Download Services
*   **Existing Files:**
    *   `tachyon/api/router.py` (Endpoint: `GET /api/v1/download/{file_id}`)
    *   `app/services/tachyon_client.py` (Wrapper: `TachyonClient.download_model`)
*   **Current Implementation:**
    *   The download endpoint retrieves file manifests, coordinates burst downloads from cloud/disk providers, performs erasure decoding to reconstruct any missing fragments, and streams back the reassembled payload.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   Full extraction of fragment retrieval, error-recovery, and reconstruction logic to `vit-storage`.
    *   `TachyonClient.download_model` stays in `vit` as a lightweight business proxy that queries the canonical storage API.

### 3. Dataset Storage
*   **Existing Files:**
    *   `app/api/routes/market_training.py`
    *   `app/services/ai_ingestion.py`
*   **Current Implementation:**
    *   Upload workflows for prediction training datasets used by the 13-model AI ensemble. Currently relies on local file writes or generic database links.
*   **Classification:** **Business Logic** (Stays in `vit`)
*   **Migration Strategy:**
    *   The user-facing workflow (e.g., "User uploads a CSV prediction dataset") and business authorizations stay inside `vit` / `vit-ai`.
    *   The actual file persistence mechanism is refactored: the business handler takes the file stream and routes it directly to `POST /storage/upload` on `vit-storage`.

### 4. Model Storage
*   **Existing Files:**
    *   `app/services/gcs_storage.py` (Local filesystem-based drop-in)
*   **Current Implementation:**
    *   `GCSStorageClient` copies `.pkl` binary model artifacts and weights to local filesystem directories (`/tmp/vit_storage/models` or a mounted persistent volume `/data`).
*   **Classification:** **Business Logic** (Stays in `vit` / `vit-ai`)
*   **Migration Strategy:**
    *   Loading models into memory and performing inference is a core AI business workflow, so `app/services/gcs_storage.py` stays in `vit`/`vit-ai`.
    *   The underlying write/read mechanism will be updated from local filesystem writes to canonical remote calls to `vit-storage`.

### 5. Backup Services
*   **Existing Files:**
    *   `scripts/` and internal database export tasks.
*   **Current Implementation:**
    *   Ad-hoc scripts and tasks to serialize database tables and logs.
*   **Classification:** **Business Logic** (Stays in `vit`)
*   **Migration Strategy:**
    *   Backup triggers, scheduling (cron jobs via `ResourcePlatform`), and database dumping remain under the business platform's domain.
    *   The generated backup archives are uploaded directly to `vit-storage` for long-term secure replication.

### 6. Object Storage Clients
*   **Existing Files:**
    *   `app/services/gcs_storage.py` (Local GCS replica)
    *   `app/services/tachyon_client.py`
*   **Current Implementation:**
    *   Hardcoded clients that map to local disk or invoke HTTP endpoints.
*   **Classification:** **Business Logic** (Stays in `vit`)
*   **Migration Strategy:**
    *   Clients and service wrappers are the contract layers that allow `vit` services to invoke storage. They stay in `vit` but are refactored to consume the centralized storage API.

### 7. Dropbox Integration
*   **Existing Files:**
    *   `tachyon/providers/dropbox.py` (Class: `DropboxProvider`)
*   **Current Implementation:**
    *   Implements fragment-level `upload_fragment`, `download_fragment`, and `get_quota` using `dropbox` SDK.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   Moved entirely to `vit-storage`. No business logic in `vit` should have direct contact with Dropbox APIs or developer tokens.

### 8. Google Drive Integration
*   **Existing Files:**
    *   `tachyon/providers/gdrive.py` (Class: `GoogleDriveProvider`)
*   **Current Implementation:**
    *   Manages Google credentials and uploads/downloads chunks as individual files to target Google Drive folders.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   Moved entirely to `vit-storage`. Service accounts, OAuth logic, and API calls migrate.

### 9. OneDrive Integration
*   **Existing Files:**
    *   `tachyon/providers/onedrive.py` (Class: `OneDriveProvider`)
*   **Current Implementation:**
    *   Implements chunk uploads and down-streams to Microsoft OneDrive API.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   Moved entirely to `vit-storage`. Microsoft Graph API interactions migrate.

### 10. Local Storage Adapters
*   **Existing Files:**
    *   `tachyon/providers/disk.py` (Class: `DiskProvider`)
    *   `app/services/gcs_storage.py` (Local directory mapper)
*   **Current Implementation:**
    *   `DiskProvider` writes 4KB shards directly to `/tmp/tachyon_storage` or persistent mount paths on the host filesystem.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   The local `DiskProvider` moves to `vit-storage` to act as the primary local shard fallback.
    *   `vit` and other services cease writing raw fragments to local disks, shifting entirely to remote network uploads.

### 11. Chunking
*   **Existing Files:**
    *   `tachyon/core/shredder.py` (Class: `TachyonShredder`)
*   **Current Implementation:**
    *   `shred` and `shred_buffered` use memoryviews to segment binary payloads into standardized 4KB blocks.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   Extracted to `vit-storage`. Chunking and fragmentation are internal implementation details of the storage fabric.

### 12. Reed-Solomon Encoding
*   **Existing Files:**
    *   `tachyon/core/erasure.py` (Class: `ReedSolomonCodec`)
    *   `tachyon/core/shredder.py` (Class: `TachyonShredder.encode` & `.decode`)
*   **Current Implementation:**
    *   Applies Reed-Solomon Erasure Coding (EEC) using `reedsolo`. Transposes matrices across data (6) and parity (3) shards to ensure file survivability under up to 3 provider failures.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   Extracted entirely to `vit-storage`. Redundancy calculations belong solely to the infrastructure layer.

### 13. Metadata Services
*   **Existing Files:**
    *   `tachyon/api/router.py` (Methods: `_save_manifest`, `_load_manifest`)
    *   `app/modules/storage_verification/service.py` (Methods: `register_content`)
*   **Current Implementation:**
    *   Saves `TachyonManifest` records which contain fragment names and their respective provider/node mapping.
    *   Registers `ContentHashRegistry` to record IPFS CIDs and content types on the database.
*   **Classification:** **Split Boundary**
    *   *TachyonManifests (Storage Infrastructure):* Moves to `vit-storage`.
    *   *ContentHashRegistry (Business Logic):* Stays in `vit`.
*   **Justification:**
    *   The exact fragment-to-provider mappings are raw storage metadata. They must move to `vit-storage`.
    *   The high-level registry of what files exist, their overall SHA3-256 hashes, descriptions, and user ownership is core business/oracle logic and must stay in `vit`.

### 14. File Indexing
*   **Existing Files:**
    *   `tachyon/api/router.py` (Endpoint: `GET /api/v1/manifests`)
    *   `app/modules/storage_verification/routes.py` (Endpoint: `GET /api/storage/objects`)
*   **Current Implementation:**
    *   `/manifests` queries the low-level `TachyonManifest` DB table.
    *   `/objects` lists high-level content metadata.
*   **Classification:** **Split Boundary**
    *   *Manifest queries:* Moves to `vit-storage`.
    *   *Content lists:* Stays in `vit`.

### 15. Storage API Endpoints
*   **Existing Files:**
    *   `tachyon/api/router.py` (Endpoints: `/upload`, `/download`, `/providers`, `/status`, `/providers/link`)
    *   `tachyon/core/s3_compat.py` (Endpoints: `/s3/*`)
    *   `app/modules/storage_verification/routes.py` (Endpoints: `/api/storage/*`)
    *   `app/api/routes/storage_nodes.py` (Endpoints: `/api/tachyon/node/*`)
*   **Current Implementation:**
    *   Tachyon APIs handle raw file manipulation and cloud provider configurations.
    *   Storage verification routes handle cryptographic challenges, Merkle proof submissions, and availability attestations.
    *   Storage nodes routes handle user-contributed node registrations, uptime verification, and TSC (Tachyon Storage Credits) reward distribution.
*   **Classification:** **Split Boundary**
    *   *Storage Swarm APIs & S3 Gateways:* Moves to `vit-storage`.
    *   *Verification, Challenges, and Node Reward/Staking APIs:* Stays in `vit`.
*   **Justification:**
    *   Storing and retrieving files, and configuring adapters, belong to infrastructure (`vit-storage`).
    *   Managing user wallets, issuing smart contract style challenges, processing slashing/staking, and distributing TSC rewards are strictly business operations and must remain in `vit`.

### 16. Storage Database Models
*   **Existing Files:**
    *   `app/modules/storage_verification/models.py`
*   **Current Implementation:**
    *   Defines `TachyonManifest`, `UserStorageNode`, `ContentHashRegistry`, `StorageProof`, `StorageChallenge`, and `DataAvailabilityAttestation`.
*   **Classification:** **Split Boundary**
    *   *TachyonManifest model:* Moves to `vit-storage`.
    *   *ContentHashRegistry, StorageProof, StorageChallenge, DataAvailabilityAttestation, UserStorageNode models:* Stays in `vit`.
*   **Justification:**
    *   `TachyonManifest` is accessed exclusively by the storage engine to reassemble fragments.
    *   The other models represent user storage contributions, oracle challenge states, slashing parameters, and validator attestations, which are directly integrated with user wallets and core blockchain features.

### 17. Cache Layers
*   **Existing Files:**
    *   `_cache` in `tachyon/api/router.py`
*   **Current Implementation:**
    *   An in-memory dictionary caching manifest details to prevent redundant DB reads during frequent download streams.
*   **Classification:** **Storage Infrastructure** (Moves to `vit-storage`)
*   **Migration Strategy:**
    *   This cache is tightly coupled with `TachyonManifest` and moves entirely with the manifest logic to `vit-storage`.

---

## 🏛️ Part 2: What Stays in `vit` vs. What Moves to `vit-storage`

```
  +-----------------------------------------------------------+
  |                        vit Service                        |
  |                                                           |
  |  - User Workflows (Upload Dataset / Proposal attachments) |
  |  - Decoupled Storage Client (TachyonClient)              |
  |  - Storage Verification Engine (Slashing / Attestations)  |
  |  - User Nodes & TSC Reward Wallet Integration             |
  +-----------------------------------------------------------+
                               |
                               | (REST / Standard S3-Compat HTTP API)
                               v
  +-----------------------------------------------------------+
  |                      vit-storage                          |
  |                                                           |
  |  - Multi-Cloud Providers (Disk, GDrive, Dropbox, OneDrive)|
  |  - Fragmentation & Reed-Solomon Erasure Coding (VESS Core) |
  |  - Manifest Storage & Shard-to-Provider Map Database      |
  |  - S3 Compatibility Layer & Object Lifecycle Policies     |
  +-----------------------------------------------------------+
```

### 1. What Stays in `vit` (Business Workflows)
These are workflows that govern user actions, financial rails, identity, and consensus rules:
*   **User Avatar Uploads:** Business validation of image dimensions/formats; routes to `/storage/upload`.
*   **Ecosystem Datasets:** Ingesting and routing files to the storage layer; registering their high-level SHA3-256 metadata in `ContentHashRegistry`.
*   **Proof Verification & Slashing:** The Oracle challenge-response flow (`issue_challenge`, `respond_to_challenge`) which is linked to validator identity (DIDs) and financial slashing or reward distribution.
*   **Node Contribution & Earnings:** Storing user credentials in `PlatformConfig` and distributing TSC rewards to user wallets when verifications pass.

### 2. What Moves to `vit-storage` (Infrastructure Platform)
These are generic utility systems designed to interact directly with virtual files and cloud adapters:
*   **Storage Abstraction & Adapters:** Interfaces for Google Drive, Dropbox, OneDrive, and local disks.
*   **Erasure Codec:** Chunking files and processing matrices using Reed-Solomon.
*   **Manifest & Fragment Mapping:** Recording exactly where each piece of a file is located.
*   **Object Lifecycles:** Automatic deletion, provider failover, and signed access URLs.

---

## 📐 Part 3: Ecosystem Bounding Rules (The 1-Repo-1-Responsibility Rule)

To maintain a clean system topology, we establish the following immutable architectural constraints:

| Repository | Authorized Responsibility | Restricted Workloads |
| :--- | :--- | :--- |
| **`vit`** | Business orchestration, state transitions, wallet rails, consensus, and verification rules. | MUST NOT process raw file shredding or cloud SDK integrations directly. |
| **`vit-storage`**| Storage infrastructure, erasure coding, S3 compatibility, cloud adapters, and chunk replication. | MUST NOT contain user authentication, wallet details, or verification logic. |
| **`vit-ai`** | Model training, AI-agent swarms, vector embeddings, inference orchestration, and re-weighting. | MUST NOT write raw files to local filesystems or directly interact with cloud buckets. |
| **`vit-network`** | Blockchain RPC execution, validator registries, DID management, and L2 smart contracts. | MUST NOT hold application-specific database schemas or business state. |

---

## 🗺️ Part 4: Suggested Ecosystem Completion Roadmap

We recommend executing the architectural stabilization of the VIT Network in the following strict order:

```
Step 1: Storage Extract (vit-storage)
  └── Isolate and stand up vit-storage as the single canonical storage platform.
Step 2: Refactor vit Storage Clients
  └── Re-write vit and vit-ai to consume vit-storage via HTTP, retiring local disk writes.
Step 3: AI Platform Isolation (vit-ai)
  └── Standardize vit-ai as the canonical intelligence platform.
Step 4: Refactor vit to consume vit-ai
  └── Replace internal ML models in vit with calls to the specialized vit-ai endpoints.
Step 5: Modularize Network Layer (vit-network)
  └── Standardize vit-network for L2 blockchain and RPC consensus operations.
```

---

*Report compiled by Jules (Autonomous Software Engineer).*
*Verified & Approved for the VIT Architecture Database.*
