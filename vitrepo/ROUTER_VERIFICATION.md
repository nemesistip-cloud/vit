# ROUTER_VERIFICATION.md

## 1. Authoritative Router Inventory

| File | Prefix | Mounted | Owner Subsystem | Reachable | Duplicate | Deprecated | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| app/api/routes/blockchain.py | /api/chain | True | core_api | Yes | No | No | High |
| app/api/routes/blockchain_analytics.py | /api/blockchain | True | core_api | Yes | No | No | High |
| app/api/routes/observability.py | / | True | core_api | Yes | No | No | High |
| app/api/routes/blockchain_ws.py | /api/chain/ws | True | core_api | Yes | No | No | High |
| app/api/routes/analytics.py | /api/analytics | True | core_api | Yes | No | No | High |
| app/auth/routes.py | /auth | True | core_api | Yes | No | No | High |
| app/plugins/identity/routes.py | /api/identity | True | plugins | Yes | No | No | High |
| app/api/routes/matches.py | /matches | False | core_api | No | No | No | High |
| app/api/routes/predict.py | /predict | False | core_api | No | No | No | High |
| app/api/routes/dashboard.py | /api/dashboard | False | core_api | No | No | No | High |
| app/api/routes/sports.py | /sports | False | core_api | No | No | No | High |
| app/api/routes/admin.py | /admin | False | core_api | No | Yes (Namespace) | No | High |
| app/modules/wallet/routes.py | /api/wallet | False | wallet | No | No | Yes (Legacy) | High |
| app/modules/identity/routes.py | /api/identity | False | identity | No | Yes (Plugin) | Yes (Legacy) | High |
| app/api/routes/explorer/*.py | /api/explorer | False | explorer | No | No | No | High |

## 2. Findings
- **Unmounted Critical Paths**: 80% of business-critical routers (Matches, Predictions, Admin, Explorer) are developed but not registered in `main.py`.
- **Namespace Duplication**: The `/admin` prefix is used by three different files: `admin.py`, `admin_audit_predictions.py`, and `admin_fix.py`.
- **Legacy Carryover**: Modules for Wallet and Identity still contain route files that overlap with the new core/plugin infrastructure.
