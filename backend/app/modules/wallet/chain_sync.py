# app/modules/wallet/chain_sync.py
"""Celery tasks for synchronizing state between DB and VIT Chain."""

import logging
from decimal import Decimal
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models import User
from app.modules.wallet.models import Wallet
from vit_chain.core.state import ChainState

logger = logging.getLogger(__name__)

@shared_task(name="sync_chain_balances")
async def sync_chain_balances():
    """
    Every 5 minutes:
    Compares DB wallet balances with native VIT Chain balances.
    Logs discrepancies > 0.001 VIT for admin review.
    """
    async with AsyncSessionLocal() as db:
        # 1. Fetch all users with a wallet address
        result = await db.execute(
            select(User, Wallet)
            .join(Wallet, User.id == Wallet.user_id)
            .where(User.wallet_address != None)
        )
        rows = result.all()

        state = ChainState()
        discrepancies = []

        for user, wallet in rows:
            # 2. Get on-chain balance
            on_chain_bal = await state.get_balance(db, user.wallet_address)
            db_bal = wallet.vitcoin_balance

            diff = abs(on_chain_bal - db_bal)

            # 3. Log if discrepancy > 0.001 VIT
            if diff > Decimal("0.001"):
                discrepancy = {
                    "user_id": user.id,
                    "address": user.wallet_address,
                    "db_balance": float(db_bal),
                    "chain_balance": float(on_chain_bal),
                    "diff": float(diff)
                }
                discrepancies.append(discrepancy)
                logger.warning(
                    f"[CHAIN_SYNC_ALERT] Discrepancy detected for user {user.id} ({user.wallet_address}): "
                    f"DB={db_bal}, Chain={on_chain_bal}, Diff={diff}"
                )

        # In a full implementation, we might save these to a 'SyncAudit' table
        return {
            "processed": len(rows),
            "discrepancies_found": len(discrepancies),
            "discrepancies": discrepancies
        }
