import json
import logging
from decimal import Decimal
from typing import Optional, Callable, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from .block import VITBlock, validate_block
from .transaction import VITTransaction
from .state import ChainState
from app.db.models import IoTEvent

logger = logging.getLogger(__name__)


class _BlockTransactionRejected(Exception):
    pass


class VITChain:
    CHAIN_ID = 7764
    GENESIS_HASH = "8f0376d859187321685794178550186178864700877041857917856018617886"

    def __init__(self):
        self.state = ChainState()

    def _to_block(self, event: IoTEvent) -> VITBlock:
        p = event.payload
        txs = []
        for tx_data in p.get("transactions", []):
            txs.append(VITTransaction(
                from_address=tx_data["from_address"],
                to_address=tx_data["to_address"],
                amount=Decimal(str(tx_data["amount"])),
                nonce=int(tx_data["nonce"]),
                timestamp=int(tx_data["timestamp"]),
                gas_fee=Decimal(str(tx_data.get("gas_fee", "0.001"))),
                data=tx_data.get("data"),
                signature=tx_data.get("signature", ""),
                status=tx_data.get("status", "confirmed"),
                tx_hash=tx_data.get("tx_hash", "")
            ))

        return VITBlock(
            height=int(p["height"]),
            prev_hash=p["prev_hash"],
            merkle_root=p["merkle_root"],
            timestamp=int(p["timestamp"]),
            validator_id=p["validator_id"],
            transactions=txs,
            tx_count=int(p.get("tx_count", len(txs))),
            total_fees=Decimal(str(p.get("total_fees", "0"))),
            block_reward=Decimal(str(p.get("block_reward", "0"))),
            validator_signature=p.get("validator_signature", ""),
            block_hash=p.get("block_hash", ""),
            storage_proofs=p.get("storage_proofs", []),
            consensus_votes=p.get("consensus_votes", []),
            state_commitment=p.get("state_commitment", ""),
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

    async def add_block(self, arg1: Any, arg2: Any = None,
                        known_validators: list[str] = None,
                        consensus_validator: Callable = None) -> bool:
        """
        Validates block, applies all transactions, updates state.
        Supports both add_block(db, block) and add_block(block, db).
        """
        if isinstance(arg1, AsyncSession) and isinstance(arg2, VITBlock):
            db, block = arg1, arg2
        elif isinstance(arg1, VITBlock) and isinstance(arg2, AsyncSession):
            block, db = arg1, arg2
        else:
            raise TypeError("add_block requires both an AsyncSession and a VITBlock instance")

        latest = await self.get_latest_block(db)
        # 1. Validate block structure, signature and consensus rules
        if not validate_block(block, latest, known_validators, consensus_validator):
            return False

        try:
            async with db.begin_nested():
                # 2. Apply transactions and rewards atomically with block persistence.
                for tx in block.transactions:
                    success = await self.state.apply_transaction(db, tx)
                    if not success:
                        raise _BlockTransactionRejected

                await self.state.apply_block_reward(
                    db,
                    block.validator_id,
                    block.block_reward + block.total_fees,
                )

                # 3. Persist the block
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
                    "state_commitment": block.state_commitment,
                    "storage_proofs": block.storage_proofs,
                    "consensus_votes": block.consensus_votes,
                }
                db.add(IoTEvent(
                    source="vitchain_block",
                    event_type="block_finalized",
                    payload=p,
                ))

                # Index block into ChainBlock, ChainTransaction, ChainAccount.
                from vit_chain.storage.indexer import ChainIndexer
                await ChainIndexer().index_block(db, block)

                # Persist into the legacy Block model when available.
                try:
                    from app.db.models import Block
                    res = await db.execute(select(Block).where(Block.height == block.height))
                    if not res.scalar_one_or_none():
                        db.add(Block(
                            height=block.height,
                            chain_id=self.CHAIN_ID,
                            hash=block.block_hash,
                            parent_hash=block.prev_hash,
                            proposer=block.validator_id,
                            tx_count=block.tx_count,
                            extra_data=f"VIT Chain block height={block.height}",
                        ))
                except Exception as exc:
                    logger.warning("[vitchain] Could not persist Block model: %s", exc)
        except _BlockTransactionRejected:
            return False

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
        return []

    async def chain_height(self, db: AsyncSession) -> int:
        latest = await self.get_latest_block(db)
        return latest.height if latest else -1

    async def get_height(self, db: AsyncSession) -> int:
        """Alias for chain_height to align with P2P and RPC callers."""
        return await self.chain_height(db)

    async def get_blocks(self, start_or_db: Any, end_or_start: Any, db_or_end: Any = None) -> list[dict]:
        """
        Fetch block payload dictionaries between start and end heights (inclusive).
        Supports flexible parameter ordering: (start, end, db) or (db, start, end).
        """
        if isinstance(start_or_db, AsyncSession):
            db = start_or_db
            start = int(end_or_start)
            end = int(db_or_end)
        else:
            start = int(start_or_db)
            end = int(end_or_start)
            db = db_or_end

        result = await db.execute(
            select(IoTEvent)
            .where(IoTEvent.source == "vitchain_block")
            .order_by(IoTEvent.id)
        )
        events = result.scalars().all()
        matching = []
        for ev in events:
            p = ev.payload or {}
            h = p.get("height")
            if h is not None and start <= int(h) <= end:
                matching.append(p)
        return matching
