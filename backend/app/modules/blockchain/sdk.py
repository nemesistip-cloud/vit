import logging
import time
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.kernel import kernel
from vit_chain.core.transaction import VITTransaction, create_transaction
from vit_chain.storage.db import ChainAccount

logger = logging.getLogger(__name__)

class BlockchainSDK:
    """
    High-level SDK for VIT subsystems to interact with the blockchain.
    Provides a stable, simplified interface for common operations.
    """

    def __init__(self, subsystem):
        self.subsystem = subsystem
        self.manager = subsystem.manager

    async def get_balance(self, db: AsyncSession, address: str) -> Decimal:
        """Returns the current balance for an address."""
        stmt = select(ChainAccount.balance).where(ChainAccount.address == address)
        res = await db.execute(stmt)
        return res.scalar_one_or_none() or Decimal("0")

    async def submit_transaction(self,
                                 from_key: str,
                                 to_address: str,
                                 amount: Decimal,
                                 data: Optional[Dict] = None) -> str:
        """
        Creates, signs, and submits a transaction to the mempool.
        Returns the transaction hash.
        """
        # 1. Determine nonce (should be handled by a higher-level wallet service,
        # but for SDK we can try to fetch current nonce + 1)
        # Note: This is simplified; real systems need careful nonce management.
        from vit_chain.crypto.address import public_key_to_address
        from coincurve import PrivateKey

        priv = PrivateKey.from_hex(from_key)
        from_address = public_key_to_address(priv.public_key.format(compressed=False).hex())

        # In a real app, we'd use a DB session here.
        # But SDK might be called from contexts where session isn't readily available.
        # For now, we assume the caller provides a session or we use a temporary one.
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            stmt = select(ChainAccount.nonce).where(ChainAccount.address == from_address)
            res = await db.execute(stmt)
            current_nonce = res.scalar_one_or_none() or 0

        tx = create_transaction(
            from_key=from_key,
            to_address=to_address,
            amount=amount,
            nonce=current_nonce,
            data=data,
            timestamp=int(time.time())
        )

        success = await self.manager.add_transaction(tx)
        if not success:
            raise ValueError("Transaction rejected by mempool")

        return tx.tx_hash

    async def get_block(self, db: AsyncSession, height_or_hash: Any) -> Optional[Dict[str, Any]]:
        """Retrieves block details as a dictionary."""
        if isinstance(height_or_hash, int) or (isinstance(height_or_hash, str) and height_or_hash.isdigit()):
            block = await self.manager.get_block_by_height(db, int(height_or_hash))
        else:
            block = await self.manager.get_block_by_hash(db, str(height_or_hash))

        return block.to_dict() if block else None

    async def get_transaction(self, db: AsyncSession, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves transaction details and status."""
        return await self.manager.get_transaction(db, tx_hash)

    async def get_status(self) -> Dict[str, Any]:
        """Returns basic health and status of the blockchain subsystem."""
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            height = await self.manager.chain.chain_height(db)
            mempool = await self.manager.get_mempool_stats()

        return {
            "height": height,
            "mempool": mempool,
            "subsystem_healthy": await self.subsystem.health_check()
        }
