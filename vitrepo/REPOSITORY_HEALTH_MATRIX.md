# Repository Health Matrix

## 1. Health Overview
The ecosystem exhibits strong architectural maturity but is currently experiencing a critical runtime failure.

| Component | Build Status | Test Status | Deployment Status | Open Issues/PRs | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend (Core)** | ❌ Failing | ❌ Failing | ❌ Failing | 322 PRs (Total) | High |
| **Frontend** | ✅ Passing | ⚠️ Unknown | ⚠️ Pending | N/A | High |
| **Explorer** | ✅ Passing | ⚠️ Unknown | ⚠️ Pending | N/A | Medium |
| **VIT Node** | ✅ Passing | ⚠️ Unknown | ⚠️ Pending | N/A | Medium |
| **Tachyon** | ✅ Passing | ⚠️ Unknown | ⚠️ Pending | N/A | Medium |

## 2. Critical Health Issues (Verified @ 925ca8c)
- **Kernel Regression (STILL VALID)**: `main.py` fails with `AttributeError: 'VITRuntimeKernel' object has no attribute 'get_subsystem'`. This prevents any backend-integrated tests or deployments from succeeding.
- **Render Deployment (STILL VALID)**: All recent deploys (`dep-d94inu3tqb8s73c4o9b0` and earlier) are failing. The 404 fix in #322 was necessary but insufficient as the kernel crash occurs earlier in the boot sequence.
- **Router Debt (STILL VALID)**: ~80+ unmounted routers (`app/api/routes/`) represent significant "dark code" that is untested and inaccessible.

## 3. Test Coverage
- **Status**: ❌ Test collection fails due to kernel imports in `conftest.py`.
- **Remediation**: Kernel must be stabilized before coverage can be re-assessed.

**Overall Health Score: 58/100** (Decreased from previous estimate due to confirmation of regression persistence after PR #322).
