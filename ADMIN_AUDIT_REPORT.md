# Admin Panel — Production Readiness Gap Analysis

## 1. Existing Backend Endpoints

| Route | Method | Auth Guard | Purpose | Production Ready? | Gap |
|---|---|---|---|---|---|
| /admin/api-keys | GET | get_current_admin | Lists configured/missing API keys | ❌ | No audit log, no super_admin guard |
| /admin/config-status | GET | get_current_admin | Health check for external services | ✅ | - |
| /admin/health | GET | get_current_admin | Basic status check | ✅ | - |
| /admin/system/health | GET | get_current_admin | Full system diagnostic | ✅ | No metrics endpoint |
| /admin/fixture-health | GET | get_current_admin | Upcoming vs settled match counts | ✅ | - |
| /admin/models/status | GET | get_current_admin | ML model orchestrator status | ✅ | No per-model CRUD |
| /admin/models/reload | POST | get_current_admin | Reload ML models | ❌ | No audit log, no job tracking |
| /admin/models/train | POST | get_current_admin | Bootstrap training | ❌ | No audit log, no retrain per model |
| /admin/stats | GET | get_current_admin | Dashboard overview stats | ❌ | Missing user/wallet/prediction data |
| /admin/fixtures/sync-fd12 | POST | get_current_admin | Sync Football-Data fixtures | ❌ | No audit log |
| /admin/sync-fixtures | POST | get_current_admin | Sync TheSportsDB fixtures | ❌ | No audit log |
| /admin/matches/backfill-ft-results | POST | get_current_admin | Backfill match results | ❌ | No audit log |
| /admin/leagues | GET | get_current_admin | List supported leagues | ✅ | - |
| /admin/markets | GET | get_current_admin | List betting markets | ✅ | - |
| /admin/marketplace/pending | GET | get_current_admin | Pending marketplace listings | ❌ | No approve/reject endpoints |
| /admin/integrations/settings | GET | get_current_admin | Integration settings (masked) | ✅ | - |
| /admin/integrations/settings | PUT | get_current_admin | Store/update integration key | ❌ | No audit log |
| /admin/integrations/settings/{key} | DELETE | get_current_admin | Remove integration key | ❌ | No super_admin guard, no audit log |
| /admin/rewards/ | GET | get_current_admin | List offer completions | ✅ | - |
| /admin/rewards/{id} | GET | get_current_admin | Reward detail | ✅ | - |
| /admin/rewards/{id}/review | PATCH | get_current_admin | Approve/reject reward | ❌ | No audit log |
| /admin/rewards/{id} | DELETE | get_current_admin | Remove reward | ❌ | No audit log, no super_admin guard |
| /admin/clv/backfill | POST | get_current_admin | CLV backfill | ❌ | No audit log |
| /admin/audit-predictions | GET | get_current_admin | Audit prediction coverage | ✅ | - |
| /api/admin/wallet/withdrawals | GET | inline _require_admin | List withdrawals | ❌ | Uses inline check, no Depends() |
| /api/admin/wallet/withdrawals/{id}/approve | POST | inline _require_admin | Approve withdrawal | ❌ | No audit log, no AppError |
| /api/admin/wallet/withdrawals/{id}/reject | POST | inline _require_admin | Reject withdrawal | ❌ | No audit log |
| /api/admin/wallet/config | GET/PATCH | inline _require_admin | Platform financial config | ❌ | No audit log |
| /api/admin/wallet/plans | GET/POST/PATCH | inline _require_admin | Subscription plans | ❌ | No audit log |
| /api/admin/wallet/overview | GET | inline _require_admin | Financial overview | ✅ | - |
| /api/blockchain/admin/validators | GET | get_current_admin | List validators | ✅ | - |
| /api/blockchain/admin/validators/{id}/approve | POST | get_current_admin | Approve validator | ❌ | No audit log |
| /api/blockchain/admin/validators/{id}/reject | POST | get_current_admin | Reject validator | ❌ | No audit log |
| /api/blockchain/admin/validators/{id}/suspend | POST | get_current_admin | Suspend validator | ❌ | No audit log |
| /api/blockchain/admin/validators/{id}/slash | POST | get_current_admin | Slash validator stake | ❌ | No audit log |

## 2. Missing Backend Endpoints

- `GET /api/admin/users` — paginated user list with wallet balance + prediction count
- `GET /api/admin/users/{user_id}` — full user detail (wallet, CLV, validator, referral, predictions)
- `PATCH /api/admin/users/{user_id}` — update role, tier, active status, freeze/flag
- `POST /api/admin/users/{user_id}/reset-password` — send reset email
- `DELETE /api/admin/users/{user_id}` — soft delete (super_admin)
- `GET /api/admin/users/export` — CSV export
- `GET /api/admin/matches` — paginated match list with filters
- `PATCH /api/admin/matches/{match_id}/result` — set match result, trigger settlement
- `DELETE /api/admin/matches/{match_id}` — soft delete with cascade
- `GET /api/admin/predictions` — paginated predictions with CLV
- `POST /api/admin/predictions/recalculate-clv` — queue CLV recalculation
- `GET /api/admin/config` — all PlatformConfig rows
- `PUT /api/admin/config/{key}` — update config value
- `POST /api/admin/config` — create config key (super_admin)
- `DELETE /api/admin/config/{key}` — delete config key (super_admin)
- `GET /api/admin/models` — all ModelMetadata with accuracy/weight/status
- `POST /api/admin/models/{model_key}/retrain` — single model retrain
- `POST /api/admin/models/retrain-all` — full ensemble retrain
- `GET /api/admin/training-jobs` — paginated training job list
- `GET /api/admin/training-jobs/{job_id}` — job detail with progress
- `GET /api/admin/audit-log` — paginated admin audit log
- `GET /api/admin/system/metrics` — 24h request count, error rate, avg response time
- `POST /api/admin/system/cache/flush` — flush admin/predictions cache namespaces (super_admin)
- `GET /api/admin/wallet/transactions` — paginated wallet transactions
- `POST /api/admin/wallet/manual-credit` — manual credit to user wallet
- `POST /api/admin/wallet/manual-debit` — manual debit from user wallet
- `GET /api/admin/wallet/vitcoin-price` — price + 30d OHLCV + supply
- `POST /api/admin/wallet/vitcoin-price/override` — override VITCoin price (super_admin)
- `GET /api/admin/wallet/platform-revenue` — revenue totals by currency
- `GET /api/admin/wallet/withdrawal-queue` — pending withdrawals with KYC status
- `POST /api/admin/wallet/withdrawal/{tx_id}/approve` — approve withdrawal
- `POST /api/admin/wallet/withdrawal/{tx_id}/reject` — reject with reason
- `POST /api/admin/validators/{id}/slash` — slash with ValidatorSlashEvent
- `POST /api/admin/validators/{id}/reinstate` — reinstate (super_admin)
- `GET /api/admin/validators/appeals` — pending appeals
- `PATCH /api/admin/validators/appeals/{appeal_id}` — approve/reject appeal
- `GET /api/admin/marketplace/listings` — all listings including pending
- `POST /api/admin/marketplace/listings/{id}/approve` — approve listing
- `POST /api/admin/marketplace/listings/{id}/reject` — reject with note
- `DELETE /api/admin/marketplace/listings/{id}` — hard delete

## 3. Existing Frontend Pages & Components

| File | Status | Missing Features |
|---|---|---|
| frontend/src/pages/admin.tsx | ❌ Monolithic 5000+ line file | No component separation, no typed API client, no pagination, no audit trail display, no JSON diff, no CSV export, missing wallet/validator/model management |

## 4. Missing Frontend Pages

- `frontend/src/pages/admin/AdminLayout.tsx` — persistent sidebar + topbar
- `frontend/src/pages/admin/AdminDashboard.tsx` — KPI cards + sparklines + quick actions
- `frontend/src/pages/admin/AdminUsers.tsx` — paginated user table + slide-over
- `frontend/src/pages/admin/AdminWallet.tsx` — transactions + withdrawals + VITCoin
- `frontend/src/pages/admin/AdminMatches.tsx` — matches + predictions
- `frontend/src/pages/admin/AdminValidators.tsx` — validators + appeals
- `frontend/src/pages/admin/AdminModels.tsx` — model metadata + training jobs
- `frontend/src/pages/admin/AdminMarketplace.tsx` — listings approval
- `frontend/src/pages/admin/AdminConfig.tsx` — PlatformConfig CRUD
- `frontend/src/pages/admin/AdminAuditLog.tsx` — paginated audit log with JSON diff
- `frontend/src/pages/admin/AdminSystemHealth.tsx` — live system health + cache flush
- `frontend/src/components/admin/AdminTable.tsx` — generic sortable paginated table
- `frontend/src/components/admin/AdminModal.tsx` — generic modal
- `frontend/src/components/admin/AdminKPICard.tsx` — stat card
- `frontend/src/components/admin/AdminStatusPill.tsx` — colored badge
- `frontend/src/components/admin/AdminConfirmDialog.tsx` — destructive action modal
- `frontend/src/components/admin/AdminJsonDiff.tsx` — before/after diff viewer
- `frontend/src/hooks/useAdminData.ts` — typed data-fetch hook
- `frontend/src/api/admin.ts` — typed API client

## 5. Security Gaps

- `app/modules/wallet/admin_routes.py`: Uses inline `_require_admin(user)` instead of `Depends(get_current_admin)` — easily bypassed if dependency injection chain fails
- `app/api/routes/admin.py`: Dual import of `get_current_admin` (from `app.auth.dependencies` then overwritten by `app.api.deps`) — second import silently shadows the first
- No `require_super_admin` dependency for destructive operations (delete user, delete config, price override)
- No rate limiting on any admin endpoint
- No IP-based audit logging on mutations
- No write_audit() calls on any existing mutating route
- Security routes (`/api/security/*`) have no auth guard at all

## 6. Data Integrity Gaps

- Withdrawal approve/reject has no audit trail
- Integration key updates have no audit trail
- Reward approve/reject has no audit trail
- Model reload/train triggers have no audit trail
- Fixture sync actions have no audit trail
- Validator approve/reject/suspend have no audit trail
- No before_state/after_state capture on any mutation

## 7. Priority Matrix

| Item | Priority | Effort | Blocks Production? |
|---|---|---|---|
| require_admin dependency (proper Depends()) | Critical | Low | Yes |
| write_audit() service | Critical | Low | Yes |
| User CRUD endpoints | Critical | Medium | Yes |
| Wallet transaction + withdrawal queue | Critical | Medium | Yes |
| Fix inline auth in wallet admin_routes | Critical | Low | Yes |
| Audit log endpoint | High | Low | Yes |
| Match result management | High | Medium | Yes |
| Platform config CRUD | High | Medium | Yes |
| Model management endpoints | High | Medium | No |
| Frontend split into components | High | High | Yes |
| Validator slash/reinstate/appeals | Medium | Medium | No |
| Marketplace approval | Medium | Low | No |
| System metrics endpoint | Medium | Low | No |
| CSV export | Low | Low | No |
| Security routes auth guards | Low | Low | No |
