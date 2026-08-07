---
name: Branch and deployment contract
description: Production branch and frontend dependency conventions for VIT Network.
---

The Render gateway deploys `main`; isolated agent snapshots may have unrelated Git histories and should be merged with production code preserved, not force-merged as replacements.

**Why:** The agent snapshot was a separate repository history, while Render continued serving the protected production branch.

**How to apply:** Compare branch ancestry first, retain the production application as the base, and integrate only reviewed assets or fixes.

The frontend workspace is governed by the root `pnpm-lock.yaml`; startup must use pnpm when that lock exists rather than the stale root npm lock.

**Why:** The npm lock pulled a blocked Vitest artifact even though the frontend did not declare Vitest, preventing Vite from installing and starting.

**How to apply:** Use the workspace pnpm lock for local and deployment validation, and fail explicitly when Vite is unavailable.
