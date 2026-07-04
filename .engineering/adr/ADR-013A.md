# ADR-013A: VIT Wallet & Account Platform Architecture

- **Date**: 2026-07-04
- **Status**: Proposed
- **Context**:
  The VIT ecosystem requires an authoritative, high-performance, and secure Wallet & Account Platform. Currently, wallet logic is scattered across modules. This ADR defines the centralized infrastructure to manage digital wallets, blockchain addresses, multi-asset balances, and account ownership.

- **Decision**:
  1. **Core Subsystem**: Implement `WalletSubsystem` as a core kernel component in `app/core/wallet/`.
  2. **Normalized Data Model**: Move away from flat balance columns to a normalized `CoreBalance` table supporting arbitrary assets defined in an `AssetRegistry`.
  3. **Multi-layer Identity**: Support `CoreAccount` as the owner of multiple `CoreWallet` instances, linking to `SystemID` from the Identity Platform.
  4. **Blockchain Integration**: `AddressManager` will delegate address generation to `BlockchainSubsystem` while maintaining a local index for fast lookup.
  5. **Hybrid Storage**: Use PostgreSQL for the authoritative ledger and Redis for high-performance balance/wallet caching (<5ms target).
  6. **Event-Driven**: Emit granular events for all state changes (BalanceChanged, WalletCreated, etc.) via the internal `event_bus`.
  7. **Atomic Operations**: All balance changes must be executed through the `BalanceEngine` using atomic DB transactions and Redis synchronization.

- **Consequences**:
  - Existing modules (like `app.modules.wallet`) will need to be refactored to use this new platform as their base.
  - Increased complexity in balance reconciliation but significantly better scalability and asset flexibility.
  - Mandatory dependency on Redis for performance targets.
