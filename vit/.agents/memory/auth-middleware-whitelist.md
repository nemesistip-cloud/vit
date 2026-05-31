---
name: Auth middleware whitelist
description: Routes in _ALWAYS_OPEN in app/middleware/auth.py bypass JWT checks. Prefix matching means /api/ai catches /api/ai-upload.
---

## Rule
Any public (unauthenticated) route must be added to `_ALWAYS_OPEN` list in `app/middleware/auth.py`.

**Why:** The middleware uses `startswith()` matching. The protected prefix `/api/ai` matches `/api/ai-upload`, blocking unauthenticated access to the upload route even though the route handler has no auth dep. Explicit entries override this.

**How to apply:** When creating new public API routes under `/api/ai-*`, add explicit entries to `_ALWAYS_OPEN`. Current entries include:
- `/api/ai-upload` (explicit, overrides the `/api/ai` protected prefix)
- `/api/config/public`
- `/api/system/status`

**File:** `app/middleware/auth.py` — look for `_ALWAYS_OPEN` list near the top.
