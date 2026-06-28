import json
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .block import VITBlock, validate_block
from .transaction import VITTransaction, Mempool
from .state import ChainState
from app.db.models import IoTEvent
from ..storage.db import ChainBlock, ChainTransaction, ChainAccount
from ..storage.indexer import ChainIndexer
from decimal import Decimal

class VITChain:
    CHAIN_ID = 7764
    GENESIS_HASH = "8f0376d859187321685794178550186178864700877041857917856018617886"

    # Singleton instance for shared mempool
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VITChain, cls).__new__(cls)
            cls._instance.state = ChainState()
            cls._instance.indexer = ChainIndexer()
            cls._instance.mempool = Mempool()
        return cls._instance

    def __init__(self):
        # Already initialized in __new__
        pass

    def _to_block(self, event: IoTEvent) -> VITBlock:
        p = event.payload
        txs = []
        for tx_data in p.get("transactions", []):
            txs.append(VITTransaction(
                from_address=tx_data["from_address"],
                to_address=tx_data["to_address"],
                amount=Decimal(tx_data["amount"]),
                nonce=tx_data["nonce"],
                timestamp=tx_data["timestamp"],
                gas_fee=Decimal(tx_data["gas_fee"]),
                data=tx_data.get("data"),
                signature=tx_data["signature"],
                status=tx_data["status"],
                tx_hash=tx_data["tx_hash"]
            ))

        return VITBlock(
            height=p["height"],
            prev_hash=p["prev_hash"],
            merkle_root=p["merkle_root"],
            timestamp=p["timestamp"],
            validator_id=p["validator_id"],
            transactions=txs,
            tx_count=p["tx_count"],
            total_fees=Decimal(p["total_fees"]),
            block_reward=Decimal(p["block_reward"]),
            validator_signature=p["validator_signature"],
            block_hash=p["block_hash"],
            storage_proofs=p.get("storage_proofs", []),
            consensus_votes=p.get("consensus_votes", [])
        )

    async def get_latest_block(self, db: AsyncSession) -> Optional[VITBlock]:
        """Returns the block with the highest height."""
        result = await db.execute(
            select(IoTEvent)
            .where(IoTEvent.source == "vitchain_block")
            .order_by(IoTEvent.id.desc())
            .limit(1)
        )
        event = result.scalar_one_or_none()
        return self._to_block(event) if event else None

    async def get_block_by_height(self, db: AsyncSession, height: int) -> Optional[VITBlock]:
        result = await db.execute(
            select(IoTEvent)
            .where(IoTEvent.source == "vitchain_block")
            .where(IoTEvent.payload["height"].as_integer() == height)
            .limit(1)
        )
        event = result.scalar_one_or_none()
        return self._to_block(event) if event else None

    async def get_block_by_hash(self, db: AsyncSession, block_hash: str) -> Optional[VITBlock]:
        result = await db.execute(
            select(IoTEvent)
            .where(IoTEvent.source == "vitchain_block")
            .where(IoTEvent.payload["block_hash"].as_string() == block_hash)
            .limit(1)
        )
        event = result.scalar_one_or_none()
        return self._to_block(event) if event else None

    async def add_block(self, db: AsyncSession, block: VITBlock) -> bool:
        """
        Validates block, applies all transactions, updates state, and indexes.
        Returns False if invalid
        """
        latest = await self.get_latest_block(db)
        # 1. Validate block structure and signature
        if not validate_block(block, latest, []):
            return False

        # 2. Apply transactions and rewards to core state (Wallet/User)
        for tx in block.transactions:
            success = await self.state.apply_transaction(db, tx)
            if not success:
                return False

        await self.state.apply_block_reward(db, block.validator_id, block.block_reward + block.total_fees)

        # 3. Persist the block in IoTEvent (Legacy storage compatibility)
        p = {
            "height": block.height,
            "prev_hash": block.prev_hash,
            "merkle_root": block.merkle_root,
            "timestamp": block.timestamp,
            "validator_id": block.validator_id,
            "validator_signature": block.validator_signature,
            "block_hash": block.block_hash,
            "tx_count": block.tx_count,
            "total_fees": str(block.total_fees),
            "block_reward": str(block.block_reward),
            "transactions": [tx.to_dict() for tx in block.transactions],
            "storage_proofs": block.storage_proofs,
            "consensus_votes": block.consensus_votes
        }
        event = IoTEvent(
            source="vitchain_block",
            event_type="block_finalized",
            payload=p
        )
        db.add(event)

        # 4. Index block into dedicated chain tables (Session 1.3 storage)
        state_root = await self.state.get_state_root(db)
        await self.indexer.index_block(db, block, state_root=state_root)

        return True

    async def get_transaction(self, db: AsyncSession, tx_hash: str) -> Optional[VITTransaction]:
        # Simple search through blocks for now
        result = await db.execute(
            select(IoTEvent)
            .where(IoTEvent.source == "vitchain_block")
            .where(IoTEvent.payload["transactions"].as_json().contains([{"tx_hash": tx_hash}]))
        )
        event = result.scalar_one_or_none()
        if event:
            block = self._to_block(event)
            for tx in block.transactions:
                if tx.tx_hash == tx_hash:
                    return tx
        return None

    async def pending_transactions(self, db: AsyncSession) -> list[VITTransaction]:
        return self.mempool.get_pending()

    async def chain_height(self, db: AsyncSession) -> int:
        latest = await self.get_latest_block(db)
        return latest.height if latest else -1
