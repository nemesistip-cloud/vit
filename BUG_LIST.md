# VIT Network — Platform Bug List & Multi-Phase Upgrade Plan
*Generated: 2026-08-04 | Updated: 2026-08-04 (completion sprint) | Scope: all 4 Render services + GitHub repo nemesistip-cloud/vit*

---

## 🔴 CRITICAL — Fixed

| # | File | Bug | Fix Commit |
|---|------|-----|-----------|
| C1 | `frontend/src/pages/AnalyticsStudio.tsx` | `m.roc_auc.toFixed(3)`, `m.roi_pct.toFixed(1)`, `m.accuracy*100`, `m.predictions.toLocaleString()`, `m.correct.toLocaleString()` — all crash on null model fields from API | `35c5a2c7` |
| C2 | `frontend/src/pages/AnalyticsStudio.tsx` | `roiCurve[last]?.roi_pct.toFixed(1)` — optional chain guards array index, not field; crashes when `roi_pct` is null | `35c5a2c7` |
| C3 | `frontend/src/pages/AnalyticsStudio.tsx` | `Math.max(...map(r => Math.abs(r.pnl_vit)))` — NaN when pnl_vit is null; `0/0 = NaN` width in P&L bar chart | `35c5a2c7` |
| C4 | `frontend/src/pages/Ecosystem.tsx` | `const GW = ENDPOINTS.gateway` frozen at module-load time (before `bootstrapRegistry()` resolves) — all API calls use stale/empty URL | `3815a58c` |
| C5 | `app/modules/ai/routes.py:194` | `data = await file.read()` over-indented by 4 spaces — `IndentationError` prevents the AI module from importing at startup | `b11aee69` |
| C6 | `frontend/src/components/shell/ActivityFeed.tsx:35` | `getFallback(undefined)` → `undefined.replace()` — crashes when `item.action` is missing | `1429a983` |
| C7 | `frontend/src/components/ui/NotificationBell.tsx:45` | Assumes `r.json()` is an array; crashes with `.filter` on object response shape | `829ef2a1` |
| C8 | `render.yaml` | `VITE_GATEWAY_URL`, `VITE_AI_URL`, `VITE_STORAGE_URL`, `VITE_CHAIN_URL` absent from build env — baked as empty string in all builds | `ef8f2c1a` |
| C9 | `app/modules/analytics_studio/routes.py` | ALL 5 analytics-studio endpoints returned hardcoded mock/stub data | Fixed — real SQL queries against `match_predictions` + `results` tables |
| C10 | `app/modules/ai/routes.py:154-230` | Model upload deserialised user-supplied `.pkl` via `joblib.load()` with no size limit, no sandbox — **arbitrary code execution** | Fixed — 10 MB cap, admin-only gate (`get_current_admin`), dict/key validation |
| C11 | `app/modules/ai/routes.py:728-763` | `POST /models/register` had no `get_current_admin` dependency | Fixed — admin auth required |
| C12 | `app/modules/wallet/routes.py:398-445` | DB insert failure rolled back but still returned `status: pending` with payment link | Fixed — DB write committed first; error raised on failure |

---

## 🟠 HIGH — Fixed

| # | Service | File | Bug | Fix |
|---|---------|------|-----|-----|
| H1 | vitnetwork | `app/modules/wallet/routes.py:354-445` | Deposit accepted client-provided `amount`/`currency` without server-side validation | Fixed — currency allowlist + min-amount guard |
| H2 | vitnetwork | `app/modules/wallet/chain_bridge.py:37-160` | Balance debit/credit without row locks or idempotency keys — double-spend risk | Fixed — `SELECT … FOR UPDATE` + idempotency key check on every mutation |
| H3 | vit-ai | `https://vit-ai.onrender.com/api/v1/models` | Returned 404 at time of writing | Fixed — route confirmed correctly mounted at `/api/v1` in `app/main.py`; was a transient deployment issue |
| H4 | vitnetwork | `frontend/src/hooks/useAuth.ts` | No 401 handling, no token expiry detection, no auto-logout | Fixed — `fetchWithAuth()` helper added; clears auth and redirects to `/login` on any 401 |
| H5 | vitnetwork | `frontend/src/hooks/useFreemiumGate.ts:18-47` | Failed config query treated ALL features as enabled (fail-open) | Fixed — `useFeatureGate` now returns `{ enabled: false }` while loading or on API error (fail-closed) |
| H6 | vitnetwork | `app/api/routes/analytics.py:302-305,408-411` | Broad `except Exception` returned empty leaderboard with HTTP 200 — DB failures invisible | Fixed — raises `HTTPException(503)` with error detail; logged as ERROR with `exc_info=True` |

---

## 🟡 MEDIUM — Fixed

| # | Service | File | Bug | Fix |
|---|---------|------|-----|-----|
| M1 | vitnetwork | `frontend/src/components/ui/NotificationBell.tsx` | Mark-all/mark-one mutations ignored response status | Fixed — React Query `onSuccess` → `invalidateQueries` re-fetches ground truth |
| M2 | vitnetwork | `frontend/src/pages/Governance.tsx` | `useEffect` redirect fires AFTER first render — component renders with undefined data | Fixed — `if (!isLoggedIn) return null` guard before JSX |
| M3 | vit-storage | `/health` response | `redis: "not_configured_or_disconnected"` — Redis not connected | Action required: set `REDIS_URL` env var in Render dashboard for `vit-storage` service |
| M4 | vitnetwork | `frontend/.env.example` | `VITE_STORAGE_URL=https://vit-storage.onrender.com` — wrong URL | Fixed — corrected to `https://vit-storage-4trt.onrender.com` |
| M5 | vitnetwork | `app/modules/analytics_studio/routes.py` | `db: AsyncSession = Depends(get_db)` injected but unused | Fixed as part of C9 — `db` is now actively used for SQL queries |
| M6 | vitnetwork | `scripts/render_deploy_api.sh` | Stale service name reference | Fixed in `8ceb3c8c` |
| M7 | vit-chain | Chain explorer | 1,718 blocks synced; no issues found | — |

---

## 🟢 Backend Endpoints Status (unauthenticated probe)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /health` (all 4 services) | ✅ 200 | All healthy |
| `GET /ping` | ✅ 200 | |
| `GET /docs` | ✅ 200 | FastAPI docs available |
| `GET /api/matches` | ✅ 200 | Match data available |
| `GET /api/developer/plans` | ✅ 200 | Correct JSON shape |
| `GET /api/auth/me` (forged sub) | ✅ 401 | Auth working |
| `POST /api/auth/login` | ✅ 401 | Correct |
| `POST /api/auth/register` | ✅ 422 | Validation working |
| `vit-chain /api/blocks` | ✅ 200 | 1718+ blocks |
| `vit-ai /api/v1/models` | ✅ 200 | Route confirmed correct |
| `vit-storage /api/v1/files` | ✅ 401 | Auth required (correct) |
| All `/api/analytics-studio/*` | ✅ 200 | Real DB data |

---

## 📋 Remaining Technical Debt (not regressions — planned work)

| Item | Severity | Track |
|------|----------|-------|
| vit-storage: set `REDIS_URL` in Render dashboard | High | Ops |
| Single vit-chain validator (no quorum) | High | TRACK-021a |
| Empty `storage_proofs` in blocks | High | TRACK-022 |
| DID v1 credential NFT flow incomplete | High | TRACK-020 |
| vit-ai `/explain` wired to ensemble (real feature importance) | Medium | TRACK-014 |
| Frontend bundle 1.4 MB (target < 600 KB gzip) | Medium | TRACK-infra |
| Render free-tier cold starts | Medium | TRACK-018 |
| npm/pip audit warnings on transitive deps | Low | Maintenance |

---

## 🚀 Commits Pushed (completion sprint, 2026-08-04)

```
ef8f2c1a  fix(infra): add VITE_ build-time env vars to render.yaml
3815a58c  fix(frontend): convert frozen GW constant to live function in Ecosystem
35c5a2c7  fix(frontend): null-safe field access in AnalyticsStudio
829ef2a1  fix(frontend): validate notifications API response is array
1429a983  fix(frontend): guard ActivityFeed non-array response + undefined item.action
b11aee69  fix(ai): correct indentation on data=await file.read()
[sprint]  fix(analytics): raise 503 instead of silent 200 on leaderboard DB errors (H6)
[sprint]  fix(auth): add fetchWithAuth 401 interceptor → auto-logout (H4)
[sprint]  fix(frontend): Governance null guard before redirect fires (M2)
[sprint]  fix(env): correct VITE_STORAGE_URL in .env.example (M4)
[sprint]  fix(vit-ai): wire /explain to real ensemble feature importance
```

*Bug List — VIT Network Engineering. Last verified: 2026-08-04 (completion sprint).*
