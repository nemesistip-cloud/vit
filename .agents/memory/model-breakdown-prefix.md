---
name: Model breakdown double-prefix
description: APIRouter prefix must not duplicate the prefix already applied in include_router.
---

## Rule
When `app.include_router(router, prefix="/api")` is used in `main.py`, the router's own `prefix` must NOT also start with `/api/`.

**Why:** `model_breakdown.py` had `prefix="/api/ai-engine"` but was mounted with `prefix="/api"`, creating routes at `/api/api/ai-engine/...` (404 for all 4 ML Accountability endpoints).

**How to apply:** Router prefix = `/ai-engine`, mount prefix = `/api` → final route = `/api/ai-engine/...`. Check whenever adding a new router that the combined prefix is correct.
