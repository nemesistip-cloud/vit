---
name: Frontend API path convention
description: apiClient uses ${API_BASE}${path} with no auto-prefix — every route call must be fully qualified.
---

## Rule
Every `apiGet`, `apiPost`, `apiPut`, `apiDelete`, `apiPatch`, `apiFormPost` call must include the full path:
- Backend API routes: `/api/...`
- Auth routes: `/auth/...` (these are registered WITHOUT `/api/` prefix in main.py)
- WebSocket: `/ws/...`

**Why:** `apiClient` in `frontend/src/lib/api.ts` constructs the URL as `${API_BASE}${path}` where `API_BASE` is the origin (e.g. `https://...replit.dev`). There is no automatic `/api/` prefix injected.

**How to apply:** When adding a new frontend API call, check how the backend router is registered in `main.py` (`include_router(router, prefix="/api")` → needs `/api/` in frontend path). Auth router is registered with NO prefix, so auth routes stay as `/auth/...`.

**Common patterns that were wrong (now fixed):**
- `/predict` → `/api/predict` (predict router registered with `prefix="/api"`)
- `/odds/injuries` → `/api/odds/injuries`
- `/training/dataset/stats` → `/api/training/dataset/stats`
- `/ai/performance/update` → `/api/ai/performance/update`
