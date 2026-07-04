# VIT Network Admin Panel Audit (v5.5.0)

This report outlines the current gaps, missing features, and recommended upgrades for the VIT Network Admin Panel, discovered during a comprehensive codebase audit.

## 1. Missing Features (Backend exists, Frontend is absent)
These modules have functional backend logic but no user interface in the Control Panel:

- **Task & Quest Engine (`app/api/routes/admin_tasks.py`):**
    - No UI to create, update, or delete platform tasks (e.g., "Daily Intelligence Check-in").
    - Missing visibility into task completion rates and user reward distributions.
- **Reward Review Terminal (`app/api/routes/admin_rewards.py`):**
    - No interface for admins to manually review, approve, or reject offerwall/referral reward completions.
    - Missing fraud detection flags or risk assessment UI for automated rewards.
- **Prediction Audit Diagnostics (`app/api/routes/admin_audit_predictions.py`):**
    - A backend tool exists to check for "broken" matches (missing probabilities for specific markets like BTTS or Over/Under), but it is not exposed in the UI.
- **KYC & Identity Verification Terminal:**
    - The `kyc` module and `User.is_verified` status are present in the backend, but there is no terminal for admins to review uploaded documents or manually verify user identities.
- **Manual CLV Backfill Granularity (`app/api/routes/admin_clv.py`):**
    - Backend supports manual re-calculation of Closing Line Value (CLV) scores, but the UI only provides a basic "Recalculate" button without granular controls or execution logs.

## 2. Incomplete Features (UI exists but is limited)
These pages are functional but lack "Institutional Grade" depth or complete integration:

- **Audit Log Visualizer (`AdminAuditLog.tsx`):**
    - The UI shows *what* action was taken but not *how* the data changed.
    - The `AdminJsonDiff.tsx` component exists but is not integrated to show field-level JSON diffs for config or user changes.
- **Market Mapping & Affiliate Analytics:**
    - Tables for `market_mappings` and `affiliate_clicks` exist in the database (`app/modules/sports/models.py`).
    - There is no admin dashboard to view CTR (Click-Through Rate), conversion analytics, or to manually manage provider-specific market links.
- **Governance & Academy Oversight:**
    - Modules for `governance` and `academy` exist in the backend, but the admin panel cannot manage curriculum articles, review community governance proposals, or update the "Campus" content.
- **Advanced User 360-View (`AdminUsers.tsx`):**
    - User management is restricted to basic role/ban toggles.
    - Missing a unified view of a user's transaction history, prediction performance charts, and session security logs in a single profile page.

## 3. Recommended New Features (Gaps)
Strategic additions missing from both layers that would enhance platform stability and institutional trust:

- **Live Worker Telemetry Dashboard:**
    - Real-time monitor for background workers (Celery/lifespan tasks), showing queue depth, task failure rates, and individual node heartbeats.
- **Global Kill-Switch Dashboard:**
    - A central panel to instantly toggle "Maintenance Mode" for specific modules (e.g., "Pause Withdrawals", "Disable Sports Sync", "Lock Marketplace") without code deployments or ENV restarts.
- **AI Shadow Mode Management:**
    - A UI to deploy and monitor new AI models in "shadow mode"—allowing them to generate predictions for internal audit without affecting user-visible signals.
- **Institutional Reporting Engine:**
    - One-click generation of PDF/CSV reports for regulatory compliance, tax-ready user activity summaries, and platform performance audits.

## 4. Upgrade Parts (UI/UX & Technical)
- **Visual Consistency (8pt System):**
    - Transition remaining `rounded-lg` elements to `rounded-sm` to match the institutional "Terminal" aesthetic.
    - Ensure all data metrics across all admin tabs use JetBrains Mono for precision.
- **Real-time Telemetry (WebSockets):**
    - Replace the current 15s/30s polling in the Health Dashboard and KPI cards with a WebSocket connection for sub-second updates.
- **Server-side Search & Pagination:**
    - Upgrade User and Audit Log tables from client-side filtering to server-side full-text search to handle scaling beyond 10k+ records.
- **Tachyon VESS Node Management:**
    - UI to view active Tachyon nodes, their storage health, and manually trigger file re-syncs if needed.
