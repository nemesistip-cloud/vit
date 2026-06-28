from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from ..storage.db import ChainBlock, ChainTransaction, ChainAccount
from ..core.transaction import VITTransaction, verify_transaction
from ..core.chain import VITChain
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
    result = await db.execute(select(ChainBlock.height).order_by(desc(ChainBlock.height)).limit(1))
    height = result.scalar_one_or_none()
    return to_hex(height) if height is not None else "0x0"

async def eth_getBalance(address: str, block: str, db: AsyncSession) -> str:
    """Returns balance in hex wei-equivalent"""
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
    # In this simplified RPC, we expect hex-encoded JSON string for VITTransaction
    try:
        if raw_tx_hex.startswith("0x"):
            raw_tx_hex = raw_tx_hex[2:]

        tx_data = json.loads(bytes.fromhex(raw_tx_hex).decode("utf-8"))
        tx = VITTransaction(
            from_address=tx_data["from_address"],
            to_address=tx_data["to_address"],
            amount=Decimal(tx_data["amount"]),
            nonce=tx_data["nonce"],
            timestamp=tx_data["timestamp"],
            gas_fee=Decimal(tx_data["gas_fee"]),
            data=tx_data.get("data"),
            signature=tx_data["signature"],
            tx_hash=tx_data.get("tx_hash", "")
        )

        chain = VITChain()
        success = chain.mempool.add(tx)
        if success:
            return tx.tx_hash
        else:
            raise ValueError("Invalid transaction or duplicate")

    except Exception as e:
        raise ValueError(f"Failed to process raw transaction: {str(e)}")

async def eth_getBlockByNumber(block_number: str, full_txs: bool, db: AsyncSession) -> dict:
    """Returns block in Ethereum block format (MetaMask compatible)"""
    if block_number == "latest":
        stmt = select(ChainBlock).order_by(desc(ChainBlock.height)).limit(1)
    else:
        height = int(block_number, 16)
        stmt = select(ChainBlock).where(ChainBlock.height == height)

    result = await db.execute(stmt)
    block = result.scalar_one_or_none()
    if not block:
        return None

    return {
        "number": to_hex(block.height),
        "hash": block.block_hash,
        "parentHash": block.prev_hash,
        "timestamp": to_hex(block.timestamp),
        "transactions": [] # Simplified
    }

async def eth_getTransactionByHash(tx_hash: str, db: AsyncSession) -> dict:
    result = await db.execute(select(ChainTransaction).where(ChainTransaction.tx_hash == tx_hash))
    tx = result.scalar_one_or_none()
    if not tx:
        return None
    return {
        "hash": tx.tx_hash,
        "blockNumber": to_hex(tx.block_height) if tx.block_height else None,
        "from": tx.from_address,
        "to": tx.to_address,
        "value": vit_to_wei_hex(tx.amount),
        "nonce": to_hex(tx.nonce)
    }

async def eth_getTransactionReceipt(tx_hash: str, db: AsyncSession) -> dict:
    result = await db.execute(select(ChainTransaction).where(ChainTransaction.tx_hash == tx_hash))
    tx = result.scalar_one_or_none()
    if not tx:
        return None
    return {
        "transactionHash": tx.tx_hash,
        "blockNumber": to_hex(tx.block_height),
        "status": "0x1" if tx.status == "confirmed" else "0x0"
    }

async def eth_call(call_object: dict, block: str, db: AsyncSession) -> str:
    return "0x"

async def eth_gasPrice() -> str:
    return hex(1000000000) # 1 gwei

async def eth_estimateGas(call_object: dict) -> str:
    return "0x5208" # 21000
