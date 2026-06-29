# VIT Network Python SDK

Official Python SDK for interacting with the VIT Network (Value Analytics Trust) v5.5.0.

## Installation

```bash
pip install vit-sdk
```

## Quick Start

### Initialize Client

```python
from vit_sdk import VITClient

# For public data (no auth)
client = VITClient(api_url="https://api.vitnetwork.app")

# For private/wallet operations
client = VITClient(
    api_url="https://api.vitnetwork.app",
    api_key="your_api_key",
    private_key="your_private_key_hex"
)
```

### Wallet & Transfers

```python
from vit_sdk.wallet import WalletAPI
import asyncio

async def main():
    wallet = WalletAPI(client)

    # Get on-chain balance
    balance = await wallet.get_balance("VIT...")
    print(f"Balance: {balance} VIT")

    # Transfer VIT on-chain
    tx_hash = await wallet.transfer(
        to_address="VIT...",
        amount=10.5
    )
    print(f"Transfer Hash: {tx_hash}")

asyncio.run(main())
```

### Tachyon VESS Storage

```python
from vit_sdk.storage import StorageAPI

async def storage_demo():
    storage = StorageAPI(client)

    # Upload
    file_id = await storage.upload(b"Hello Tachyon!", "hello.txt")
    print(f"Uploaded: {file_id}")

    # Download
    content = await storage.download(file_id)
    print(f"Downloaded: {content}")

    # Verify (Audit)
    audit = await storage.verify(file_id)
    print(f"Audit Result: {audit}")

asyncio.run(storage_demo())
```

### VIT Chain Queries

```python
from vit_sdk.chain import ChainAPI

async def chain_demo():
    chain = ChainAPI(client)

    # Latest block
    block = await chain.get_block("latest")
    print(f"Latest Block: {block['number']}")

    # Chain stats
    stats = await chain.get_chain_stats()
    print(f"Network Staked: {stats['total_staked_vitcoin']} VIT")

asyncio.run(chain_demo())
```

## Features

- **VIT Chain L2 Integration**: Local transaction signing and JSON-RPC 2.0 interface.
- **Tachyon VESS**: Verifiable elastic storage swarm integration.
- **Custodial & Non-Custodial Support**: API key for platform services, private key for chain actions.
- **Async First**: Built on `httpx` for high-performance asynchronous operations.
