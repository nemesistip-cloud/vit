# AUDIT - vit_chain (Session 1.3)

## Status
Audit for Chain Storage and EVM-Compatible RPC implementation. Session 1.2 core logic is complete.

## What Exists
- `vit_chain/crypto/`: Hashing, Merkle, ECDSA, Address.
- `vit_chain/core/`: Transaction, Block, State, Chain.
- `vit_chain/genesis.py`: Genesis logic.

## What's Missing
- `vit_chain/storage/db.py`: Dedicated SQLAlchemy models for the chain.
- `vit_chain/storage/indexer.py`: Logic to sync core blocks to storage models.
- `vit_chain/rpc/`: EVM-compatible JSON-RPC server and handlers.
- `vit_chain/tests/test_rpc.py`: Tests for RPC and Indexing.

## Implementation Details
- Dedicated tables with `chain_` prefix to avoid conflict with main app tables.
- `ChainIndexer` will provide high-level chain stats.
- RPC will mimic Ethereum's JSON-RPC 2.0 to allow MetaMask connectivity.
- `eth_getBalance` will report in "wei" (1e18) for compatibility.

## Hard Constraints Check
- No modifications to `main.py` or existing webhooks.
- Using `Base` from `app.db.database`.
- Async SQLAlchemy throughout.
