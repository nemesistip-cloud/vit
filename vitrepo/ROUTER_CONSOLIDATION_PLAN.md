# ROUTER_CONSOLIDATION_PLAN.md

## 1. Active Routers (Registered in main.py)
These routers are currently mounted and functional.
- **Auth**: `app/auth/routes.py`
- **Observability**: `app/api/routes/observability.py`
- **Identity**: `app/plugins/identity/routes.py`
- **Blockchain**: `app/api/routes/blockchain.py`
- **Explorer**: `app/api/routes/explorer/__init__.py`
- **Blockchain WS**: `app/api/routes/blockchain_ws.py`
- **Blockchain Analytics**: `app/api/routes/blockchain_analytics.py`

## 2. REGISTER NOW (Critical for Production & Testing)
These routers are developed but currently unmounted. They must be registered to restore core platform functionality.
- **Matches**: `app/api/routes/matches.py` (Prefix: `/api/matches`)
- **Predict**: `app/api/routes/predict.py` (Prefix: `/api/predict`)
- **Dashboard**: `app/api/routes/dashboard.py` (Prefix: `/api/dashboard`)
- **Sports**: `app/api/routes/sports.py` (Prefix: `/api/sports`)
- **Admin**: `app/api/routes/admin.py` (Prefix: `/api/admin`)
- **Wallet (Core)**: `app/core/wallet/subsystem.py` (Registration via subsystem)
- **Paystack/Stripe Webhooks**: `app/api/routes/paystack_webhooks.py`, `app/api/routes/stripe_webhooks.py`

## 3. INCOMPLETE / LEAVE DISABLED
Routers for modules still in early development or that require further stabilization.
- **Academy/Campus**: `app/modules/academy/routes.py`
- **Community**: `app/modules/community/routes.py`
- **Elections**: `app/modules/elections/routes.py`
- **Governance**: `app/modules/governance/routes.py`
- **Prophecy Chain**: `app/modules/prophecy_chain/routes.py`

## 4. OBSOLETE / DEPRECATE
Redundant routers that have been replaced by core subsystems or newer versions.
- **Legacy Wallet**: `app/modules/wallet/routes.py` (Replaced by Core Wallet)
- **Legacy Identity**: `app/modules/identity/routes.py` (Replaced by Plugin Identity)
- **Direct Sale**: `app/modules/wallet/direct_sale.py` (To be moved to Marketplace)

## 5. EXPERIMENTAL / MOVE TO LABS
- **Similarity Engine**: `app/api/routes/similarity.py`
- **Wrapped (Year-in-review)**: `app/api/routes/wrapped.py`
- **AI Support/Assistant**: `app/api/routes/ai_support.py`, `app/api/routes/ai_assistant.py`

## Implementation Strategy
- **Phase 1**: Update `main.py` to include the "REGISTER NOW" group.
- **Phase 2**: Implement dynamic registration in `ModuleRegistry` so subsystems can mount their own routes.
- **Phase 3**: Clean up obsolete routes from the file system to reduce confusion.
