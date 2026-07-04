# ADR-012: Blockchain Platform Service Layer

## Status
Proposed

## Context
The VIT ecosystem requires a stable, high-performance interface to interact with the underlying VIT Chain. Previously, interactions were direct and fragmented, leading to code duplication and performance bottlenecks in querying the ledger.

## Decision
We implement a centralized "Blockchain Platform Service Layer" consisting of:
1. **BlockchainManager**: Central coordinator in `vit_chain/core` managing mempool, chain state, and block processing.
2. **BlockchainQueryEngine**: Optimized for rich queries (search, history, metrics) using the indexer and Redis caching.
3. **BlockchainSDK**: A stable, simplified Python interface for other subsystems to interact with the blockchain.
4. **Refined API/RPC**: Standardized FastAPI routes and JSON-RPC handlers delegating logic to the SDK and Query Engine.

## Consequences
- **Pros**: Improved performance via caching, better code modularity, simplified integration for future subsystems (e.g., Prophecy Chain).
- **Cons**: Increased complexity in the blockchain module due to the additional abstraction layers.
