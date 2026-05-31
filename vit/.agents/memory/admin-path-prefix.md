---
name: Admin panel path prefix bug
description: Frontend admin API calls must all use /api/admin/... prefix — apiClient adds no auto-prefix.
---

## Rule
Every call to an admin endpoint in `frontend/src/` must use the full path `/api/admin/...`.
`apiClient.ts` uses `${API_BASE}${path}` — no automatic `/api/` prefix is injected.

**Why:** The admin router has `prefix="/admin"` and is mounted with `prefix="/api"` in `main.py`, so all routes live at `/api/admin/...`. Frontend code that omits `/api/` hits the Vite dev server directly (no proxy match) and gets 404.

**How to apply:** When adding new admin calls in any `.tsx` or `.ts` file, always use `/api/admin/...`. Also applies to raw `fetch()` calls (e.g. CSV upload). The `localStorage` token key is `"vit_token"` — not `"token"` or `"access_token"`.

Files fixed: `admin.tsx`, `accumulator.tsx`, `training.tsx`, `api-client/index.ts`, `components/error-boundary.tsx`.
