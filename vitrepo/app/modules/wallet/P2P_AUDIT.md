# P2P Exchange & Direct Sale Audit (v5.5.0)

## Overview
A preliminary P2P implementation exists within the primary `app/modules/wallet/routes.py` file. However, it is not currently decoupled into a dedicated module and lacks advanced activation features requested for Session 6.2.

## Existing P2P Components
- **`app/modules/wallet/models.py`**:
    - `P2POffer`: Table for buy/sell listings.
    - `P2POrder`: Table for individual trades and dispute tracking.
    - `P2POfferType`, `P2POfferStatus`, `P2POrderStatus`: Necessary enums are present.
- **`app/modules/wallet/routes.py`**:
    - Contains several P2P endpoints (GET `/p2p/offers`, POST `/p2p/offers`, DELETE `/p2p/offers/{id}`, POST `/p2p/orders`, etc.).
    - These are currently mixed with general wallet routes.

## Gaps & Missing Paths
1. **Decoupling**: P2P routes need to be moved from `routes.py` to a dedicated `p2p_routes.py` for cleaner domain management.
2. **Direct Sale Refinement**: The existing `POST /vitcoin/buy` in `routes.py` uses legacy pricing and generic idempotency. It must be replaced/extended in `direct_sale.py` with the 3-Governor pricing and the specialized time-bucketed idempotency key.
3. **Advanced P2P Activation**:
    - Enhanced validation for payment methods.
    - Explicit escrow release logic with audit trails.
    - Standardized dispute resolution hooks.

## Broken/Partial Logic
- The current P2P order creation does not strictly enforce KYC checks which are mandated by the platform's risk settings for large trades.
- Escrow logic in `routes.py` is functional but lacks transaction-level atomicity across all states.

## Implementation Plan
- Create `app/modules/wallet/p2p_routes.py` and migrate/enhance P2P logic.
- Create `app/modules/wallet/direct_sale.py` to implement the refined VITCoin purchase flow.
- Ensure the new `direct_sale.py` correctly interacts with the 3-Governor `PricingEngine`.

## Operator Instructions
The following lines must be added to `main.py` after the rollover router to activate these new routes (to be performed by the INTEGRATION ENGINE):

```python
from app.modules.wallet.p2p_routes import router as p2p_router
app.include_router(p2p_router, prefix="/api")

from app.modules.wallet.direct_sale import router as direct_sale_router
app.include_router(direct_sale_router, prefix="/api")
```

## Post-Audit Fixes & Compliance
- **Asset-Minting Bug**: Identified and fixed a critical bug where Taker-Sell (satisfying a Buy offer) was not escrowing funds from the taker, leading to VIT creation. Logic now strictly escrows VIT from the seller regardless of Maker/Taker role.
- **Type Safety**: Ensured JSON serialization compatibility in the Pricing Engine by converting Decimals to floats before Redis caching.
- **Hard Constraints**:
    - Migrated all error handling from `HTTPException` to `AppError`.
    - Implemented Idempotency Keys on all financial entry points (Offers, Orders, Direct Buy).
    - Enforced atomic mutations using `async with db.begin()`.
