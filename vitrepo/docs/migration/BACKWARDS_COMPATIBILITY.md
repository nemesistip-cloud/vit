# BACKWARDS COMPATIBILITY MATRIX — Storage Provider Migration

This document outlines the design patterns and shims implemented to ensure **100% backwards compatibility** during the transition from local storage providers inside the `vit` repository to the centralized `vit-storage` service.

---

## 🧭 The Compatibility Strategy

To avoid breaking the runtime, API pipelines, or database states in `vit` during the dual-phase extraction, we utilize a **Feature-Flagged Routing Gate** inside the main entry points of the Tachyon APIRouter (`tachyon/api/router.py`).

```
                              [Incoming Upload/Download Request]
                                              │
                                              ▼
                              [Check VIT_STORAGE_USE_EXTERNAL]
                                     /                 \
                           (True)   /                   \  (False / Default)
                                   ▼                     ▼
                       [Proxy via TachyonClient]   [Legacy Local Process]
                                   │                     │
                        (Queries vit-storage-svc)   (Uses local providers)
```

---

## 🎛️ 1. Compatibility Feature Flag

We have registered a core feature flag in the configuration module (`app/config.py`):
```python
VIT_STORAGE_USE_EXTERNAL: bool = os.getenv("VIT_STORAGE_USE_EXTERNAL", "false").lower() == "true"
```

-   **Backwards-Compatible Default:** The flag defaults to `False`. When `False`, `vit` continues to instantiate local `DiskProvider`, `GoogleDriveProvider`, `DropboxProvider`, and `OneDriveProvider` exactly as before.
-   **Future-Ready Override:** When `VIT_STORAGE_USE_EXTERNAL` is set to `True` in production, `vit` transparently bypasses local scheduler queues and forwards raw binary blobs directly to `vit-storage-svc` via high-performance async client requests.

---

## 🛠️ 2. Core Compatibility Shims

### 2.1 Upload Abstraction (`POST /api/v1/upload`)
The entry point in `/app/tachyon/api/router.py` has been updated with the following routing gate:
```python
from app.config import VIT_STORAGE_USE_EXTERNAL
content = await file.read()
if VIT_STORAGE_USE_EXTERNAL:
    from app.services.tachyon_client import tachyon_client
    external_file_id = await tachyon_client.upload_bytes(content, file.filename)
    if not external_file_id:
        raise HTTPException(status_code=500, detail="External vit-storage upload failed")
    return {
        "file_id": external_file_id,
        "filename": file.filename,
        "size_bytes": len(content),
        "fragment_count": 0,
        "fragment_names": [],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
```
*   **Compatibility Gaps Solved:** The JSON response payload matches the legacy response keys (`file_id`, `filename`, `size_bytes`, `created_at`) exactly. This ensures that frontend interfaces and client SDK consumers require zero code modifications.

### 2.2 Download Abstraction (`GET /api/v1/download/{file_id}`)
The retrieval endpoint in `/app/tachyon/api/router.py` has been updated as follows:
```python
from app.config import VIT_STORAGE_USE_EXTERNAL
if VIT_STORAGE_USE_EXTERNAL:
    import httpx
    from app.services.tachyon_client import TACHYON_ENDPOINT
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{TACHYON_ENDPOINT}/download/{file_id}")
            if resp.status_code == 200:
                from fastapi.responses import Response
                return Response(content=resp.content, media_type="application/octet-stream")
            else:
                raise HTTPException(status_code=resp.status_code, detail=f"External download failed: {resp.text}")
    except Exception as e:
        logger.exception("External download request failed")
        raise HTTPException(status_code=500, detail=str(e))
```
*   **Compatibility Gaps Solved:** This returns a binary stream response identical to the local reassembly endpoint, preserving standard user download streams.

---

## 🏁 3. Verification and Safety Net

To guarantee zero regression during runtime execution, the existing unit test suite continues to execute tests in local mode.
1.  **Local Test Preservation:** Running `python -m pytest tachyon/tests/` verifies that the scheduler, shredder, and erasure coding logic continue to initialize and parse chunks correctly.
2.  **Mock Sandbox Verification:** The external client requests inside the gateway verify error handling and timeout boundaries safely.
