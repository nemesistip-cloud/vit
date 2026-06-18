## 2026-06-16 - [Notification Accessibility & Empty State]
**Learning:** Icon-only buttons in notification headers (Mark Read, Settings) were missing descriptive ARIA labels, making them invisible to screen readers. Additionally, a simple text "No notifications" didn't provide enough guidance for a good user experience.
**Action:** Always add `aria-label` to header action buttons and use a visual `EmptyState` component with an icon and helpful description to guide the user when no data is present.

## 2026-06-17 - [Icon-Only Button Accessibility Pattern]
**Learning:** Found a recurring pattern of icon-only buttons (Logout, Close, Copy, Share) lacking `aria-label` attributes across several core pages (Layout, Referral, Watchlist). These buttons are functional but silent for screen reader users.
**Action:** Consistently audit interactive `Button` components with `size="icon"` and ensure they have descriptive `aria-label` or `title` props.

## 2026-06-17 - [Global Tooltip Integration]
**Learning:** Icon-only buttons with 'aria-label' provide accessibility but lack visual clarity for sighted users on hover. Integrating Radix Tooltips globally in core components (Layout, NotificationBell) provides a consistent UX where users can confidently identify actions (Logout, Theme Toggle, etc.) without relying solely on icon recognition.
**Action:** Wrap global icon-only actions in 'Tooltip' components from '@ui/tooltip' to bridge the gap between accessibility (aria-label) and visual discoverability.

## 2026-06-18 - [Accessible Dynamic Labels for FABs]
**Learning:** Using a static `aria-label` on a button with dynamic child content (like a count badge) causes screen readers to ignore the dynamic information.
**Action:** Always include dynamic state (counts, statuses) within the `aria-label` string for interactive elements that use badges or overlay icons to convey information.
