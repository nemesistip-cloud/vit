"""Celery tasks for automated settlement — Track 7.3"""

import asyncio
import logging
from sqlalchemy import select
from app.db.database import get_db
from app.worker import celery_app
from app.services.oracle_settlement_bridge import OracleSettlementBridge
from app.modules.blockchain.models import OracleResult, ConsensusPrediction, ConsensusStatus

logger = logging.getLogger(__name__)

@celery_app.task(name="oracle_settlement_check")
def oracle_settlement_check():
    """
    Periodic task to check for matches with sufficient oracle results
    and trigger consensus-based settlement.
    """
    async def run():
        async for db in get_db():
            try:
                # Find matches with at least one oracle result but not yet settled
                stmt = select(OracleResult.match_id).distinct()
                res = await db.execute(stmt)
                match_ids = res.scalars().all()

                if not match_ids:
                    return

                # Filter match_ids to only those not settled in ConsensusPrediction
                unsettled_res = await db.execute(
                    select(ConsensusPrediction.match_id).where(
                        ConsensusPrediction.match_id.in_(match_ids),
                        ConsensusPrediction.status != ConsensusStatus.SETTLED.value
                    )
                )
                pending_ids = unsettled_res.scalars().all()

                for match_id in pending_ids:
                    try:
                        logger.info(f"[task] Checking consensus for match {match_id}")
                        # OracleSettlementBridge.check_and_settle handles 67% threshold logic
                        await OracleSettlementBridge.check_and_settle(match_id, db)
                        await db.commit()
                    except Exception as me:
                        logger.error(f"[task] Error settling match {match_id}: {me}")
                        await db.rollback()
            except Exception as e:
                logger.error(f"[task] oracle_settlement_check error: {e}")
                await db.rollback()
            break

    # Run the async loop inside the sync Celery task
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # This shouldn't happen in a Celery worker unless misconfigured
        asyncio.create_task(run())
    else:
        loop.run_until_complete(run())
