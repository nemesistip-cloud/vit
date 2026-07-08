# VIT API Audit

**Date**: 2026-07-08
**Type**: Router Registry Verification

## 1. Quantitative Summary

- **Total Router Files Found**: 93 (`app/api/routes/` and `app/modules/`).
- **Mounted Routers (main.py)**: 37 unique router objects.
- **Dark Routers (Unmounted)**: ~56 (Significant "shadow" API surface).

## 2. API Mounting Inventory

| Router Object | Path Prefix | Domain | Status |
| :--- | :--- | :--- | :--- |
| `auth_router` | `/api/auth` | Identity | Mounted |
| `blockchain_router` | N/A | Blockchain | Mounted |
| `matches_router` | `/api` | Sports | Mounted |
| `predict_router` | `/api` | AI | Mounted |
| `admin_router` | `/api` | Admin | Mounted |
| `governance_router`| `/api` | Governance | Mounted |
| `wallet_router` | N/A | Finance | Mounted |
| `did_router` | `/api/did` | Identity | Mounted |
| `academy_router` | `/api/academy` | Intelligence| Mounted |
| `marketplace_router`| `/api/marketplace`| Intelligence| Mounted |

## 3. Dark Code Audit (Unmounted Examples)

The following routers exist in the filesystem but are **NOT** mounted in the gateway (`main.py`):

1. **admin_clv.py**: Performance tracking for sports models.
2. **admin_finance.py**: Specialized blockchain treasury management.
3. **admin_rewards.py**: Reward distribution auditing.
4. **ai_support.py**: Customer support AI agents.
5. **odds_compare.py**: Multi-bookmaker odds comparison.
6. **similarity.py**: Match similarity analysis.
7. **wrapped.py**: "Year in review" style user statistics.

## 4. Architectural Drift

- **Versioned Routes**: The Engineering Constitution (`05_ENGINEERING_STANDARDS.md`) mandates a `/v1/` prefix for all APIs. However, most mounted routes use the flat `/api/` prefix.
- **Naming Conventions**: Inconsistencies exist between singular and plural resource naming (e.g., `/api/match` vs `/api/matches` in some modules).
- **Shadowing**: Multiple routers are mounted with the same `/api` prefix without sub-segmentation, leading to potential route shadowing and collision risks.

## 5. Recommendations

1. **Consolidation**: Consolidate unmounted routers into logical domain gateways (e.g., `admin_router` should import and mount sub-routers).
2. **Standardization**: Implement a global `/v1` prefix as mandated by the constitution.
3. **Registry Audit**: Remove orphaned router files that are no longer part of the product roadmap.

---
**Confidence Level**: High (Verified via `main.py` inspection and `ls` cross-referencing).
