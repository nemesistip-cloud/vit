## 2024-05-18 - Restoring Design Tokens and Enabling Multi-Leg Accumulators

**Learning:** Corrupted CSS selectors (like `., ., .`) in global design tokens can silently break the entire application's visual polish and accessibility features (shadows, animations, focus rings). Automation scripts should be carefully audited when performing bulk replacements. Additionally, "Coming Soon" placeholders in the UI often persist long after the underlying backend infrastructure (like affiliate deep-linking) is ready for integration.

**Action:** Always verify the integrity of `tokens.css` after any environment-wide refactoring. Prioritize the replacement of static "Coming Soon" blocks with functional prototypes that leverage existing API endpoints, such as the `generate-slip` multi-leg support.
