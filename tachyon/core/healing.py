import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.modules.storage_verification.models import TachyonManifest
from tachyon.core.erasure import ReedSolomonCodec
from tachyon.core.providers.pool import ProviderPool
from tachyon.core.manifest import ManifestManager
from tachyon.core.retrieval import ShardRetriever

logger = logging.getLogger(__name__)

class SelfHealingManager:
    def __init__(self):
        self.manifests = ManifestManager()
        self.retriever = ShardRetriever()

    async def heal_manifest(self, db: AsyncSession,
                             manifest: TachyonManifest,
                             pool: ProviderPool,
                             codec: ReedSolomonCodec) -> bool:
        """
        Attempt to repair a degraded manifest.
        """
        file_id = manifest.file_id
        shard_locations = manifest.provider_mapping.get("shards", [])

        # 1. Download all shards (some may return None)
        total_expected = 9 # Assuming 6+3
        shards_with_nones = [None] * total_expected

        downloaded = await self.retriever.retrieve_shards_parallel(shard_locations, pool)

        missing_indices = []
        for i, loc in enumerate(sorted(shard_locations, key=lambda x: x["shard_index"])):
             if i < len(downloaded) and downloaded[i] is not None:
                 shards_with_nones[loc["shard_index"]] = downloaded[i]
             else:
                 missing_indices.append(loc["shard_index"])

        # 2. If all healthy: return True
        if not missing_indices and len(shard_locations) == total_expected:
            await self.manifests.update_health(db, file_id, 1.0, datetime.now(timezone.utc))
            return True

        # 3. Try to decode with available shards
        try:
            data = codec.decode(shards_with_nones, data_shards=6, parity_shards=3)
        except Exception as e:
            logger.error(f"Healing failed for {file_id}: data unrecoverable ({e})")
            return False

        # 4. Re-encode to get full 9 shards again
        all_shards = codec.encode(data, data_shards=6, parity_shards=3)

        # 5. Re-upload missing shards to healthy providers
        new_shard_locations = []
        # Keep existing healthy shards
        for loc in shard_locations:
            if loc["shard_index"] not in missing_indices:
                new_shard_locations.append(loc)

        # Repair missing ones
        async def _repair_one(idx):
            shard_id = f"{file_id}_{idx}"
            try:
                provider_id, drive_file_id = await pool.upload_shard(shard_id, all_shards[idx])
                return {
                    "shard_index": idx,
                    "provider_id": provider_id,
                    "file_id": drive_file_id,
                    "shard_hash": codec.shard_hash(all_shards[idx]),
                    "size_bytes": len(all_shards[idx])
                }
            except Exception as e:
                logger.error(f"Failed to repair shard {idx} for {file_id}: {e}")
                return None

        repair_results = await asyncio.gather(*[_repair_one(idx) for idx in missing_indices])
        new_shard_locations.extend([r for r in repair_results if r is not None])

        # 6. Update manifest shard_locations
        manifest.provider_mapping["shards"] = sorted(new_shard_locations, key=lambda x: x["shard_index"])

        # 7. Update health_score to 1.0
        manifest.provider_mapping["_metadata"]["health_score"] = 1.0
        manifest.provider_mapping["_metadata"]["last_verified_at"] = datetime.now(timezone.utc).isoformat()
        flag_modified(manifest, "provider_mapping")
        await db.flush()

        # 8. Publish: vit:tachyon:healed {file_id, repaired_shards}
        try:
            from app.services.cache import _get_redis
            redis = _get_redis()
            if redis:
                event = {
                    "file_id": file_id,
                    "repaired_shards": len([r for r in repair_results if r is not None])
                }
                await redis.publish("vit:tachyon:healed", json.dumps(event))
        except Exception as e:
            logger.warning(f"Failed to publish healing event: {e}")

        return True

    async def healing_loop(self):
        """
        Background task to repair degraded manifests.
        """
        logger.info("Tachyon healing loop started")
        from tachyon.core.erasure import ReedSolomonCodec
        from tachyon.core.providers.pool import ProviderPool
        from app.db.database import AsyncSessionLocal

        codec = ReedSolomonCodec()
        pool = ProviderPool()

        while True:
            try:
                async with AsyncSessionLocal() as db:
                    degraded = await self.manifests.get_degraded(db)
                    if degraded:
                        logger.info(f"Found {len(degraded)} degraded manifests, starting repair...")
                        for manifest in degraded:
                            async with db.begin():
                                await self.heal_manifest(db, manifest, pool, codec)

                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Error in healing loop: {e}")
                await asyncio.sleep(60)
