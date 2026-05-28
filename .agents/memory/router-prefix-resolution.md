---
name: Router prefix resolution
description: Final route path = router's own prefix + include_router prefix. Check both in main.py to derive the full path.
---

## Rule
To find the full URL path of any backend endpoint:
1. Look at `router = APIRouter(prefix="X")` in the route file → this is the router's own prefix
2. Look at `app.include_router(router, prefix="Y")` in `main.py` → this is the mount prefix
3. Full path = Y + X + endpoint_path

**Why:** FastAPI combines both prefixes. Most routers in this project are mounted with `prefix="/api"`, so a router with `prefix="/training"` and a `GET /dataset/stats` endpoint becomes `/api/training/dataset/stats`.

**Exceptions:** 
- `auth.router` → registered with NO `prefix="/api"`, so routes are at `/auth/...`
- `ai_engine_router` (from `app/modules/ai/routes.py`) → registered with no additional prefix (already has `/api/ai-engine/` built in)
- `blockchain_router`, `training_module_router` → registered with no extra prefix (self-contained)
