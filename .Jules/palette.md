## 2026-06-16 - [Notification Accessibility & Empty State]
**Learning:** Icon-only buttons in notification headers (Mark Read, Settings) were missing descriptive ARIA labels, making them invisible to screen readers. Additionally, a simple text "No notifications" didn't provide enough guidance for a good user experience.
**Action:** Always add `aria-label` to header action buttons and use a visual `EmptyState` component with an icon and helpful description to guide the user when no data is present.

## 2026-06-17 - [Icon-Only Button Accessibility Pattern]
**Learning:** Found a recurring pattern of icon-only buttons (Logout, Close, Copy, Share) lacking `aria-label` attributes across several core pages (Layout, Referral, Watchlist). These buttons are functional but silent for screen reader users.
**Action:** Consistently audit interactive `Button` components with `size="icon"` and ensure they have descriptive `aria-label` or `title` props.

## 2026-06-17 - [Global Tooltip Integration]
**Learning:** Icon-only buttons with 'aria-label' provide accessibility but lack visual clarity for sighted users on hover. Integrating Radix Tooltips globally in core components (Layout, NotificationBell) provides a consistent UX where users can confidently identify actions (Logout, Theme Toggle, etc.) without relying solely on icon recognition.
**Action:** Wrap global icon-only actions in 'Tooltip' components from '@ui/tooltip' to bridge the gap between accessibility (aria-label) and visual discoverability.

## 2026-06-18 - [Fixing Redundant Icon Aliases]
**Learning:** Using redundant aliases in imports (e.g., `Zap as Zap`) can cause build failures in certain environments or with stricter linters/transpilers, even if they seem benign in dev. It clutters the namespace and increases the risk of naming collisions.
**Action:** Always prefer clean imports and only use `as` aliases when there is a genuine naming conflict to resolve.

## 2026-06-18 - [Migration to VIT Network]
**Learning:** Redundant icon aliases in Lucide-React imports (e.g., `Zap as ZapIcon` when `Zap` is also imported) can cause build failures in certain environments or configurations (like Render's production build) even if they seem valid in development. Always ensure icon imports are clean and unambiguous.
**Action:** Use a centralized `Icons` object or ensure unique aliases when multiple variants are needed, but prefer standard imports for core UI components.

## 2026-06-18 - [Build Script Robustness]
**Learning:** Shell scripts that change directories (e.g., `cd frontend`) must explicitly return to the root or use absolute paths when subsequent steps (like Python module imports) depend on a specific working directory or `PYTHONPATH`.
**Action:** Use a `ROOT_DIR` variable derived from the script's location and explicitly `cd` back to it after sub-directory operations.
