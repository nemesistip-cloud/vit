# VIT Network — Design System Tokens & Guidelines

**Version:** 6.0.0
**Domain:** /docs/design-system/
**Status:** Canonical Reference

---

## 1. Design Language Foundations

The VIT Network design language is **dark-first, high-density, and glass-morphic**. It is engineered to support professional analytics, real-time telemetry, and institutional-grade trust. The aesthetic borrows heavily from high-end developer platforms and real-time trading dashboards.

---

## 2. Global Color Token Matrix

Colors are defined as semantic Tailwind tokens to allow consistent usage across all workspaces:

### 2.1 Brand & Accent Palette (VIT Blue)
| Token Name | Hex Code | Tailwind Equivalent | Primary Usage |
| :--- | :--- | :--- | :--- |
| `vit-300` | `#93b4ff` | `text-blue-300` | Text gradients, secondary hyperlinks |
| `vit-400` | `#5f8aff` | `text-blue-400` | Active icons, small labels, action tooltips |
| `vit-500` | `#3b65ff` | `bg-blue-500` | Primary action background, brand button base |
| `vit-600` | `#2247f5` | `bg-blue-600` | Primary buttons, active state indicators |
| `vit-700` | `#1a35e1` | `bg-blue-700` | Button hover states, focus indicator borders |

### 2.2 Surface & Dark Palette (Dark Themes)
Our core layout is built on a rich, cold slate palette:
| Token Name | Hex Code | Tailwind Equivalent | Primary Usage |
| :--- | :--- | :--- | :--- |
| `surface-950` | `#05070a` | `bg-slate-950` | Global canvas backdrop (page body) |
| `surface-900` | `#0a0d14` | `bg-slate-900` | Main navbar, sidebars, dashboard backdrops |
| `surface-800` | `#0f1520` | `bg-slate-800` | Card container panels, form backdrops |
| `surface-700` | `#141c2e` | `border-slate-700` | Cards borders, subtle dividing rules |
| `surface-600` | `#1a2540` | `bg-slate-600/50` | Highlighted rows, active sidebar states |

### 2.3 Semantic Status Palette
| Semantic Meaning | Core Color | Usage Example |
| :--- | :--- | :--- |
| **Healthy / Success** | Emerald (`#10b981`) | Operational nodes, confirmed transaction pings |
| **Degraded / Warn** | Amber (`#f59e0b`) | Partial sync latency, unverified DID profiles |
| **Unhealthy / Fail** | Crimson (`#ef4444`) | Disconnected Redis, validator stake slashes |

---

## 3. Typography & Grids

### 3.1 Typography Scale
- **Primary Body & Interface:** **Inter** (weights: $400$ regular, $500$ medium, $600$ semi-bold, $700$ bold).
- **Tabular Data, Code, & Latencies:** **JetBrains Mono** (monospaced to keep numeric columns perfectly aligned).
- **Scale Tokens:**
  - Display Title: `text-4xl tracking-tight font-extrabold`
  - Workspace Title: `text-2xl tracking-tight font-semibold`
  - Metric Label: `text-xs uppercase tracking-wider font-medium text-slate-400`

### 3.2 High-Density Grid System
Layouts are built on an 8-pixel grid increment to maintain absolute spacing consistency:
- Section Padding: `p-4` (16px) or `p-6` (24px).
- Between-Card Spacing: `gap-4` (16px) or `gap-6` (24px).
- Horizontal Grid Columns: 12-column layout with customizable spans (`col-span-1` through `col-span-12`).

---

## 4. Light Theme Strategy (Enterprise Fallback)

While VIT is designed dark-first, corporate enterprise compliance requires a functional **Light Theme**. Light theme token mapping swaps slate backdrops for high-contrast white and gray equivalents:
- Global Backdrop: `bg-slate-50` (instead of `surface-950`).
- Card Container Panels: `bg-white` with subtle drop shadows (`shadow-sm shadow-slate-100`).
- Border Tokens: `border-slate-200` (instead of `border-surface-700`).
- Text Elements: `text-slate-900` (instead of `text-slate-100`).

---

## 5. Motion, Elevation, & Shadows

### 5.1 Elevation Layers
- **Base Canvas:** `z-0`
- **Standard Cards:** `z-10`
- **Navbar / Sidebar:** `z-30`
- **Slide-out Drawers:** `z-40`
- **Modals & Overlays:** `z-50`

### 5.2 Motion Guidelines
VIT uses **Framer Motion** to drive transitions. Animation durations are kept short to maintain a highly responsive feel.
- **Page Transitions:** `duration: 0.15s` with `easeOut` easing.
- **Card Hover Glow:** Slight border-color transition and scale increase (`scale-101`) over `0.2s`.
- **Live Status Pulsation:**
  ```css
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: .4; transform: scale(1.1); }
  }
  ```

---

## 6. Mobile-First Interaction Rules

To maintain usability on mobile and tablet devices, the UI adheres to 3 strict constraints:
1. **Minimum Touch Target:** All interactive buttons and selectors must have a minimum dimensions of **44x44 pixels**.
2. **Horizontal Overflow Swiping:** Tables and tab bars on mobile viewports must utilize `overflow-x-auto` with native momentum scrolling enabled (`-webkit-overflow-scrolling: touch`).
3. **Drawer-over-Modal Pattern:** Modals displayed on desktop views translate automatically into bottom-anchored slide-up sheet drawers on viewport sizes $<640\text{px}$.
