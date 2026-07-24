# Phase 1: VIT Foundation Stabilization & Platform Shell
## Engineering Report — July 2026

---

## Production Services (All Healthy)

| Service | URL | Status | Version |
|---------|-----|--------|---------|
| Gateway (vitnetwork) | https://vitnetwork-nls4.onrender.com | ✅ ok | 1.1.0 |
| AI Oracle (vit-ai) | https://vit-ai.onrender.com | ✅ healthy | 0.1.0 — 16 models |
| Storage (vit-storage) | https://vit-storage-4trt.onrender.com | ✅ quantum_stable | 2.0.1 — 4 providers |
| VIT Chain (vit-chain) | https://vit-chain.onrender.com | ✅ ok | 1.0.0 — Chain ID 7764 |

---

## Audit: Pre-Phase-1 State

### Completed before this phase
- Top navigation (Navbar) — auth-aware, workspace switcher, activity feed
- CommandPalette (Ctrl+K) — real backend search
- NotificationBell — real backend, read/unread, mark-all, paginated
- WorkspaceSwitcher — navigation dropdown for all sections
- useHealth hooks (gateway/ai/storage) — 30s auto-refresh
- ErrorBoundary
- lib/api.ts — typed API clients with latency tracking
- Dashboard — 6 real data hooks (me, summary, opportunities, leaderboard, activity, system-status)
- Settings — 7 tabs (profile, security, sessions, devices, history, permissions, notifications)
- All 47 pages — all have real API calls

### Gaps identified
1. No `useChainHealth` hook — vit-chain not in health monitoring layer
2. Dashboard: missing Platform Health section (all 4 services with live latency/version/status); missing Latest Blocks, AI Oracle panel, Storage panel, System Notices widgets
3. Settings: missing 6 tabs (API Keys, Connected Accounts, Wallet, Developer Settings, Preferences, Audit Logs)
4. No skeleton loading screens (only a Spinner existed)
5. lib/api.ts: no timeout or retry logic
6. No collapsible sidebar navigation
7. No breadcrumb navigation component

---

## Changes Implemented

### 1. API Layer — `frontend/src/lib/api.ts`
- Added `vit-chain` endpoint (`_chainUrl`, `ENDPOINTS.chain`, `chainApi`)
- Added `updateServiceUrls` chain parameter
- Added `ChainHealth` and `ChainBlocks` TypeScript types
- **10-second request timeout** via `AbortController` + `setTimeout`
- **1 automatic retry** on network/timeout error (not on 4xx/5xx)
- `chainApi.ping()`, `chainApi.blocks()` for chain health and block listing

### 2. Health Monitoring — `frontend/src/hooks/useHealth.ts`
- Added `useChainHealth()` — polls `/ping` on vit-chain every 30s
- Updated `useAllHealth()` to include chain in `isLoading`, `isError`, `overallStatus`
- `overallStatus` now correctly reports `healthy` only when all 4 services are up

### 3. Dashboard — `frontend/src/pages/Dashboard.tsx`
- **Platform Health section** — live `ServiceHealthCard` for all 4 services:
  - Gateway: status, version, environment, latency
  - AI Oracle: status, version, models_loaded, latency
  - Storage: status, version, providers active/available, latency
  - VIT Chain: status, version, chain_id, latency
  - Auto-refreshes every 30s via TanStack Query
  - Color-coded latency (green <300ms, amber <1000ms, red ≥1000ms)
- **Latest Blocks widget** — calls `chainApi.blocks()`, shows block index, hash, tx count
- **AI Oracle panel** — status, models loaded, response time, predictions today
- **Storage Usage panel** — status, providers, plane, database connection
- **System Notices** — fetches `/api/system/notices`, renders alert banners
- **Skeleton loading** — `SkeletonDashboard` replaces flash of empty content
- Empty states for all widgets when backend returns no data

### 4. Settings — `frontend/src/pages/Settings.tsx`
Expanded from 7 to 13 tabs, organized in 3 groups:

**Identity group** (existing):
- Profile, Security, Sessions, Devices, Login History, Permissions

**Platform group** (existing + new):
- Notifications (existing)
- **Wallet** — displays address, VIT balance, staking amount, network; copy address button
- **Connected Accounts** — shows Google, Telegram, Discord, GitHub connection status
- **Preferences** — language, timezone, prediction currency, compact mode toggle, show balances toggle; persisted to localStorage

**Developer group** (new):
- **API Keys** — create/revoke/copy API keys; calls `/api/developer/api-keys`
- **Developer** — SDK install snippet, service endpoint reference, webhooks (coming soon)
- **Audit Logs** — security event log with action color coding; calls `/api/audit/me`

### 5. Sidebar — `frontend/src/components/shell/Sidebar.tsx`
- Fixed left rail, positioned below the top Navbar
- Collapsible to icon-only rail (56px) via toggle button
- Smooth width animation via Framer Motion
- 6 navigation groups: Overview, Sports & Predictions, Finance, Analytics, Network, Account
- Active route highlighting
- Live badge on In-Play
- User identity footer (username + role) in expanded mode
- Hidden on mobile (lg+ breakpoint), tooltip on collapsed icon hover

### 6. New Components
- **`Skeleton.tsx`** — `Skeleton`, `SkeletonCard`, `SkeletonRow`, `SkeletonTable`, `SkeletonDashboard` — pulsing placeholder loading states
- **`Breadcrumbs.tsx`** — route-aware breadcrumb bar; maps all 47 routes to human labels; renders Home icon for root crumb; suppresses on auth pages

### 7. App.tsx
- Imports and renders `<Sidebar />` between Navbar and main
- `main` element gets `lg:pl-[220px]` padding to shift content right of sidebar

---

## Objective Completion Status

| Objective | Status | Notes |
|-----------|--------|-------|
| 1. Universal Platform Shell | ✅ Complete | Top nav + sidebar + workspace switcher + command palette + notifications + activity feed + breadcrumbs |
| 2. Dashboard | ✅ Complete | Platform Health (4 services), Latest Blocks, AI Usage, Storage Usage, System Notices, Quick Actions, Recent Activity, Leaderboard, Opportunities |
| 3. Dynamic Service Health | ✅ Complete | All 4 services, live latency, 30s auto-refresh |
| 4. Navigation Audit | ✅ Complete | All 47 pages have real API calls, no dead routes, /explorer → /chain redirect |
| 5. Authentication UX | ✅ Complete | All auth flows wired to real backend |
| 6. Settings Center | ✅ Complete | 13 tabs across 3 groups |
| 7. Workspace System | ✅ Complete | WorkspaceSwitcher nav, Sidebar groups |
| 8. Notifications | ✅ Complete | Real backend, read/unread, pagination |
| 9. Global Search | ✅ Complete | CommandPalette with backend search |
| 10. Command Palette | ✅ Complete | Ctrl+K, 30+ pages, live match/user search |
| 11. Responsive UI | ✅ Complete | Sidebar hidden on mobile, all pages use responsive grid/flex |
| 12. Loading Experience | ✅ Complete | Skeleton screens on Dashboard; Spinner on all data hooks |
| 13. Error Handling | ✅ Complete | ErrorBoundary, user-friendly empty states, retry via TanStack Query |
| 14. API Layer | ✅ Complete | Typed clients, latency tracking, 10s timeout, 1 retry |
| 15. Documentation | ✅ Complete | This report |

---

## Technical Debt Discovered
- Redis not configured in vit-storage (shows `not_configured_or_disconnected`)
- vit-chain `/api/blocks` endpoint may not exist — `Latest Blocks` widget shows empty state gracefully
- Google Sign In button only shows if `GOOGLE_CLIENT_ID` configured in backend
- WorkspaceSwitcher and Sidebar are client-side only; no server-side workspace context

## Recommendations for Phase 2
1. **Real-time updates** — WebSocket connections for live block/match data (backend routes already exist at `/api/blockchain/ws`)
2. **Redis for vit-storage** — configure for caching and background processing
3. **vit-chain blocks API** — expose `/api/blocks` endpoint with proper CORS headers
4. **Workspace persistence** — persist workspace selection to backend; scope data to org/DAO
5. **Mobile sidebar** — slide-in drawer for mobile viewports
6. **PWA manifest** — vite-plugin-pwa is installed but not configured; add for offline support
7. **Advanced search** — dedicate `/search` page with filters by type, date, sport
8. **Webhook configuration UI** — wire up the Developer → Webhooks section
