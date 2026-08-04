# VIT Network — Platform Bug List & Multi-Phase Upgrade Plan
*Generated: 2026-08-04 | Scope: all 4 Render services + GitHub repo nemesistip-cloud/vit*

---

## 🔴 CRITICAL — Fixed in This Session

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

---

## 🔴 CRITICAL — Not Yet Fixed

| # | Service | File | Bug | Impact |
|---|---------|------|-----|--------|
| C9 | vitnetwork | `app/modules/analytics_studio/routes.py` | **ALL 5 analytics-studio endpoints return hardcoded mock/stub data** — synthetic sine-wave ROI, fake 13-model list, identical KPIs for every user, unused `db` parameter. Analytics Studio shows fabricated financial data to users | Users see fake 64.1% accuracy / +38.4% ROI regardless of actual prediction history |
| C10 | vitnetwork | `app/modules/ai/routes.py:154-230` | Model upload deserializes user-supplied `.pkl` via `joblib.load()` with no size limit, no checksum, no sandbox — **arbitrary code execution via pickle** | Full server RCE if model upload endpoint is reachable |
| C11 | vitnetwork | `app/modules/ai/routes.py:728-763` | `POST /models/register` has no `get_current_admin` dependency — any authenticated (possibly unauthenticated) user can register production AI models | Attacker can replace live prediction models |
| C12 | vitnetwork | `app/modules/wallet/routes.py:398-445` | DB insert failure rolls back but still returns `status: pending` with payment link — client told to pay against a transaction that was never persisted | Users pay money, no deposit recorded |

---

## 🟠 HIGH — Not Yet Fixed

| # | Service | File | Bug | Impact |
|---|---------|------|-----|--------|
| H1 | vitnetwork | `app/modules/wallet/routes.py:354-445` | Deposit accepts client-provided `amount`/`currency` without server-side validation; payment URL returned even when gateway init fails | Gateway/client amount divergence |
| H2 | vitnetwork | `app/modules/wallet/chain_bridge.py:37-160` | Balance debit/credit and transfer record handled without row locks or idempotency keys — concurrent transfers can double-spend | Race condition double-spend |
| H3 | vit-ai | `https://vit-ai.onrender.com/api/v1/models` | Returns 404 — models endpoint not registered or route prefix mismatch | AI model list unavailable |
| H4 | vitnetwork | `frontend/src/hooks/useAuth.ts` | No 401 handling, no token expiry detection, no auto-logout — expired token stays in localStorage and keeps being sent | Users see 401 errors on all authenticated API calls until manual logout |
| H5 | vitnetwork | `frontend/src/hooks/useFreemiumGate.ts:18-47` | Failed config query (`data = undefined`) treats ALL features as enabled (undefined keys default true) — feature gating silently bypassed on API failure | Free users access paid features when config API is down |
| H6 | vitnetwork | `app/api/routes/analytics.py:302-305,408-411` | Broad `except Exception` handlers return empty leaderboard with HTTP 200 — DB failures are invisible | Silent data loss masked as empty results |

---

## 🟡 MEDIUM

| # | Service | File | Bug | Impact |
|---|---------|------|-----|--------|
| M1 | vitnetwork | `frontend/src/components/ui/NotificationBell.tsx` | Mark-all/mark-one mutations ignore response status — failed mark-as-read silently appears to succeed | Notifications re-appear on refresh |
| M2 | vitnetwork | Multiple pages | `useEffect(() => { navigate('/login') })` redirect fires AFTER first render — component executes render cycle with undefined data before redirect | Crash window between mount and redirect |
| M3 | vit-storage | `/health` response | `redis: "not_configured_or_disconnected"` — Redis not connected on vit-storage service | Storage coordination degraded |
| M4 | vitnetwork | `frontend/.env.example` | `VITE_STORAGE_URL=https://vit-storage.onrender.com` — wrong URL (actual is `vit-storage-4trt.onrender.com`) | Misleads local dev setup |
| M5 | vitnetwork | `app/modules/analytics_studio/routes.py` | `db: AsyncSession = Depends(get_db)` injected but unused in all 5 endpoints (stub leftovers) | Dead dependency injection |
| M6 | vitnetwork | `scripts/render_deploy_api.sh` | Default service name was `vit-sports-analytics` (fixed in `8ceb3c8c`); confirm no other stale references | Deploy script reliability |
| M7 | vit-chain | Chain explorer | 1,718 blocks synced; no issues found — service healthy | — |

---

## 🟢 Backend Endpoints Status (unauthenticated probe)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /health` (all 4 services) | ✅ 200 | All healthy |
| `GET /ping` | ✅ 200 | |
| `GET /docs` | ✅ 200 | FastAPI docs available |
| `GET /api/matches` | ✅ 200 | Match data available |
| `GET /api/developer/plans` | ✅ 200 | Correct JSON shape |
| `GET /api/auth/me` (forged sub) | ✅ 401 | Fix C1 working |
| `POST /api/auth/login` | ✅ 401 | Correct |
| `POST /api/auth/register` | ✅ 422 | Validation working |
| `vit-chain /api/blocks` | ✅ 200 | 1718 blocks |
| `vit-ai /api/v1/models` | ❌ 404 | Route missing |
| `vit-storage /api/v1/files` | ❌ 200* | Auth required (correct) |
| All `/api/analytics-studio/*` | ⚠️ 401→stub data | Stub endpoints |

---

## 📋 Multi-Phase Upgrade Plan

### Phase 1 — Stability (Current Sprint, Days 1-3) ✅ Partially Done
- [x] Fix AnalyticsStudio null crashes (C1-C3)
- [x] Fix Ecosystem frozen GW constant (C4)
- [x] Fix AI routes IndentationError (C5)
- [x] Fix ActivityFeed / NotificationBell crashes (C6-C7)
- [x] Add VITE_ build-time env vars to render.yaml (C8)
- [ ] Fix analytics-studio backend stubs → real DB queries (C9)
- [ ] Fix AI model upload RCE (C10)
- [ ] Fix AI model register auth (C11)
- [ ] Fix wallet deposit state divergence (C12)

### Phase 2 — Security & Data Integrity (Days 4-7)
- [ ] Wallet: row-level locking + idempotency keys for bridge transfers (H2)
- [ ] Wallet: server-side amount/currency validation (H1)
- [ ] AI: admin-only model upload/register + artifact signing
- [ ] Auth: 401 interceptor → auto token refresh → auto-logout (H4)
- [ ] Feature gate: fail-closed when config API unavailable (H5)

### Phase 3 — AI & Predictions (Days 8-14)
- [ ] Connect analytics-studio to real `match_predictions` + results tables
- [ ] Fix `vit-ai /api/v1/models` 404 (route prefix mismatch)
- [ ] Wire AI training endpoints to vit-ai service
- [ ] Real-time match prediction pipeline
- [ ] Model performance tracking against actual results

### Phase 4 — Storage & Infrastructure (Days 15-21)
- [ ] Connect Redis to vit-storage service (currently disconnected)
- [ ] Fix `VITE_STORAGE_URL` in .env.example
- [ ] Implement real storage file list / upload endpoints on vitnetwork
- [ ] vit-storage: S3-compatible API health verification

### Phase 5 — UX & Polish (Days 22-30)
- [ ] Fix useEffect redirect race (render before redirect) across all auth-gated pages (M2)
- [ ] Add token expiry detection + silent refresh in useAuth (H4)
- [ ] Notification mark-read reliability (M1)
- [ ] Analytics leaderboard error masking (H6)
- [ ] Mobile app (vit-mobile repo) integration review

---

## 🚀 Commits Pushed This Session

```
ef8f2c1a  fix(infra): add VITE_ build-time env vars to render.yaml
3815a58c  fix(frontend): convert frozen GW constant to live function in Ecosystem
35c5a2c7  fix(frontend): null-safe field access in AnalyticsStudio
829ef2a1  fix(frontend): validate notifications API response is array
1429a983  fix(frontend): guard ActivityFeed non-array response + undefined item.action
b11aee69  fix(ai): correct indentation on data=await file.read()
```

*Deploy in progress: `dep-d9p13jna7a5s739q6o20` (queued from render.yaml commit)*
