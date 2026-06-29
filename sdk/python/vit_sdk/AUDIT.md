# Audit - Developer Platform (Python SDK)

## Current State
- `sdk/python/vit_sdk/` directory created.
- All required files are missing:
    - `sdk/python/vit_sdk/__init__.py`
    - `sdk/python/vit_sdk/client.py`
    - `sdk/python/vit_sdk/wallet.py`
    - `sdk/python/vit_sdk/storage.py`
    - `sdk/python/vit_sdk/chain.py`
    - `sdk/python/setup.py`
    - `sdk/README.md`

## Planned Implementation

### `vit_sdk/client.py`
- Base `VITClient` using `httpx.AsyncClient`.
- Handles authentication (API Key, Private Key).
- Provides a common `request` method for other API classes.

### `vit_sdk/wallet.py`
- `WalletAPI` class.
- `get_balance(address)`: Calls `/api/chain/rpc` (eth_getBalance).
- `transfer(to_address, amount, private_key)`: Constructs, signs, and sends a VIT Chain transaction via `/api/chain/rpc` (eth_sendRawTransaction).
- `get_transactions(address, limit)`: Calls `/api/wallet/transactions` (Wait, this is custodial. I should check if there is a chain equivalent).

### `vit_sdk/storage.py`
- `StorageAPI` class.
- `upload(data, filename)`: `POST /api/tachyon/upload`.
- `download(file_id)`: `GET /api/tachyon/download/{file_id}`.
- `delete(file_id)`: `DELETE /api/tachyon/manifests/{file_id}`.
- `verify(file_id)`: `POST /api/tachyon/admin/verify/{file_id}` (or public equivalent if it exists).

### `vit_sdk/chain.py`
- `ChainAPI` class.
- `get_block(height_or_hash)`: `eth_getBlockByNumber` via RPC.
- `get_transaction(tx_hash)`: `eth_getTransactionByHash` via RPC.
- `get_balance(address)`: `eth_getBalance` via RPC.
- `send_transaction(from_key, to_address, amount)`: Similar to `WalletAPI.transfer`.
- `get_chain_stats()`: `/api/blockchain/economy`.

### `setup.py`
- Standard `setuptools` configuration for `vit-sdk`.
- Dependencies: `httpx`, `coincurve`, `pydantic`.

### `README.md`
- Installation instructions.
- Quick start examples for Transfer, Upload, and Chain Query.

## Missing/Broken
- No public `/api/wallet/transfer` endpoint exists for custodial transfers in the current API.
- `WalletAPI.transfer` in the build spec takes a `private_key`, strongly suggesting it's for the non-custodial VIT Chain.
- `WalletAPI.get_transactions` in the build spec takes an `address`, while the custodial `/api/wallet/transactions` is for the logged-in user. I will aim for chain-based transaction fetching if possible, or use the custodial API if that's the intent.
- No public `verify` endpoint for storage except the admin one. I'll use the admin one or a placeholder if a public one is preferred.

## Integration Notes
- SDK must handle both custodial API (via API Key) and VIT Chain (via Private Key/RPC).
- `coincurve` will be used for signing VIT Chain transactions locally in the SDK.
