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
- `tachyon/core/erasure.py`: A dedicated Reed-Solomon codec class.
- `tachyon/core/providers/`: New provider implementations matching the spec's naming and structure.
- `tachyon/core/providers/pool.py`: A dedicated `ProviderPool` class for better provider management.
- `tachyon/tests/test_erasure.py`: Unit tests for the erasure coding logic.
