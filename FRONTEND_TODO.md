# VIT Sports Intelligence Network — Frontend Audit & Master Prompt

**Audited:** April 24, 2026
**Scope:** `frontend/` (React 19 + Vite 6 + TS + Tailwind v4 + ShadCN, Wouter routing, TanStack Query, served by FastAPI on port 5000)
**Source of truth used for backend wiring:** `app/api/routes/*.py` and `app/modules/*/routes.py`

The frontend is roughly **90% complete**. Most pages are real and wired to working endpoints. The gaps below are what remains before it can be called feature-complete.

---

## 1. Compile / Type-Safety Gaps

| # | File:Line | Issue | Fix Hint |
|---|-----------|-------|----------|
| T-01 | `frontend/src/pages/matches.tsx:68-74` | `tsc --noEmit` fails: `new Map(...)` rejects the `[key, value]` tuples because `.map(...)` widens to `any[][]`. | Type the entry as `[string, string]`, e.g. `.map((m) => [(m as any).league_key ?? m.league, m.league] as [string, string])`. |

> Run from `frontend/`: `npx tsc --noEmit` — must come back with **0 errors** before merging.

---

## 2. Missing Backend Wiring (endpoints exist, no UI uses them)

These are real backend routes with no client call site — they need either an `apiGet/apiPost` helper in `frontend/src/api-client/index.ts` and a UI surface, or a panel inside `admin.tsx`.

| # | Backend Route | Where it should live |
|---|---------------|---------------------|
| W-01 | `POST /admin/calibration/fit` and `POST /admin/calibration/reload` (`app/api/routes/admin.py`) | New "ML Calibration" card in `admin.tsx` → System / ML tab. |
| W-02 | `POST /admin/settle-results` and `POST /admin/backfill-ft-results` (`app/api/routes/admin.py`) | New "Manual Settlement" card in `admin.tsx`. Confirm dialog + dry-run preview. |
| W-03 | `POST /admin/accumulator/place-bet` and `POST /admin/accumulator/send` (`app/api/routes/admin.py`) | "Global Accumulator" admin panel — composer + broadcast button. |
| W-04 | `GET /analytics/roi` and `GET /analytics/clv` (`app/api/routes/analytics.py`) | Two new tabs/cards in `analytics.tsx` (currently only `/analytics/my` is consumed). |
| W-05 | `GET /ai/performance`, `GET /ai/report` (`app/api/routes/ai.py`) | Per-model accuracy table on the `analytics.tsx` "Models" tab; also surface in `admin.tsx` ML view. |
| W-06 | `GET /odds/injuries` and `GET /odds/audit-log` (`app/api/routes/odds_compare.py`) | "Injuries" sub-tab in `match-detail.tsx`; admin-only audit log view. |
| W-07 | `app/api/routes/ai_feed.py` (manual consensus push) | Optional admin tool; small form in `admin.tsx`. |
| W-08 | `app/api/routes/audit.py` (whole router) | New "Audit Log" tab inside `admin.tsx` with filters (actor, action, date range, target). |
| W-09 | `app/api/routes/exports.py` | "Export" buttons (CSV / JSON) on `predictions.tsx`, `wallet.tsx`, and `analytics.tsx`. |

---

## 3. Page-Level Functionality Gaps

| # | Page | Gap | What "done" looks like |
|---|------|-----|------------------------|
| P-01 | `predictions.tsx:520-524` | Hard-coded "Coming soon" pill for unsupported markets (BTTS variants, AH, etc.). | Implement those market views OR move the unsupported list to backend `/predictions/markets/supported` so the frontend doesn't drift. |
| P-02 | `odds.tsx` (Arbitrage tab) | Tab exists but does not display arb edges, stake split, or guaranteed return — just lists books. | Call `/odds/arbitrage`, render: edge %, suggested stake-split per outcome, guaranteed profit. |
| P-03 | `admin.tsx` | 1,860 lines but missing: calibration controls (W-01), manual settlement (W-02), global accumulator broadcast (W-03), audit log (W-08), backend health drill-down (Redis status, SMTP status, supervisor task list). | Add the four panels above plus a "System Health" card that consumes `/admin/health` (or equivalent) and shows red/green per subsystem. |
| P-04 | `analytics.tsx` | Only consumes `/analytics/my`; missing ROI, CLV, model-attribution charts. | Add ROI tab (W-04), CLV tab (W-04), Per-Model Accuracy tab (W-05). |
| P-05 | `match-detail.tsx` | Rich match data but no injuries panel and no live odds-movement chart. | Wire `/odds/injuries` (W-06) + a sparkline that streams from the existing notifications WebSocket (`live_odds` channel). |
| P-06 | `wallet.tsx` | No CSV/JSON transaction export; no PnL summary by date range. | Add export button (W-09) + a date-range filter that hits `/wallet/transactions?from=&to=`. |
| P-07 | **No page** | Backend has Gemini configured (`GEMINI_API_KEY`) but there is **no AI assistant chat UI** in the frontend. The user's request literally starts with *"Connect with an AI Assistant"*. | New page `frontend/src/pages/assistant.tsx`, route `/assistant`, lazy-loaded in `App.tsx`. Chat thread persisted in localStorage; calls a new backend `/ai/assistant/chat` endpoint that proxies to Gemini and grounds the answer in the user's recent predictions/wallet. |

---

## 4. Cross-Cutting Frontend Issues

| # | File:Line | Issue | Fix |
|---|-----------|-------|-----|
| C-01 | `frontend/src/lib/apiClient.ts:46-47` | `refreshToken` swallows the catch silently — if the refresh endpoint 500s, the user just gets logged out with no telemetry. | Log via `console.error` and surface a one-time toast `"Session refresh failed — please sign in again."` before the redirect. |
| C-02 | `frontend/src/lib/auth.tsx:84` | `TIER_ORDER` is a hard-coded constant — adding a new subscription tier on the backend will silently break gating. | Fetch tier metadata from `/subscription/plans` once at boot and derive ordering. |
| C-03 | `frontend/src/lib/websocket.ts:44` | Single connection assumed; the internal `_emit` router conflates `notifications` and `live_odds`. | Split into two named channels with their own reconnect/back-off; keep the same exponential strategy already in place. |
| C-04 | `frontend/src/components/error-boundary.tsx:34` | The only `console.error` left in production code — fine, but it should also POST to `/admin/client-error` (or Sentry-equivalent) so we can see frontend crashes server-side. | Add a fire-and-forget `apiPost("/admin/client-error", { message, stack, url })` (gated to authenticated users). |
| C-05 | Missing UI for backend warnings: `SMTP_HOST`, `REDIS_URL`, `ANTHROPIC_API_KEY`. | Admins have no way to know these are missing without reading server logs. | Add a "Configuration Health" strip at the top of `admin.tsx` driven by a new `/admin/config-status` endpoint (or extend an existing one). Show amber for "missing optional", red for "missing required". |
| C-06 | No service worker / PWA manifest. | No offline state, no installable. | Optional: add a Vite PWA plugin with a network-first strategy for `/api/*` and stale-while-revalidate for static assets. |
| C-07 | No automated frontend tests. | Regressions ship unnoticed. | Add Vitest + React Testing Library; start with a smoke test per route plus the `apiClient.refreshToken` race. |

---

## 5. Polish / UX

| # | Where | Item |
|---|-------|------|
| U-01 | All long lists (`matches.tsx`, `predictions.tsx`, `marketplace.tsx`, `leaderboard.tsx`) | Add virtualization (`@tanstack/react-virtual`) — these can grow into the thousands. |
| U-02 | All forms | Standardize Zod schema imports — some pages do inline validation, others use `@hookform/resolvers/zod`. |
| U-03 | `Layout` (`frontend/src/components/layout.tsx`) | Mobile nav drawer is missing some routes added in v4.x (governance, bridge, trust). Audit nav items vs `App.tsx` route list. |
| U-04 | All pages | Add a global "Empty State" component used consistently when API returns `[]` (currently every page renders its own empty markup). |
| U-05 | Light/dark theme | Re-test contrast — several muted-foreground texts fail WCAG AA on light theme. |

---

## Master Prompt — paste this into Codespace AI

> Below is a single self-contained prompt. It tells the assistant the codebase shape, the conventions to follow, and exactly which gaps to close. It assumes the assistant has read/write access to the repo.

```
You are working in the VIT Sports Intelligence Network monorepo.

STACK
- Backend: Python 3.11, FastAPI, SQLAlchemy async, Alembic, Uvicorn (port 5000). Routes live in `app/api/routes/*.py` and `app/modules/*/routes.py`. Entry point is `main.py`.
- Frontend: React 19 + TypeScript + Vite 6, Tailwind v4, ShadCN UI, Wouter for routing, TanStack Query for data, Sonner for toasts, framer-motion for animation. Code is under `frontend/src/`. Built artifacts go to `frontend/dist/` and are served by FastAPI's SPA catch-all.
- Auth: JWT access + refresh tokens stored in localStorage (`vit_token`, `vit_refresh_token`). 2FA (TOTP) is enforced.
- API client: `frontend/src/lib/apiClient.ts` (`apiGet/apiPost/apiPatch/apiPut/apiDelete/apiFormPost`). Always use this — never raw `fetch`.
- Routing: every authenticated page is lazy-loaded in `frontend/src/App.tsx` and wrapped in `<Layout><ProtectedRoute component={X} /></Layout>`. Follow that pattern for any new page.

CONVENTIONS — DO NOT VIOLATE
1. No new raw `fetch` calls. Use `apiClient.ts`.
2. No mocked, hard-coded, or fake data. If a backend endpoint is missing, add it (FastAPI route + Pydantic model + tests) before wiring the UI.
3. Errors must be visible to the user via Sonner toast AND be loggable — never swallow with empty `catch {}`.
4. Every new page must be: (a) lazy-loaded in `App.tsx`, (b) added to the nav in `frontend/src/components/layout.tsx`, (c) protected with `ProtectedRoute` unless explicitly public.
5. Every new TanStack Query call must set a stable `queryKey` and respect the global `staleTime: 15_000`.
6. Style: Tailwind utility classes + ShadCN primitives only. Match the existing typography (mono labels, `text-xs/text-[10px]`, uppercase tracking-widest section headers).
7. TypeScript strictness: `npx tsc --noEmit` must pass with zero errors after each change.
8. Update `replit.md` when you add a new module, env var, or route group.

TASK LIST — execute in this order, one PR/commit per group

GROUP A — Compile fix (must be first)
- A1. Fix `frontend/src/pages/matches.tsx` line ~70: type the `Map` entries as `[string, string]` so `tsc --noEmit` is clean.

GROUP B — Backend wiring gaps (UI exists, endpoints don't reach it)
- B1. Add a "ML Calibration" card to `frontend/src/pages/admin.tsx` calling `POST /admin/calibration/fit` and `POST /admin/calibration/reload`. Show last-fit timestamp, per-model log-loss before/after, confirmation dialog before fit.
- B2. Add a "Manual Settlement" card to `admin.tsx` calling `POST /admin/settle-results` and `POST /admin/backfill-ft-results`. Provide a dry-run toggle and a summary of affected predictions.
- B3. Add a "Global Accumulator Broadcast" card to `admin.tsx` calling `POST /admin/accumulator/place-bet` and `POST /admin/accumulator/send`. Composer with leg picker, edge filter, target user segment.
- B4. Add `Roi` and `Clv` tabs to `frontend/src/pages/analytics.tsx` calling `GET /analytics/roi` and `GET /analytics/clv`. Use Recharts (already a dep). Time-range selector reused from existing `PerformanceTab`.
- B5. Add a "Per-Model Performance" table to `analytics.tsx` calling `GET /ai/performance` and a printable report from `GET /ai/report`.
- B6. Add an "Injuries" tab to `frontend/src/pages/match-detail.tsx` calling `GET /odds/injuries?match_id=...`. Cards grouped by team with severity color.
- B7. Add an "Audit Log" tab inside `admin.tsx` calling the routes in `app/api/routes/audit.py` with filters: actor, action, date range, target id. Paginated.
- B8. Add export buttons to `predictions.tsx`, `wallet.tsx`, `analytics.tsx` consuming `app/api/routes/exports.py`. Default CSV; JSON behind a dropdown.

GROUP C — Page features
- C1. Implement the unsupported markets listed at `frontend/src/pages/predictions.tsx:522` (BTTS variants, AH, etc.) end-to-end (backend scoring + UI rendering + tests). Replace the "Coming soon" copy with the real cards.
- C2. Build out the Arbitrage tab in `frontend/src/pages/odds.tsx` against `GET /odds/arbitrage`. Show edge %, stake-split per outcome, guaranteed profit, "copy bets" button.
- C3. Add a "Configuration Health" strip at the top of `admin.tsx` consuming a new `GET /admin/config-status` endpoint that reports SMTP, Redis, Anthropic, Stripe, Paystack, Football-Data status. Add the route to `app/api/routes/admin.py` if missing.
- C4. Create `frontend/src/pages/assistant.tsx` route `/assistant`: chat thread (persisted in localStorage), composer, streaming responses. Add backend `POST /ai/assistant/chat` (in `app/api/routes/ai.py` or a new `assistant.py`) that proxies to Gemini and grounds answers in the caller's recent predictions, wallet balance, and active subscriptions. Add to nav.

GROUP D — Cross-cutting infra
- D1. Update `frontend/src/lib/apiClient.ts` `refreshToken` to log failures to `console.error` and surface a one-time Sonner toast before redirecting to `/login`.
- D2. Update `frontend/src/lib/auth.tsx` to derive `TIER_ORDER` from `GET /subscription/plans` instead of the hard-coded constant. Cache in React context.
- D3. Refactor `frontend/src/lib/websocket.ts` into per-channel sockets (`notifications`, `live_odds`) with independent reconnect/back-off. Keep the existing exponential strategy.
- D4. In `frontend/src/components/error-boundary.tsx`, fire-and-forget `apiPost("/admin/client-error", { message, stack, url, user_agent })` for authenticated users. Add the route on the backend.

GROUP E — Polish
- E1. Audit the mobile nav in `frontend/src/components/layout.tsx` and add any routes from `App.tsx` that are missing (governance, bridge, trust, etc.). Same for desktop sidebar.
- E2. Extract a shared `<EmptyState />` component into `frontend/src/components/empty-state.tsx` and replace the per-page empty markup.
- E3. Add `@tanstack/react-virtual` and virtualize `matches.tsx`, `predictions.tsx`, `marketplace.tsx`, `leaderboard.tsx` lists when >100 items.
- E4. Add Vitest + React Testing Library. First tests: `apiClient.refreshToken` race condition, smoke render of every lazy page with a mocked auth context.

DEFINITION OF DONE per task
- `npx tsc --noEmit` passes from `frontend/`
- `npm run build` succeeds from `frontend/`
- The new behavior is reachable from the running app (start with the existing "Start application" workflow on port 5000)
- No new `console.log`. `console.error` only inside ErrorBoundary or telemetry helpers
- New backend routes have at least one pytest in `tests/`
- `replit.md` updated if you added an env var, route group, or new top-level module

OUT OF SCOPE
- Do NOT touch ML training code in `services/`, `pipeline.py`, `feature_engineering.py`, `optimizer.py`.
- Do NOT change blockchain modules (`app/modules/blockchain/`) — they are intentionally feature-flagged off.
- Do NOT migrate the database away from SQLite for development.

Start with GROUP A. After each group, run `npx tsc --noEmit && npm run build` from `frontend/` and `pytest -q` from the repo root. Report results before moving on.
```

---

## How to use this document

1. Skim section 1 — fix T-01 first, it's a one-line type fix that's blocking the type checker.
2. Decide which groups (B / C / D / E) you actually want; trim them out of the master prompt before pasting.
3. Paste the **Master Prompt** block (everything inside the ```​code fence```) into Codespace AI.
4. Have it work group-by-group; review each commit.
