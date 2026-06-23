## 2024-05-18 - Restoring Design Tokens and Enabling Multi-Leg Accumulators

**Learning:** Corrupted CSS selectors (like `., ., .`) in global design tokens can silently break the entire application's visual polish and accessibility features (shadows, animations, focus rings). Automation scripts should be carefully audited when performing bulk replacements. Additionally, "Coming Soon" placeholders in the UI often persist long after the underlying backend infrastructure (like affiliate deep-linking) is ready for integration.

**Action:** Always verify the integrity of `tokens.css` after any environment-wide refactoring. Prioritize the replacement of static "Coming Soon" blocks with functional prototypes that leverage existing API endpoints, such as the `generate-slip` multi-leg support.

## 2026-05-20 - Dashboard Stability & Route Alignment
**Learning:** React components using platform configuration data must ensure hooks like `usePublicConfig` are invoked within the specific component scope or passed as props, rather than assuming global availability if they are part of a shared layout but not a shared context provider. Additionally, frontend-driven dashboard summaries often expect specific scoped endpoints (e.g., `/api/analytics/user-stats`) that must be explicitly mapped in the backend to avoid 404 "Operation failed" states.

**Action:** Always verify that every `config?.platform` access is backed by a local hook call or verified prop. Maintain a mapping of frontend query keys to backend router paths to catch missing endpoints early in the development cycle.
## 2026-06-23 - Fix scope error in DashboardPage

**Learning:** Components that rely on global configuration hooks like `usePublicConfig` must explicitly call the hook within their own scope if they are not receiving the data via props. Relying on outer scope variables can lead to "not defined" errors if the component is moved or if the outer scope is not what was expected.

**Action:** Always ensure that child components in `frontend/src/pages` that use `config` either receive it as a prop or call `usePublicConfig()` themselves. Double-check for literal text placeholders like `{config?.platform?.model_count || 13}` in strings and replace them with template literals or `.replace()` calls.
