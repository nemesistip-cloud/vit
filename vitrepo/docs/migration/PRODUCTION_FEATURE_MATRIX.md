# PRODUCTION FEATURE MATRIX — VIT Ecosystem Migration

This document identifies all advanced, production-grade features in the local `vit` storage providers that **must** be preserved when completing the migration to the canonical `vit-storage` service. Removing or simplifying these components during the final stage would introduce critical operational regressions.

---

## 🛠️ Provider Feature Completeness Matrix

| Target Feature | Legacy `vit` Provider Implementation | Destination `vit-storage` Mock/Stub | Requirement for Destination Migration |
| :--- | :--- | :--- | :--- |
| **OAuth2 Refresh Token** (Dropbox) | **Supported.** Auto-refreshes using App Key + App Secret + Refresh Token trio. | *Not Supported.* Static token only. | **Critical.** Destination must merge the refresh flow to avoid credential expiration after 4 hours. |
| **Silent Token Acquisition** (OneDrive) | **Supported.** MSAL app silent caching. | *Not Supported.* Requests token on every call. | **Critical.** High-concurrency downloads will trigger Azure endpoint rate-limiting without MSAL silent caching. |
| **Folder-ID Memoization Cache** (GDrive) | **Supported.** Keeps name-to-file-ID cache after first lookup. | *Not Supported.* Searches Drive via string match API on every shard download. | **High.** Eliminates search round-trip from GDrive API latency. |
| **Suppress Discovery Flag** (GDrive) | **Supported.** `cache_discovery=False` on GAPI build client. | *Not Supported.* Discovery enabled (calls GAPI servers on instantiation). | **High.** Discovery flag caching speeds up build instantiations by >150ms. |
| **Quota Guard Fallback** (Pool) | **Supported.** Block uploads when a cloud provider exceeds 90% capacity. | *Not Supported.* Fails only when provider raises disk full error. | **Critical.** Required to prevent un-shreddable chunks and upload failures. |
| **Degraded Timeout Quarantine** (Pool) | **Supported.** 10-minute (600s) automated quarantine for failing nodes. | *Not Supported.* Tries same failing nodes in round-robin on every call. | **Critical.** High-concurrency operations will stall if a single provider is slow or offline. |
| **Path Traversal Shield** (Security) | *Not Supported in Legacy.* | **Supported.** GDrive, Dropbox, OneDrive check `..` and leading `/`. | **Critical.** Must be kept in merged production implementations. |
| **Resumable Chunk Uploads** (GDrive) | *Not Supported in Legacy.* | **Supported.** Uses `MediaIoBaseUpload` with resumable flag for shards > 5MB. | **High.** Enhances reliability for large binary datasets. |

---

## 🔍 Detailed Analysis of Production Capabilities

### 1. Dropbox OAuth2 Token Refresh Flow
The production-ready `DropboxProvider` inside `vit` (located at `/app/tachyon/providers/dropbox.py`) includes specific logic to overcome short-lived access tokens:
```python
if self._access_token:
    return dropbox.Dropbox(self._access_token)
if self._refresh_token and self._app_key and self._app_secret:
    return dropbox.Dropbox(
        oauth2_refresh_token=self._refresh_token,
        app_key=self._app_key,
        app_secret=self._app_secret,
    )
```
*   **Operational Risk:** If the destination `vit-storage` is deployed using only the static token, the service will stop functioning once the initial access token expires, requiring manual maintenance of environment files.
*   **Mitigation:** The final consolidated `DropboxProvider` in `vit-storage` must incorporate this key logic block.

### 2. OneDrive (MSAL) Silent Acquisition & Token Caching
The production-ready `OneDriveProvider` inside `vit` (located at `/app/tachyon/providers/onedrive.py`) utilizes the Confidential Client Application framework from `msal` to fetch and reuse tokens efficiently:
```python
def _acquire_token_sync(self, app) -> str:
    result = app.acquire_token_silent(_SCOPES, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=_SCOPES)
```
*   **Operational Risk:** Making a full HTTPS roundtrip to Microsoft AD on every read/write operation is slow and triggers rate-limiting under standard load.
*   **Mitigation:** Silent token lookup must be maintained.

### 3. Provider Pool Degraded Timout and Round-Robin
The registry coordinator inside `vit` (located at `/app/tachyon/core/providers/pool.py`) implements advanced high-availability routing:
-   **Lockout logic:** When an upload to a provider fails, the provider is placed in a 600-second quarantine.
-   **Index rotation:** Keeps a rolling current index to avoid selecting the same initial provider sequentially.
*   **Operational Risk:** Without this, a single slow cloud provider can degrade overall ecosystem throughput.
*   **Mitigation:** Port the registry pool directly to `vit-storage`.
