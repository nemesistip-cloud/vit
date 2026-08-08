---
name: Frontend build reproducibility
description: Keep frontend dependency manifests, lockfiles, and generated asset checks aligned for production builds.
---

Frontend dependency upgrades must update the lockfile used by the deployment build, and the production build should verify that every HTML and dynamic-import asset exists in the same dist artifact.

**Why:** A dependency bump left the deployment lockfile stale, causing the current main build to fail while an older deployment continued serving a consistent but outdated hashed asset set.

**How to apply:** Before publishing frontend changes, run the deployment package manager with its frozen-lockfile mode, typecheck, build, and validate the generated index and lazy chunks.