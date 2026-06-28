from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from .db import ChainBlock, ChainTransaction, ChainAccount
from ..core.block import VITBlock
from ..core.transaction import VITTransaction
import datetime

class ChainIndexer:
    async def index_block(self, db: AsyncSession, block: VITBlock, state_root: str = ""):
        """Writes ChainBlock + all ChainTransactions + updates ChainAccounts"""
        # Ensure session is active
        if not db.is_active:
            await db.begin()

        # 1. Create ChainBlock
        cb = ChainBlock(
            height=block.height,
            block_hash=block.block_hash,
            prev_hash=block.prev_hash,
            merkle_root=block.merkle_root,
            state_root=state_root,
            timestamp=block.timestamp,
            validator_id=block.validator_id,
            validator_signature=block.validator_signature,
            tx_count=block.tx_count,
            total_fees=block.total_fees,
            block_reward=block.block_reward,
            raw_data={
                "height": block.height,
                "timestamp": block.timestamp,
                "validator_id": block.validator_id,
                "tx_count": block.tx_count
            }
        )
        db.add(cb)

        # 2. Create ChainTransactions and update Accounts
        for tx in block.transactions:
            ctx = ChainTransaction(
                tx_hash=tx.tx_hash,
                block_height=block.height,
                from_address=tx.from_address,
                to_address=tx.to_address,
                amount=tx.amount,
                nonce=tx.nonce,
                gas_fee=tx.gas_fee,
                tx_type=tx.data.get("type", "transfer") if tx.data else "transfer",
                data=tx.data,
                signature=tx.signature,
                timestamp=tx.timestamp,
                status="confirmed"
            )
            db.add(ctx)

            # Update Sender Account
            await self._update_account(db, tx.from_address, block.height, debit=tx.amount + tx.gas_fee, nonce=tx.nonce + 1)
            # Update Recipient Account
            await self._update_account(db, tx.to_address, block.height, credit=tx.amount)

        # 3. Apply validator reward to Account
        total_reward = block.block_reward + block.total_fees
        # Skip reward update if validator is the sender (handled in tx loop)
        # to avoid overwriting or double counting in simple tests if not careful.
        # Actually, validator reward should ALWAYS be added.
        # But in my test, addr is both sender and validator.
        # addr balance before: 100
        # tx debit: 10.001 -> 89.999
        # validator reward: 10 + 0.001 = 10.001 -> 100.000
        # This is correct blockchain logic. My test expectation was wrong.
        await self._update_account(db, block.validator_id, block.height, credit=total_reward)

    async def _update_account(self, db: AsyncSession, address: str, height: int,
                              credit: Decimal = Decimal("0"), debit: Decimal = Decimal("0"),
                              nonce: int = None):
        result = await db.execute(select(ChainAccount).where(ChainAccount.address == address))
        acc = result.scalar_one_or_none()
        if not acc:
            acc = ChainAccount(
                address=address,
                balance=Decimal("0"),
                nonce=0,
                first_seen_height=height,
                last_active_height=height
            )
            db.add(acc)

        acc.balance = acc.balance + Decimal(str(credit)) - Decimal(str(debit))
        if nonce is not None:
            acc.nonce = nonce
        acc.last_active_height = height

    async def get_blocks(self, db: AsyncSession, limit: int = 20, offset: int = 0) -> list[ChainBlock]:
        result = await db.execute(
            select(ChainBlock).order_by(desc(ChainBlock.height)).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_transactions_for_address(self, db: AsyncSession, address: str, limit: int = 50) -> list[ChainTransaction]:
        result = await db.execute(
            select(ChainTransaction)
            .where((ChainTransaction.from_address == address) | (ChainTransaction.to_address == address))
            .order_by(desc(ChainTransaction.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_chain_stats(self, db: AsyncSession) -> dict:
        """Returns summary of the chain state."""
        total_blocks = await db.scalar(select(func.count(ChainBlock.height))) or 0
        total_txs = await db.scalar(select(func.count(ChainTransaction.tx_hash))) or 0
        total_accounts = await db.scalar(select(func.count(ChainAccount.address))) or 0

        latest_res = await db.execute(select(ChainBlock).order_by(desc(ChainBlock.height)).limit(1))
        latest = latest_res.scalar_one_or_none()

        circ = await db.scalar(select(func.sum(ChainAccount.balance))) or Decimal("0")

        # Explicitly flush to ensure data is visible to queries in same session
        await db.flush()

        return {
            "total_blocks": total_blocks,
            "total_transactions": total_txs,
            "total_accounts": total_accounts,
            "latest_block_height": latest.height if latest else -1,
            "latest_block_time": latest.timestamp if latest else 0,
            "avg_block_time_seconds": 15, # Constant for now
            "total_vit_in_circulation": str(circ)
        }
