# VITCoin Pricing Engine Audit (v5.5.0)

## Overview
The existing pricing infrastructure in `app/modules/wallet/` provides a foundation for price persistence and historical tracking, but the current valuation logic deviates from the "3-Governor Pricing Engine" requirement.

## Existing Components
- **`app/modules/wallet/models.py`**:
    - `VITCoinPriceHistory`: Successfully tracks historical prices.
    - `PlatformConfig`: Correctly stores floor prices and configuration.
    - `Wallet` & `SavingsVault`: Provides data for locked/staked supply.
    - `WalletTransaction`: Tracks buy/sell signals.
- **`app/modules/wallet/pricing.py`**:
    - `VITCoinPricingEngine`: Currently acts as a getter for historical prices and an exchange rate utility. It does not contain the core valuation logic.
- **`app/modules/wallet/scheduler.py`**:
    - `WalletScheduler.update_vitcoin_price`: Implements an interim v5.5.0 formula based on Revenue + Collateral. This is slated for replacement by the 3-Governor model.

## Gaps & Requirements
1. **3-Governor Hybrid Logic**:
    - **Governor 1 (Demand Signal)**: Missing. Needs to compute 24h buy/sell volume ratio.
    - **Governor 2 (Supply Compression)**: Missing. Needs to compute (Staked + Vaulted) / Circulating supply ratio.
    - **Governor 3 (Momentum Carry)**: Missing. Needs to compute price velocity from `VITCoinPriceHistory`.
2. **Phase Detection**:
    - Logic to switch weights between 'launch', 'growth', and 'mature' based on circulating supply is missing.
3. **Core API**:
    - `get_current_price` needs to be implemented/overridden to return the full state (price, phase, floor, governors) and use Redis caching (`vit:vitcoin:price_cache`).

## Identified Issues
- The current formula in `scheduler.py` is disconnected from the requirement's "3-Governor" specification.
- Redis caching is not yet implemented for the price calculation endpoint.
- No unified `PHASE_WEIGHTS` constant exists in the codebase.

## Plan for Implementation
- Implement the 3-Governor logic in `app/modules/wallet/pricing_engine.py`.
- Integrate phase detection based on supply thresholds.
- Implement Redis-backed caching for the price engine.
- Ensure the floor price is strictly enforced.
