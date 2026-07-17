# STORAGE PROVIDER MIGRATION PACKAGE — Execution Guide for vit-storage

This document is a **repository-ready specification** designed for a separate, dedicated Jules task operating directly on the `vit-storage` repository. It provides all files, dependency hierarchies, and testing scripts required to complete the migration without redundant analysis.

---

## 📦 1. Target File Migration Checklist

Execute the extraction and consolidation of provider files in `vit-storage` in this exact order:

```
[Step 1: Interface base.py]
          │
          ▼
[Step 2: Disk disk.py]
          │
          ▼
[Step 3: GDrive gdrive.py] ──┐
          │                  ├─► [Step 6: Pool Registry pool.py]
          ▼                  │
[Step 4: Dropbox dropbox.py] ┘
          │
          ▼
[Step 5: OneDrive onedrive.py]
```

### 1.1 `base.py` (Base Contract Standard)
*   **Source in `vit`:** `tachyon/providers/base.py`
*   **Destination in `vit-storage`:** `tachyon/providers/base.py`
*   **Target Interface Contract:**
    ```python
    from abc import ABC, abstractmethod
    from typing import Optional, List

    class CloudProvider(ABC):
        account_id: str

        @abstractmethod
        async def upload_fragment(self, data: bytes, name: str) -> bool: ...

        @abstractmethod
        async def download_fragment(self, name: str) -> Optional[bytes]: ...

        @abstractmethod
        async def delete_fragment(self, name: str) -> bool: ...

        @abstractmethod
        async def list_fragments(self) -> List[str]: ...

        @abstractmethod
        async def get_quota(self) -> dict: ...

        @abstractmethod
        async def get_latency(self) -> float: ...
    ```

### 1.2 `disk.py` (Local Shard Backend)
*   **Source in `vit`:** `tachyon/providers/disk.py`
*   **Destination in `vit-storage`:** `tachyon/providers/disk.py` (File must be newly created in `vit-storage`).
*   **Integration Action:** Copy directly. Ensure it inherits from `CloudProvider` and implements the abstract methods.

### 1.3 `gdrive.py` (Google Drive Provider)
*   **Source in `vit`:** `tachyon/providers/gdrive.py` (and `tachyon/core/providers/gdrive.py`)
*   **Destination in `vit-storage`:** `tachyon/providers/gdrive.py`
*   **Merge Criteria:** Unify both classes. Accept `service_account_json` dictionary/strings and implement the traversal guard (`".." not in name`) along with the local lookups cache (`_name_to_id`).

### 1.4 `dropbox.py` (Dropbox Provider)
*   **Source in `vit`:** `tachyon/providers/dropbox.py`
*   **Destination in `vit-storage`:** `tachyon/providers/dropbox.py`
*   **Merge Criteria:** Unify OAuth2 token-refresh flows (utilizing app keys/secrets/refresh tokens) with sandboxed traversal checks.

### 1.5 `onedrive.py` (OneDrive Provider)
*   **Source in `vit`:** `tachyon/providers/onedrive.py`
*   **Destination in `vit-storage`:** `tachyon/providers/onedrive.py`
*   **Merge Criteria:** Use async `httpx` to complete all Microsoft Graph PUT/GET queries. Maintain MSAL silent AD caching.

### 1.6 `pool.py` (Central Provider Factory / Pool)
*   **Source in `vit`:** `tachyon/core/providers/pool.py`
*   **Destination in `vit-storage`:** `tachyon/core/providers/pool.py`
*   **Action:** Transition directly. Set as the authoritative manager to bootstrap providers based on env vars array configurations.

---

## ⚙️ 2. Environment Configuration Mapping

To prevent any environment configuration leakages or variable duplication, configure `vit-storage` to standardise on these authoritative settings:

| Cloud Platform | Config Environment Variable | Format Specification |
| :--- | :--- | :--- |
| **Google Drive** | `GDRIVE_SERVICE_ACCOUNT_JSON` | Raw SA JSON dictionary or Base64 string |
| | `GDRIVE_SERVICE_ACCOUNT_KEYS` | JSON-encoded array of service account structures (Pool) |
| **Dropbox** | `DROPBOX_ACCESS_TOKEN` | Static string token |
| | `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET` | OAuth developer credential |
| | `DROPBOX_REFRESH_TOKEN` | Continuous offline authorization refresh token |
| **OneDrive** | `ONEDRIVE_CLIENT_ID` | Azure client application identifier |
| | `ONEDRIVE_CLIENT_SECRET` | Azure confidential secret |
| | `ONEDRIVE_TENANT_ID` | Azure tenant directory or `"common"` |

---

## 🧪 3. Validation & Testing Protocols

The executing task in `vit-storage` must run and verify these specific test routines:

### 3.1 Mock Provider Testing
Construct tests that mock external networks (`unittest.mock` or `pytest-mock`) to simulate successful/failed transfers:
-   **Gdrive:** Verify `cache_discovery=False` and that correct `MediaIoBaseUpload` is structured.
-   **Dropbox:** Verify that if credentials are instantiated with app keys/secrets, `dropbox.Dropbox` refresh method is invoked.
-   **OneDrive:** Verify `httpx` handles status code `201` during file upload PUT calls.

### 3.2 Recovery & Fallback Assertions
Configure tests inside `ProviderPool` that verify:
-   **Capacity Fallback:** If a mock provider reports storage quota used fraction > 90%, it must not be selected for `upload_shard`.
-   **Timeout Quarantine:** If a provider upload raises a timeout error, it must be quarantined for 600s and standard status returns it as degraded.

---

## 🚨 4. Rollback and Recovery Strategy

If the migration to `vit-storage` experiences deployment regressions, the cluster orchestration must immediately implement this recovery protocol:

1.  **De-escalate Routing (Feature Flag):** Turn off `VIT_STORAGE_USE_EXTERNAL` in the `vit` environment. This immediately returns the main business repository to local parsing.
2.  **Point Endpoint Local:** Keep `TACHYON_ENDPOINT` pointing to `http://localhost:5000/api/tachyon` inside `vit`.
3.  **Audit Logs:** Extract `vit-storage-svc` Cloud Run logs or Render console records to locate specific authentication / network timeouts.
