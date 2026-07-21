# VIT Network — Workspace Layout Framework

**Version:** 6.0.0
**Domain:** /docs/frontend/
**Status:** Layout Spec Approved

---

## 1. The Reusable Workspace Template

To keep layouts consistent across all 100+ planned workspaces, every page must inherit from a standardized **Workspace Template Framework**. The template provides standard coordinates for controls, data grids, toolbars, and contextual metadata, allowing users to switch workspaces with zero cognitive friction.

---

## 2. Standardized Layout Grid & Columns

The standard workspace layout uses a 3-column structural layout mapped on a flex grid:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  WORKSPACE HEADER (Title, Active Breadcrumbs, Live Status Pill)                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  TOOLBAR (Search Input, Quick Action Buttons, Filter Dropdowns)                        │
├─────────────────────────────────┬──────────────────────────────────────────────────────┤
│                                 │                                                      │
│  MAIN CANVAS AREA               │  CONTEXTUAL RIGHT SIDE DRAWER                        │
│  (Data Grids, Recharts Canvas,  │  (AI Insights, Activity Logs, Settings,              │
│   Metric Groups)                │   Help Documentation)                                │
│                                 │                                                      │
└─────────────────────────────────┴──────────────────────────────────────────────────────┘
```

### 2.1 Workspace Header
- **Breadcrumbs:** Displays current workspace location (e.g. `Platform / Sports Intelligence / Calibration`).
- **Live Status Pill:** Displays the real-time operational status of the subsystem feeding the workspace (e.g., green pulsating `CHAIN ONLINE` or amber `STORAGE SYNCING`).

### 2.2 Workspace Toolbar
- **Unified Search:** Quick search box that filters the main canvas lists.
- **Action Group:** Button hub featuring primary and secondary actions (e.g. "Create Proposal", "Ingest Dataset").
- **Filters:** Category-specific filters (e.g., date ranges, sport category, provider selection).

### 2.3 Main Canvas Area
- The core display area. Spans the remaining width of the viewport. Supports grid columns from 1 to 4 depending on card densities.

### 2.4 Contextual Right Drawer
- **Aesthetic:** Collapsible panel (`w-80` on desktop, hidden by default on tablet and mobile) used for contextual insights.
- Includes dynamic AI-generated text feeds or diagnostic statistics.

---

## 3. Responsive Breakpoint Mapping

To guarantee performance and usability on all consumer hardware, layouts dynamically adapt using strict CSS media query breakpoints:

| Device Class | Viewport Range | Layout Adjustments | Sidebar State |
| :--- | :--- | :--- | :--- |
| **Desktop** | $\ge 1024\text{px}$ | Standard 3-column layout, full width main canvas, visible right drawer | Sidebar pinned open (`w-64`) |
| **Tablet** | $768\text{px} \le w < 1024\text{px}$ | Left side navigation collapses; right contextual drawer moves into scrollable accordion panels below main content | Sidebar is sliding-drawer |
| **Mobile** | $< 768\text{px}$ | All content stacks vertically; 1-column layouts; minimum touch targets set to 44px; tables get horizontal overflow | Sidebar hidden, toggled via hamburger |

---

## 4. State Management Integration

Workspace states are synchronized across the layout using React context and TanStack Query:

```typescript
interface WorkspaceState {
  currentFilter: string;
  searchQuery: string;
  isRightDrawerOpen: boolean;
  setFilter: (filter: string) => void;
  setSearchQuery: (query: string) => void;
}
```

By enforcing this structural framework, any new workspace can be introduced into the VIT Network codebase inside of a single file, eliminating CSS redundancy and preserving design consistency.
