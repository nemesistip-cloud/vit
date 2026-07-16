# Router Inventory Report

## 1. Summary
A total of **105** files contain `APIRouter` definitions. However, only a small fraction are explicitly mounted in `main.py`. Most routers reside in `app/modules/` and are intended to be registered dynamically via the Plugin Framework or a future integration step.

## 2. Mounted Routers (main.py)
| Router | File Path | Prefix | Endpoint Count | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| Auth | `app/auth/routes.py` | `/api/auth` | 8 | KEEP |
| Observability | `app/api/routes/observability.py` | `/api/obs` | 8 | KEEP |
| Identity | `app/plugins/identity/routes.py` | `/api/identity` | 3 | KEEP |
| Blockchain | `app/api/routes/blockchain.py` | `/` | 8 | KEEP |
| Explorer | `app/api/routes/explorer/__init__.py` | `/api/explorer` | 9 | KEEP |
| Blockchain WS | `app/api/routes/blockchain_ws.py` | `/` | 1 | KEEP |
| Blockchain Analytics | `app/api/routes/blockchain_analytics.py` | `/` | 9 | KEEP |

## 3. Key Unmounted/Orphaned Routers
| Router | File Path | Status | Recommendation |
| :--- | :--- | :--- | :--- |
| Wallet Legacy | `app/modules/wallet/routes.py` | UNMOUNTED | DEPRECATE (Use Wallet Platform) |
| Matches | `app/api/routes/matches.py` | UNMOUNTED | REGISTER |
| Sports | `app/api/routes/sports.py` | UNMOUNTED | REGISTER |
| AI | `app/api/routes/ai.py` | UNMOUNTED | REGISTER |
| Admin | `app/api/routes/admin.py` | UNMOUNTED | REGISTER |
| Paystack Webhooks | `app/api/routes/paystack_webhooks.py` | UNMOUNTED | REGISTER |
| Predict | `app/api/routes/predict.py` | UNMOUNTED | REGISTER |
| Dashboard | `app/api/routes/dashboard.py` | UNMOUNTED | REGISTER |

## 4. Duplicate/Redundant Routers
- **Identity**: `app/modules/identity/routes.py` and `app/plugins/identity/routes.py`. (The plugin version is currently mounted). Recommendation: ARCHIVE `app/modules/identity/routes.py`.
- **Wallet**: Multiple routes in `app/modules/wallet/` (p2p, direct_sale, etc.). Recommendation: ARCHIVE once migrated to `app/core/wallet/`.

## 5. Recommendations
- **Consolidation**: Move towards a pattern where core subsystems register their own routers during `_on_initialize`.
- **Immediate Action**: Register critical business routers (`matches`, `predict`, `dashboard`) to restore user-facing functionality.
