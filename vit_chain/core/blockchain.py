"""
vit_chain/core/blockchain.py — High-level blockchain facade

This module re-exports the real implementations from transaction.py and
block.py, and provides a thin VITChain persistence wrapper used by the
API layer and consensus engine.

IMPORTANT: The real ECDSA verification logic lives in:
  - vit_chain/core/transaction.py  (VITTransaction, verify_transaction, Mempool)
  - vit_chain/core/block.py        (VITBlock, build_block, validate_block)

This facade delegates to those implementations rather than duplicating them.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from vit_chain.core.transaction import (   # noqa: F401  (re-export)
    VITTransaction,
    Mempool,
    create_transaction,
    verify_transaction,
)
from vit_chain.core.block import (          # noqa: F401  (re-export)
    VITBlock,
    build_block,
    validate_block,
)
from vit_chain.crypto.hash import sha256_hex  # noqa: F401

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton blockchain handle
# ---------------------------------------------------------------------------

_blockchain_instance: Optional["VITChain"] = None


def get_blockchain() -> "VITChain":
    """Return the process-wide VITChain singleton, creating it if needed."""
    global _blockchain_instance
    if _blockchain_instance is None:
        _blockchain_instance = VITChain()
    return _blockchain_instance


class VITChain:
    """
    Async persistence wrapper around the chain stored as IoTEvent rows in
    PostgreSQL.  The consensus engine and API routes use this to read/write
    blocks without knowing the storage details.
    """

    def __init__(self) -> None:
        self._height: int = 0

    # ------------------------------------------------------------------
    # Height
    # ------------------------------------------------------------------

    async def get_height(self, db: AsyncSession) -> int:
        """Return current chain height from the DB (or cached value)."""
        try:
            from app.db.models import IoTEvent
            result = await db.execute(
                select(func.max(IoTEvent.block_height)).where(
                    IoTEvent.event_type == "block"
                )
            )
            max_height = result.scalar()
            if max_height is not None:
                self._height = int(max_height)
        except Exception as exc:
            logger.debug("get_height DB fallback: %s", exc)
        return self._height

    # ------------------------------------------------------------------
    # Add block
    # ------------------------------------------------------------------

    async def add_block(self, block: VITBlock, db: AsyncSession) -> bool:
        """
        Persist a validated block to IoTEvent storage.
        Returns False if the block is invalid or already present.
        """
        # Validate before persisting
        try:
            prev_block: Optional[VITBlock] = None
            if block.height > 0:
                prev_block = await self._load_block(block.height - 1, db)

            if not validate_block(block, prev_block):
                logger.warning(
                    "add_block: block %d failed validate_block()", block.height
                )
                return False
        except Exception as exc:
            logger.error("add_block: validation error for block %d: %s", block.height, exc)
            return False

        try:
            from app.db.models import IoTEvent
            import json
            event = IoTEvent(
                event_type="block",
                block_height=block.height,
                source="vit_chain",
                data=block.to_dict(),
            )
            db.add(event)
            await db.commit()
            if block.height > self._height:
                self._height = block.height
            return True
        except Exception as exc:
            await db.rollback()
            logger.error("add_block: DB error for block %d: %s", block.height, exc)
            return False

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_blocks(
        self, start: int, end: int, db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Return serialised block dicts for heights [start, end]."""
        try:
            from app.db.models import IoTEvent
            result = await db.execute(
                select(IoTEvent)
                .where(
                    IoTEvent.event_type == "block",
                    IoTEvent.block_height >= start,
                    IoTEvent.block_height <= end,
                )
                .order_by(IoTEvent.block_height)
                .limit(100)
            )
            rows = result.scalars().all()
            return [row.data for row in rows if row.data]
        except Exception as exc:
            logger.debug("get_blocks DB error: %s", exc)
            return []

    async def get_block(self, height: int, db: AsyncSession) -> Optional[Dict[str, Any]]:
        """Return a single block dict by height."""
        blocks = await self.get_blocks(height, height, db)
        return blocks[0] if blocks else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_block(self, height: int, db: AsyncSession) -> Optional[VITBlock]:
        """Load and deserialise a block from the DB (for validation chains)."""
        data = await self.get_block(height, db)
        if not data:
            return None
        try:
            from decimal import Decimal
            txs = [
                VITTransaction(
                    from_address=t["from_address"],
                    to_address=t["to_address"],
                    amount=Decimal(t["amount"]),
                    nonce=t["nonce"],
                    timestamp=t["timestamp"],
                    gas_fee=Decimal(t.get("gas_fee", "0.001")),
                    data=t.get("data"),
                    metadata=t.get("metadata", {}),
                    signature=t.get("signature", ""),
                    status=t.get("status", "confirmed"),
                    tx_hash=t.get("tx_hash", ""),
                )
                for t in data.get("transactions", [])
            ]
            return VITBlock(
                height=data["height"],
                prev_hash=data["prev_hash"],
                merkle_root=data["merkle_root"],
                timestamp=data["timestamp"],
                validator_id=data["validator_id"],
                transactions=txs,
                tx_count=data["tx_count"],
                total_fees=Decimal(data["total_fees"]),
                block_reward=Decimal(data["block_reward"]),
                version=data.get("version", 1),
                nonce=data.get("nonce", 0),
                metadata=data.get("metadata", {}),
                validator_signature=data.get("validator_signature", ""),
                block_hash=data.get("block_hash", ""),
                storage_proofs=data.get("storage_proofs", []),
                consensus_votes=data.get("consensus_votes", []),
            )
        except Exception as exc:
            logger.warning("_load_block deserialise error at height %d: %s", height, exc)
            return None
