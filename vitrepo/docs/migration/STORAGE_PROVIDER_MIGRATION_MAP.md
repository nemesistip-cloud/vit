# STORAGE PROVIDER MIGRATION MAP — VIT Ecosystem Migration

This manifest defines the migration mapping from the source repository (`vit`) to the destination repository (`vit-storage`). Every recommendation is backed by a technical review of the current implementation in `vit` (Legacy providers in `tachyon/providers/` and Core providers in `tachyon/core/providers/`).

---

## 🗺️ File Migration Matrix

| Source File (in `vit`) | Destination File (in `vit-storage`) | Action | Recommendation & Technical Reason |
| :--- | :--- | :--- | :--- |
| `tachyon/providers/base.py` | `tachyon/providers/base.py` | **Merge** | **Merge base class interfaces.** The legacy class defines `upload_fragment` and `download_fragment`. The new `vit-storage` has `delete_fragment` and `list_fragments`. Merging guarantees compatibility for both legacy burst scheduler and standard interfaces. |
| `tachyon/providers/disk.py` | `tachyon/providers/disk.py` | **Move** | **Move to destination.** `disk.py` is entirely missing from the current `vit-storage` repository. Since the local DiskProvider is the primary local fallback and is critical for isolated test coverage, it must be migrated without modification. |
| `tachyon/providers/gdrive.py` | `tachyon/providers/gdrive.py` | **Merge** | **Merge with `tachyon/core/providers/gdrive.py`.** The legacy version supports custom initialization (`service_account_json` parameters) and in-memory directory caches. The new `vit-storage` version has path-traversal guards (`..` checks) and resumable large-file uploads. Merging prevents functional regression of either code path. |
| `tachyon/providers/dropbox.py` | `tachyon/providers/dropbox.py` | **Merge** | **Merge with `tachyon/core/providers/dropbox.py`.** The legacy implementation supports OAuth2 refresh token authorization (app key, app secret, refresh token). The `vit-storage` version only supports a static, short-lived `DROPBOX_ACCESS_TOKEN`. Merging is critical to preserve the refresh flow. |
| `tachyon/providers/onedrive.py` | `tachyon/providers/onedrive.py` | **Merge** | **Merge with `tachyon/core/providers/onedrive.py`.** The legacy version uses synchronous `urllib.request` over a threadpool, while the `vit-storage` version uses async `httpx`. The legacy version supports specific `user_id` drive lookups which must be merged into the async `httpx` version. |
| `tachyon/core/providers/pool.py` | `tachyon/core/providers/pool.py` | **Move** | **Move to destination.** `pool.py` acts as the canonical Provider Registry & Provider Factory. It constructs provider instances on-demand based on config arrays. It must be moved to `vit-storage` to coordinate providers there. |
| `tachyon/core/providers/gdrive.py` | `tachyon/providers/gdrive.py` | **Merge** | **Consolidate into standard location.** This core provider contains updated resumable uploads for data shards. It must be merged into `tachyon/providers/gdrive.py` to keep a single Google Drive implementation. |
| `tachyon/core/providers/dropbox.py`| `tachyon/providers/dropbox.py` | **Merge** | **Consolidate into standard location.** Must be merged into `tachyon/providers/dropbox.py` to eliminate duplicated code. |
| `tachyon/core/providers/onedrive.py`| `tachyon/providers/onedrive.py` | **Merge** | **Consolidate into standard location.** Must be merged into `tachyon/providers/onedrive.py` to eliminate duplicated code. |
| `app/services/gcs_storage.py` | *(Remains in `vit`)* | **Keep** | **Keep in Source.** This file manages internal MLpkl weights loading/saving workflows for the local AI models. It is pure business/ML orchestration logic. It should be refactored via a feature flag to query `vit-storage-svc` API instead of doing direct disk writes. |
| `app/services/tachyon_client.py`| *(Remains in `vit`)* | **Keep** | **Keep in Source.** This acts as the official HTTP Client SDK wrapper used by `vit` to query the externalized `vit-storage-svc`. Point the endpoint URL to `vit-storage-svc` instead of a local port. |

---

## 🔍 Consolidation Plan: One canonical class per provider

To prevent future code drift and maintain clean boundaries, we will consolidate the legacy and core provider classes into a single canonical class under `tachyon/providers/` in the `vit-storage` repository:

### 1. Unified Google Drive Provider (`GoogleDriveProvider`)
-   **Class structure:** Inherits from `CloudProvider` in `base.py`.
-   **Constructors:** Accepts `account_id`, `credentials: dict | None = None` and `folder_id: str | None = None`. It parses service account keys from dictionary structures, base64 strings, or raw JSON, following both the Legacy and Core configurations.
-   **Standardized methods:**
    -   `upload_fragment` (and `upload_shard`) -> maps to standard `upload`.
    -   `download_fragment` (and `download_shard`) -> maps to standard `download`.
    -   Provides path-traversal prevention (`..` filter) and SUPPRESS_DISCOVERY suppressions.

### 2. Unified Dropbox Provider (`DropboxProvider`)
-   **Class structure:** Inherits from `CloudProvider` in `base.py`.
-   **Constructors:** Accepts `account_id` and a `credentials` dictionary or distinct params.
-   **Token management:** Auto-checks if refresh-token trio keys (`DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET`, `DROPBOX_REFRESH_TOKEN`) exist. If yes, constructs a refresh-token-aware `dropbox.Dropbox` client; else falls back to static `DROPBOX_ACCESS_TOKEN`.
-   **Standardized methods:** Uses `asyncio.to_thread` or async clients to wrap files uploads, overwrite mode, and space usage calculations.

### 3. Unified OneDrive Provider (`OneDriveProvider`)
-   **Class structure:** Inherits from `CloudProvider` in `base.py`.
-   **Constructors:** Accepts `account_id` and credential dictionary `{client_id, client_secret, tenant_id, user_id}`.
-   **Networking:** Utilizes async `httpx.AsyncClient` for high-performance non-blocking PUT/GET Graph API requests.
-   **Silent MSAL:** Uses `acquire_token_silent` to reuse cached Azure access tokens, preventing rate-limiting on token endpoints.

---

## 📊 Mapping Actions Explained

-   **Move:** File is transferred from the source repository to the destination repository.
-   **Merge:** The legacy and core files contain overlapping or distinct production features. Their contents must be unified into a single, cohesive file in the destination to ensure zero regression.
-   **Keep:** The file remains in `vit` because it represents business orchestrations, workflows, or lightweight client proxies.
-   **Delete:** To be removed in a subsequent clean-up phase once the extraction is verified and 100% operational.
