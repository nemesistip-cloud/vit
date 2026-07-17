# Recommended Ecosystem Roadmap

## 1. Immediate Stabilization (CRITICAL)
1. **Fix Kernel Regression**: Implement `get_subsystem` in `VITRuntimeKernel` (`app/core/kernel.py`).
2. **Rehabilitate Backend Tests**: Restore test collection by fixing imports and kernel dependencies.
3. **Trigger Render Deployment**: Perform a clean deploy once the kernel is stabilized.

## 2. Governance Hardening
1. **Repository Hygiene**: Add `.github/CODEOWNERS`, `ISSUE_TEMPLATE`, and `PULL_REQUEST_TEMPLATE`.
2. **Security Disclosure**: Create `SECURITY.md`.
3. **Dependency Automation**: Enable `Dependabot`.

## 3. Architectural Evolution
1. **Router Consolidation**: Mount or archive the ~80 unmounted routers.
2. **vit-mobile Extraction**: Formalize the extraction of mobile modules into a workspace.
3. **Standard Alignment**: Synchronize the codebase with the Constitution's API standards (`/api/v1` prefix, etc.).

**Confidence Level: High**.
