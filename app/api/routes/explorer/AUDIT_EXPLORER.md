# Block Explorer API Audit (v5.5.0)

## Data Correlation Strategy

To satisfy the requirements of Session 8.2, we must link data across the chain persistence layer and the application layer:

1.  **Accounts**:
    *   `ChainAccount` (from `vit_chain/storage/db.py`) provides the core on-chain balance and nonce.
    *   Linking to `User` (via `wallet_address`) allows identifying if an account belongs to a registered `validator` or `storage` node.

2.  **Nodes**:
    *   `PeerNode` (from `vit_chain/p2p/models.py`) is the primary registry for active nodes, providing `score`, `region`, and `country_code`.
    *   `UserStorageNode` (from `app/modules/storage_verification/models.py`) provides `gb_used` (shards held proxy) and `tsc_earned` (earnings).
    *   Join Path: `PeerNode.node_id` (VIT address) -> `User.wallet_address` -> `User.id` -> `UserStorageNode.user_id`.

3.  **Blocks & Transactions**:
    *   Stored in `chain_blocks` and `chain_transactions`.
    *   Requires 10s caching for the blocks list to handle high-frequency explorer polling without overloading the database.

## Privacy Guard
- Geographic map uses a static lookup from `country_code` to prevent precise IP triangulation.

## Endpoints to Implement
- `/api/explorer/blocks`
- `/api/explorer/blocks/{id}`
- `/api/explorer/transactions`
- `/api/explorer/tx/{hash}`
- `/api/explorer/accounts/{address}`
- `/api/explorer/accounts/{address}/transactions`
- `/api/explorer/nodes`
- `/api/explorer/nodes/map`
