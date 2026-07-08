# VIT Technical Debt Inventory

**Date**: 2026-07-08
**Type**: Structural Risk Assessment

## 1. Categorized Debt

| Debt Category | Description | Severity | Effort |
| :--- | :--- | :---: | :---: |
| **Architectural** | Missing `get_subsystem` in Kernel preventing cross-domain calls. | **Critical** | Small |
| **Architectural** | ~80% of API routers unmounted/unreachable in `main.py`. | **High** | Medium |
| **Legacy Code** | `app/modules/wallet/` legacy models/routes coexist with core. | **High** | Medium |
| **Infrastructure** | Regional fragmentation between Render (Ohio) and GCP (Europe). | **Medium** | Medium |
| **Security** | Missing unified security policy and rate limiting on some modules. | **Medium** | Small |
| **Testing** | Fails to collect due to boot regression; high dependency on mocking. | **High** | Medium |
| **Documentation** | Drift between Constitution API standards and actual implementation. | **Low** | Small |
| **Performance** | Potential N+1 queries in un-audited unmounted routers. | **Medium** | Medium |

## 2. Debt Deep-Dive

### A. The "Shadow" API (Unmounted Routers)
A significant amount of logic (~50+ files) is residing in the repository but is effectively "dark code". This creates a maintenance burden where code is updated but never executed or tested in production, leading to bit-rot.

### B. Dual Wallet Implementation
The ecosystem is in the middle of a migration. `app/modules/wallet` represents the legacy path, while `app/core/wallet` is the authoritative TRACK-013A implementation. The presence of both creates confusion for developers and potential data consistency risks if not strictly isolated.

### C. Kernel Fragility
The Kernel acts as the central registry but lacks comprehensive internal state validation. The recent regression where a primary method (`get_subsystem`) was removed shows a lack of "protection of the core" during merges.

## 3. Prioritized Remediation Plan

1. **Urgent (1-2 days)**: Restore `get_subsystem` method to the Kernel.
2. **Short Term (1 week)**: Consolidate `admin_*` routers and mount them under a unified admin gateway.
3. **Short Term (1 week)**: Deprecate and remove the `app/modules/wallet` legacy files in favor of `app/core/wallet`.
4. **Medium Term (2 weeks)**: Align all mounted routes with the `/v1` naming standard.

---
**Confidence Level**: High (Verified via structural analysis and regression tracking).
