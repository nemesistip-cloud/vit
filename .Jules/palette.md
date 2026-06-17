## 2026-06-16 - [Notification Accessibility & Empty State]
**Learning:** Icon-only buttons in notification headers (Mark Read, Settings) were missing descriptive ARIA labels, making them invisible to screen readers. Additionally, a simple text "No notifications" didn't provide enough guidance for a good user experience.
**Action:** Always add `aria-label` to header action buttons and use a visual `EmptyState` component with an icon and helpful description to guide the user when no data is present.

## 2026-06-17 - [Icon-Only Button Accessibility Pattern]
**Learning:** Found a recurring pattern of icon-only buttons (Logout, Close, Copy, Share) lacking `aria-label` attributes across several core pages (Layout, Referral, Watchlist). These buttons are functional but silent for screen reader users.
**Action:** Consistently audit interactive `Button` components with `size="icon"` and ensure they have descriptive `aria-label` or `title` props.

## 2026-06-18 - [Match Detail Analytics Polish]
**Learning:** Enrichment of the Match Detail page with deterministic AI insights and child model breakdowns requires robust fallback mechanisms. When external AI providers are offline or a specific match hasn't been predicted yet, the UI must gracefully guide the user to trigger the ensemble rather than showing empty states or NaN values.
**Action:** Implemented 'Run ML Ensemble' triggers directly in the 'Child Model Analytics' section to ensure a continuous UX flow when background processing hasn't completed. Fixed NaN% bug in confidence meters by ensuring the backend always returns a numerical 'confidence' field in the insights payload.
