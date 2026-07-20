# VIT Network — Interaction & Animation Architecture

**Version:** 6.0.0
**Domain:** /docs/frontend/
**Status:** Design Approved

---

## 1. Interaction Design Philosophy

Interaction design in the VIT Network is optimized for **speed, high response, and low latency**. Every animation and micro-interaction must serve a functional purpose: directing user attention, confirming transaction states, or highlighting real-time state changes. We completely avoid sluggish, heavy transitions in favor of crisp, spring-backed physics.

---

## 2. Micro-interactions & Core UI Transitions

### 2.1 Spring-Based Page Transitions
When navigating between pages or workspaces in the platform shell, content canvas areas transition smoothly using **Framer Motion**:
- **Animation Values:**
  - Initial state: `opacity: 0, y: 8`
  - Active state: `opacity: 1, y: 0`
  - Exit state: `opacity: 0, y: -8`
  - Spring constant: `type: "spring", stiffness: 380, damping: 30`
- This layout slide communicates hierarchy without feeling sluggish.

### 2.2 Hover Card Glow Effect
Analytical cards transition their borders to high-contrast blue (`vit-400`) upon hover:
```css
.card-hover-glow {
  transition: border-color 0.15s ease-out, box-shadow 0.15s ease-out;
}
.card-hover-glow:hover {
  border-color: rgba(95, 138, 255, 0.4);
  box-shadow: 0 0 16px rgba(95, 138, 255, 0.1);
}
```

---

## 3. Gestures & Touch Interactions (Mobile-First)

For tablet and mobile viewports, specific swipe gestures are registered to provide an app-native feel:

### 3.1 Swipe to Navigate
- **Action:** Swiping from the extreme left edge ($<20\text{px}$) of the screen to the right slides out the mobile sidebar navigation.
- **Action:** Swiping from right-to-left on active metrics cards switches the displayed dataset tab.

### 3.2 Drag-to-Refresh
- Swiping down beyond the scroll limits on the Main Dashboard page triggers an active refresh request (`tanstack-query` refetch), showing an emerald-colored rotating spinner.

---

## 4. Keyboard Shortcuts & Commands

To accommodate advanced traders and node operators, keyboard navigation is fully supported across all major page layers:

| Shortcut Trigger | Global Action | Focus Context |
| :--- | :--- | :--- |
| `Cmd+K` / `Ctrl+K` | Toggle Universal Command Palette | Global |
| `Option+W` | Toggle Workspace Switching Picker | Global |
| `Escape` | Dismiss active dialog, drawer, or modal | Global |
| `/` (Slash) | Focus the search input on active data tables | Workspace tables |
| `j` / `k` | Scroll down / up in item lists (e.g. proposals) | Focus list |
| `Enter` | Activate selected list item or submit dialog | Focus item |

---

## 5. Live Updates & Real-Time Syncing

VIT Network is a real-time system; data lists must never require manual page refreshes.

### 5.1 Real-Time WebSocket Channel Sync
When a WebSocket event is broadcast by the API backend (via `app/core/event_bus.py`), the React state updates instantly.
- **Visual Micro-interaction:** The affected table cell or metric displays an emerald flash (`bg-emerald-500/20`) for $500\text{ms}$ before fading back to transparency, highlighting live values.

### 5.2 Background Refetching Indicators
When TanStack Query runs a background refetch, a tiny, rotating double-arrow icon spins in the bottom-right corner of the layout, signaling that fresh data is loading without interrupting the active user session.
