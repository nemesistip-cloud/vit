from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ..storage.db import ChainBlock, ChainTransaction, ChainAccount
from ..core.transaction import VITTransaction, verify_transaction
from app.core.kernel import kernel
import json

def to_hex(n: int) -> str:
    return hex(n)

def vit_to_wei_hex(amount: Decimal) -> str:
    # 1 VIT = 1e18 units
    return hex(int(amount * Decimal("1000000000000000000")))

async def net_version() -> str:
    """Returns VIT Chain ID as string"""
    return "7764"

async def eth_chainId() -> str:
    """Returns 7764 in hex"""
    return "0x1e54"

async def eth_blockNumber(db: AsyncSession) -> str:
    """Returns latest height as hex string"""
    subsystem = kernel.get_subsystem("blockchain")
    if subsystem and subsystem.manager:
        height = await subsystem.manager.chain.chain_height(db)
        return to_hex(height) if height >= 0 else "0x0"

    result = await db.execute(select(ChainBlock.height).order_by(desc(ChainBlock.height)).limit(1))
    height = result.scalar_one_or_none()
    return to_hex(height) if height is not None else "0x0"

async def eth_getBalance(address: str, block: str, db: AsyncSession) -> str:
    """Returns balance in hex wei-equivalent"""
    subsystem = kernel.get_subsystem("blockchain")
    sdk = subsystem.get_sdk() if subsystem else None
    if sdk:
        balance = await sdk.get_balance(db, address)
        return vit_to_wei_hex(balance)

    result = await db.execute(select(ChainAccount.balance).where(ChainAccount.address == address))
    balance = result.scalar_one_or_none() or Decimal("0")
    return vit_to_wei_hex(balance)

async def eth_getTransactionCount(address: str, block: str, db: AsyncSession) -> str:
    """Returns nonce as hex (for MetaMask tx signing)"""
    result = await db.execute(select(ChainAccount.nonce).where(ChainAccount.address == address))
    nonce = result.scalar_one_or_none() or 0
    return to_hex(nonce)

async def eth_sendRawTransaction(raw_tx_hex: str, db: AsyncSession) -> str:
    """Accepts hex-encoded VIT transaction, adds to mempool"""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        raise ValueError("Blockchain subsystem unavailable")

    try:
        if raw_tx_hex.startswith("0x"):
            raw_tx_hex = raw_tx_hex[2:]

        tx_data = json.loads(bytes.fromhex(raw_tx_hex).decode("utf-8"))
        tx = VITTransaction(
            from_address=tx_data["from_address"],
            to_address=tx_data["to_address"],
            amount=Decimal(str(tx_data["amount"])),
            nonce=tx_data["nonce"],
            timestamp=tx_data["timestamp"],
            gas_fee=Decimal(str(tx_data.get("gas_fee", "0.001"))),
            data=tx_data.get("data"),
            signature=tx_data["signature"],
            tx_hash=tx_data.get("tx_hash", "")
        )

        success = await subsystem.manager.add_transaction(tx)
        if success:
            return tx.tx_hash
        else:
            raise ValueError("Invalid transaction or duplicate")

    except Exception as e:
        raise ValueError(f"Failed to process raw transaction: {str(e)}")

async def eth_getBlockByNumber(block_number: str, full_txs: bool, db: AsyncSession) -> dict:
    """Returns block in Ethereum block format (MetaMask compatible)"""
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem or not subsystem.manager:
        return None

    if block_number == "latest":
        block = await subsystem.manager.get_latest_block(db)
    else:
        try:
            height = int(block_number, 16)
            block = await subsystem.manager.get_block_by_height(db, height)
        except (ValueError, TypeError):
            return None

    if not block:
        return None

    return {
        "number": to_hex(block.height),
        "hash": block.block_hash,
        "parentHash": block.prev_hash,
        "timestamp": to_hex(block.timestamp),
        "transactions": [tx.tx_hash for tx in block.transactions] if not full_txs else [tx.to_dict() for tx in block.transactions]
    }

async def eth_getTransactionByHash(tx_hash: str, db: AsyncSession) -> dict:
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem:
        return None

    sdk = subsystem.get_sdk()
    tx = await sdk.get_transaction(db, tx_hash)
    if not tx:
        return None

    return {
        "hash": tx["tx_hash"],
        "blockNumber": to_hex(tx["block_height"]) if tx.get("block_height") else None,
        "from": tx["from_address"],
        "to": tx["to_address"],
        "value": vit_to_wei_hex(Decimal(tx["amount"])),
        "nonce": to_hex(tx["nonce"])
    }

async def eth_getTransactionReceipt(tx_hash: str, db: AsyncSession) -> dict:
    subsystem = kernel.get_subsystem("blockchain")
    if not subsystem:
        return None

    sdk = subsystem.get_sdk()
    tx = await sdk.get_transaction(db, tx_hash)
    if not tx or not tx.get("block_height"):
        return None

    return {
        "transactionHash": tx["tx_hash"],
        "blockNumber": to_hex(tx["block_height"]),
        "status": "0x1" if tx["status"] == "confirmed" else "0x0",
        "from": tx["from_address"],
        "to": tx["to_address"]
    }

async def eth_call(call_object: dict, block: str, db: AsyncSession) -> str:
    return "0x"

async def eth_gasPrice() -> str:
    return hex(1000000000) # 1 gwei

async def eth_estimateGas(call_object: dict) -> str:
    return "0x5208" # 21000
