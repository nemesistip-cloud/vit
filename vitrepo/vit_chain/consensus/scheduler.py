import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from app.db.database import AsyncSessionLocal
from vit_chain.consensus.challenge import ChallengeGenerator, CHALLENGE_WINDOW_SECONDS
from vit_chain.consensus.verifier import ChallengeVerifier
from app.services.cache import _get_redis

logger = logging.getLogger(__name__)

EPOCH_SECONDS = 15

class EpochScheduler:
    def __init__(self):
        self.generator = ChallengeGenerator()
        self.verifier = ChallengeVerifier()
        self._running = False

    async def run(self):
        """Infinite consensus loop: generate challenges, wait, aggregate results."""
        self._running = True
        try:
            while self._running:
                now = time.time()
                next_epoch_start = (int(now // EPOCH_SECONDS) + 1) * EPOCH_SECONDS
                await asyncio.sleep(next_epoch_start - now)

                current_epoch = int(time.time() // EPOCH_SECONDS)

                # 1. Generate challenges in a separate session
                async with AsyncSessionLocal() as db:
                    try:
                        await self.generator.generate_epoch_challenges(db, current_epoch)
                    except Exception as e:
                        logger.error(f"[consensus] Generation failed for epoch {current_epoch}: {e}")
                        await db.rollback()

                # 2. Wait for the 10-second response window
                await asyncio.sleep(CHALLENGE_WINDOW_SECONDS)

                # 3. Aggregate results in a fresh session
                async with AsyncSessionLocal() as db:
                    try:
                        results = await self.verifier.collect_epoch_results(db, current_epoch)
                        await self._publish_epoch_complete(current_epoch, results)

                        if results.get("consensus_weight", 0.0) >= 0.67:
                            await self._trigger_block_production(current_epoch)
                    except Exception as e:
                        logger.error(f"[consensus] Aggregation failed for epoch {current_epoch}: {e}")
                        await db.rollback()

        except asyncio.CancelledError:
            self._running = False
        except Exception as e:
            logger.critical(f"[consensus] EpochScheduler crashed: {e}")
            self._running = False

    async def _publish_epoch_complete(self, epoch: int, results: dict):
        r = _get_redis()
        if r:
            payload = {"epoch": epoch, "results": results, "timestamp": datetime.now(timezone.utc).isoformat()}
            try:
                await r.publish("vit:consensus:epoch_complete", json.dumps(payload))
            except Exception:
                pass

    async def _trigger_block_production(self, epoch: int):
        r = _get_redis()
        if r:
            try:
                await r.publish(f"vit:consensus:produce_block:{epoch}", json.dumps({"epoch": epoch}))
            except Exception:
                pass
