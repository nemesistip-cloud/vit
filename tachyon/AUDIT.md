# Tachyon VESS Audit

## Existing Files

### `tachyon/core/worker.py`
- Contains `TachyonVerificationWorker` class.
- Periodically (default 3600s) runs `audit_cycle`.
- `audit_cycle` selects up to 10 `StorageProof`s with status `ANCHORED`.
- Issues challenges using `issue_challenge` and auto-responds using `respond_to_challenge` with simulated data.
- Uses `AsyncSessionLocal` and `app.modules.storage_verification.service`.

### `tachyon/api/router.py`
- FastAPI APIRouter with endpoints:
    - `POST /upload`: Shreds file, uploads fragments using `TachyonScheduler`, saves `TachyonManifest`, and submits storage proofs.
    - `GET /download/{file_id}`: Downloads fragments and reassembles using `TachyonScheduler`.
    - `GET /manifests`: Lists `TachyonManifest` records from DB.
    - `DELETE /manifests/{file_id}`: Deletes manifest from DB.
    - `POST /providers/link`: Persists provider credentials to `PlatformConfig`.
    - `GET /providers`: Lists configured providers and node counts.
    - `GET /status`: Returns network and storage status.
- Provider initialization:
    - Loads from `UserStorageNode` table.
    - Fallback to env vars (`GDRIVE_SERVICE_ACCOUNT_JSON`, etc.).
    - Always includes `DiskProvider` as primary backend.

### `app/modules/storage_verification/models.py`
- `ContentHashRegistry`: Tracks content hashes, IPFS CIDs, and Tachyon-specific metadata (is_tachyon, shards, parity_shards, quantum_state_hash).
- `StorageProof`: Cryptographic proofs of data availability.
- `StorageChallenge`: Challenges issued to verify proofs.
- `DataAvailabilityAttestation`: Multi-validator attestations.
- `TachyonManifest`: Metadata for Tachyon uploads (fragment names, provider mapping).
- `UserStorageNode`: User-contributed cloud storage accounts.

## Storage Mechanism
- Currently uses a mix of local disk and cloud providers.
- `DiskProvider`: Stores fragments in a local directory (`/tmp/tachyon_storage` by default).
- `GoogleDriveProvider`, `DropboxProvider`, `OneDriveProvider`: Use respective cloud APIs.
- Existing providers are located in `tachyon/providers/`.

## Observations
- `TachyonShredder` in `tachyon/core/shredder.py` already implements some Reed-Solomon logic using `reedsolo`.
- The spec calls for `tachyon/core/erasure.py` and `tachyon/core/providers/` (note the `core/` prefix).
- Existing providers use `upload_fragment` and `download_fragment` naming, whereas the spec asks for `upload_shard` and `download_shard`.
- Requirements for `reedsolo`, `google-auth`, `google-api-python-client`, `msal`, and `dropbox` are already in `requirements.txt`. `google-auth-httplib2` is missing.
- `ProviderPool` is currently missing; its logic seems partially implemented within `tachyon/api/router.py` and `TachyonScheduler`.

## Missing / To be implemented
- `tachyon/core/erasure.py`: A dedicated Reed-Solomon codec class. (Implemented in 4.1)
- `tachyon/core/providers/`: New provider implementations matching the spec's naming and structure. (Implemented in 4.1)
- `tachyon/core/providers/pool.py`: A dedicated `ProviderPool` class for better provider management. (Implemented in 4.1)
- `tachyon/tests/test_erasure.py`: Unit tests for the erasure coding logic. (Implemented in 4.1)

## Session 4.2 - Upload Orchestrator + Self-Healing

### Missing Components
- `tachyon/core/manifest.py`: `ManifestManager` to handle persistence and health tracking.
- `tachyon/core/orchestrator.py`: `TachyonOrchestrator` to coordinate upload/retrieve/delete/verify.
- `tachyon/core/retrieval.py`: `ShardRetriever` for parallel shard downloads.
- `tachyon/core/healing.py`: `SelfHealingManager` for repair and background healing loop.

### Model Constraints & Strategy
- `TachyonManifest` model is fixed.
- Strategy: Store `sha256`, `health_score`, `status`, and `last_verified_at` inside the `provider_mapping` JSON column as a nested `_metadata` key.
- Store `shard_locations` (list of dicts) in the `provider_mapping` column under a `shards` key.
- Maintain compatibility with `tachyon/api/router.py` where possible, or migrate it to use the new Orchestrator.
