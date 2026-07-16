# Oracle System Audit — Track 7.1

## Current State

### Files Audited:
- `app/modules/blockchain/oracle.py`: Handles oracle result submissions and manual dispute resolution.
- `app/modules/blockchain/models.py`: Defines `OracleResult`, `MatchSettlement`, `ConsensusPrediction`, and `ValidatorPrediction`.
- `app/modules/blockchain/settlement.py`: Core logic for match settlement, stake payout, and validator reward distribution.
- `app/services/results_settler.py`: Automated settlement polling from external APIs.

### Existing Functionality:
- Oracle providers can submit results via `POST /api/oracle/result`.
- Agreement is currently hardcoded to `_MIN_AGREEMENT = 2` (out of 3).
- Settlement is triggered directly by calling `settle_match` from the route handler.
- Admin can resolve disputes manually.

### Missing / Broken:
- **No Settlement Bridge**: The logic for checking consensus and triggering settlement is tightly coupled with the API route.
- **Agreement Threshold**: Current threshold is hardcoded to 2. The spec requires a flexible `0.67` (67%) consensus threshold.
- **Redis Events**: No events are published to Redis when an oracle triggers a settlement.
- **Consensus Calculation**: The current logic just counts votes. It should ideally be calculated as `count / total_sources >= 0.67`.

## Implementation Plan for OracleSettlementBridge

1.  Create `app/services/oracle_settlement_bridge.py`.
2.  Implement `CONSENSUS_THRESHOLD = 0.67`.
3.  Implement `check_and_settle()` to:
    - Aggregate all `OracleResult` for a given `match_id`.
    - Determine the winning outcome based on 67% threshold.
    - If met, call `settle_match()`.
4.  Implement `settle_match()` in the bridge to:
    - Invoke `app.modules.blockchain.settlement.settle_match`.
    - Publish `vit:oracle:settled` event to Redis with match details.
5.  Refactor `oracle.py` to use the bridge.
