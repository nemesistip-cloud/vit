import asyncio
import logging
import random
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.modules.storage_verification.models import StorageProof, StorageProofStatus
from app.modules.storage_verification.service import issue_challenge, respond_to_challenge

logger = logging.getLogger(__name__)

class TachyonVerificationWorker:
    """
    Background worker that periodically audits storage nodes.
    """

    def __init__(self, interval_seconds: int = 3600):
        self.interval = interval_seconds
        self.running = False

    async def start(self):
        self.running = True
        logger.info(f"Tachyon Verification Worker started (interval: {self.interval}s)")
        while self.running:
            try:
                await self.audit_cycle()
            except Exception as e:
                logger.error(f"Error in verification audit cycle: {e}")
            await asyncio.sleep(self.interval)

    async def stop(self):
        self.running = False

    async def audit_cycle(self):
        """Randomly challenge a subset of anchored proofs."""
        async with AsyncSessionLocal() as db:
            # Find anchored proofs to challenge
            stmt = select(StorageProof).where(
                StorageProof.status == StorageProofStatus.ANCHORED
            ).limit(10)

            result = await db.execute(stmt)
            proofs = result.scalars().all()

            if not proofs:
                return

            logger.info(f"Issuing challenges for {len(proofs)} storage proofs")
            for proof in proofs:
                challenge = await issue_challenge(db, proof.id)
                # In this simulated cycle, we will auto-respond with valid data
                # to simulate nodes being honest.
                # In a real distributed system, the node would receive the challenge via RPC.

                # Simulate network delay
                await asyncio.sleep(0.5)

                # For simulation, just provide valid response
                # (The expected hash was derived from proof.proof_hash in service.py)
                # Here we just trigger the resolution logic
                await respond_to_challenge(db, challenge.id, "simulated_honest_response_data")

            logger.info("Verification audit cycle complete")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = TachyonVerificationWorker(interval_seconds=10)
    asyncio.run(worker.start())
