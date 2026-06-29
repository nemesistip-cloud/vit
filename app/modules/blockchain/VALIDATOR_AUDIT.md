# Validator Rewards & Slashing Audit — Track 7.2

## Current State

### Files Audited:
- `app/modules/blockchain/models.py`: Defines `ValidatorProfile`, `ValidatorPrediction`, and `ValidatorSlashEvent`.
- `app/modules/blockchain/settlement.py`: Contains core settlement logic including a variable validator reward distribution based on platform fees.
- `app/services/oracle_settlement_bridge.py`: Coordinates oracle consensus and triggers settlement.

### Findings:
- **Rewards**: Current rewards in `settlement.py` are proportional to influence and platform fees. The new requirement is for a fixed reward (5 VIT) per consensus-aligned validator.
- **Slashing**: No slashing logic exists in the current settlement flow.
- **Models**: Models for profiles, predictions, and slash events are already in place and should not be redefined.
- **Integration**: The `OracleSettlementBridge` should be the point of integration for the new reward distributor and slash engine.

### Implementation Strategy:
1.  **ValidatorRewardDistributor**: Implement fixed VIT rewards per settlement.
2.  **ValidatorSlashEngine**: Implement slashing based on outcome deviation (30% threshold).
3.  **Bridge Update**: Update `OracleSettlementBridge` to invoke these new components during the settlement phase.
