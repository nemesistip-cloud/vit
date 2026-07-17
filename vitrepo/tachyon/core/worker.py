import asyncio
import logging
import random
import json
from datetime import datetime, timezone
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.modules.storage_verification.models import TachyonManifest
from tachyon.core.orchestrator import TachyonOrchestrator
from tachyon.core.healing import SelfHealingManager

logger = logging.getLogger(__name__)

class TachyonVerificationWorker:
    """
    Background worker that periodically audits Tachyon manifests.
    """

    def __init__(self, interval_seconds: int = 3600):
        self.interval = interval_seconds
        self.running = False
        self.orchestrator = TachyonOrchestrator()
        self.healing = SelfHealingManager()

    async def start(self):
        self.running = True
        logger.info(f"Tachyon Verification Worker started (interval: {self.interval}s)")
        while self.running:
            try:
                await self.run_verification_cycle()
            except Exception as e:
                logger.error(f"Error in verification audit cycle: {e}")
            await asyncio.sleep(self.interval)

    async def stop(self):
        self.running = False

    async def run_verification_cycle(self):
        """Audit up to 50 manifests with the oldest last_verified_at."""
        async with AsyncSessionLocal() as db:
            # We need to sort by last_verified_at stored in JSON
            # Since SQL sorting on JSON can be complex, we fetch active ones and sort in Python
            # In production, we'd use a more optimized query or a dedicated column
            stmt = select(TachyonManifest).limit(200) # Buffer to find candidates
            result = await db.execute(stmt)
            manifests = result.scalars().all()

            # Filter active and sort by last_verified_at
            candidates = []
            for m in manifests:
                meta = m.provider_mapping.get("_metadata", {})
                if meta.get("status") == "active":
                    lva_str = meta.get("last_verified_at")
                    lva = datetime.fromisoformat(lva_str) if lva_str else datetime.min
                    candidates.append((lva, m))

            candidates.sort(key=lambda x: x[0])
            to_verify = [c[1] for c in candidates[:50]]

            if not to_verify:
                return

            logger.info(f"Auditing {len(to_verify)} Tachyon manifests")
            stats = {"checked": 0, "healthy": 0, "degraded": 0, "healed": 0}

            for manifest in to_verify:
                try:
                    result = await self.orchestrator.verify(db, manifest.file_id)
                    stats["checked"] += 1
                    if result["verified"]:
                        stats["healthy"] += 1
                    else:
                        stats["degraded"] += 1
                        # Publish degradation event
                        from app.services.cache import _get_redis
                        redis = _get_redis()
                        if redis:
                            await redis.publish("vit:tachyon:shard_degraded", json.dumps({"file_id": manifest.file_id}))

                        # Trigger healing
                        logger.info(f"Triggering healing for degraded manifest: {manifest.file_id}")
                        async with db.begin_nested():
                            healed = await self.healing.heal_manifest(db, manifest, self.orchestrator.pool, self.orchestrator.codec)
                            if healed:
                                stats["healed"] += 1
                except Exception as e:
                    logger.error(f"Failed to verify/heal {manifest.file_id}: {e}")

            await db.commit()
            logger.info(f"Verification audit cycle complete: {stats}")

    async def audit_cycle(self):
        # Compatibility shim for old interface if needed, but spec says update to manifest verification
        await self.run_verification_cycle()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = TachyonVerificationWorker(interval_seconds=10)
    asyncio.run(worker.start())
