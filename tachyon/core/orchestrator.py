import asyncio
import hashlib
import logging
import random
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_env
from app.core.errors import AppError
from app.modules.storage_verification.models import TachyonManifest
from tachyon.core.erasure import ReedSolomonCodec
from tachyon.core.providers.pool import ProviderPool
from tachyon.core.manifest import ManifestManager
from tachyon.core.retrieval import ShardRetriever

logger = logging.getLogger(__name__)

class TachyonOrchestrator:
    MAX_FILE_SIZE_MB = int(get_env("TACHYON_MAX_FILE_SIZE_MB", "100"))

    def __init__(self):
        self.pool = ProviderPool()
        self.codec = ReedSolomonCodec()
        self.manifests = ManifestManager()
        self.retriever = ShardRetriever()

    async def upload(self, db: AsyncSession,
                      file_id: str,
                      filename: str,
                      data: bytes,
                      metadata: dict = None,
                      owner_user_id: int = None) -> TachyonManifest:
        """
        Orchestrate parallel upload of erasure-coded shards.
        NEVER write to local disk.
        """
        # 1. Validate size
        if len(data) > self.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise AppError("File too large", status_code=413, code="file_too_large")

        # 2. Compute sha256
        sha256 = hashlib.sha256(data).hexdigest()

        # 3. Check for duplicate using JSON-aware query
        # Metadata is stored as {"_metadata": {"sha256": "..."}}
        # SQLite: TachyonManifest.provider_mapping["_metadata"]["sha256"].as_string() == sha256
        # Postgres: TachyonManifest.provider_mapping[("_metadata", "sha256")].as_string() == sha256
        print(f"DEBUG: Checking for duplicate with sha256: {sha256}")
        stmt = select(TachyonManifest).where(
            TachyonManifest.provider_mapping["_metadata"]["sha256"].as_string() == sha256
        ).limit(1)
        result = await db.execute(stmt)
        print(f"DEBUG: Result is {result}")
        existing = result.scalar_one_or_none()
        print(f"DEBUG: Existing is {existing}")
        if existing:
            return existing

        # 4. Encode
        shards = self.codec.encode(data, data_shards=6, parity_shards=3)

        # 5. Upload shards in parallel
        async def _upload_one(i, shard):
            shard_id = f"{file_id}_{i}"
            try:
                provider_id, drive_file_id = await self.pool.upload_shard(shard_id, shard)
                return {
                    "shard_index": i,
                    "provider_id": provider_id,
                    "file_id": drive_file_id,
                    "shard_hash": self.codec.shard_hash(shard),
                    "size_bytes": len(shard)
                }
            except Exception as e:
                logger.error(f"Shard {i} upload failed: {e}")
                return e

        results = await asyncio.gather(*[
            _upload_one(i, shard) for i, shard in enumerate(shards)
        ], return_exceptions=True)

        # 6. Check results
        successful_uploads = [r for r in results if isinstance(r, dict)]
        failures = len(results) - len(successful_uploads)

        if failures > 3:
            raise AppError("Upload failed: too many shard failures", status_code=503, code="upload_failed")

        # 7. Build shard_locations
        shard_locations = successful_uploads

        # 8. Create manifest
        manifest = await self.manifests.create(
            db, file_id, filename, len(data), sha256, shard_locations, owner_user_id
        )

        # 9. Publish Redis event
        try:
            from app.services.cache import _get_redis
            redis = _get_redis()
            if redis:
                event = {
                    "file_id": file_id,
                    "size_bytes": len(data),
                    "shard_count": len(shard_locations),
                    "owner_user_id": owner_user_id
                }
                await redis.publish("vit:tachyon:uploaded", json.dumps(event))
        except Exception as e:
            logger.warning(f"Failed to publish upload event: {e}")

        # 10. Return manifest
        return manifest

    async def retrieve(self, db: AsyncSession,
                        file_id: str) -> bytes:
        # 1. Load manifest
        manifest = await self.manifests.get(db, file_id)
        if not manifest:
            raise AppError("Manifest not found", status_code=404, code="not_found")

        shard_locations = manifest.provider_mapping.get("shards", [])

        # 2. Download shards in parallel
        total_expected = 9
        downloaded_shards = await self.retriever.retrieve_shards_parallel(shard_locations, self.pool)

        shards_with_nones = [None] * total_expected
        # Correctly map downloaded shards to their indices
        sorted_locs = sorted(shard_locations, key=lambda x: x["shard_index"])
        for i, loc in enumerate(sorted_locs):
             if i < len(downloaded_shards):
                 shards_with_nones[loc["shard_index"]] = downloaded_shards[i]

        # 3. Decode
        try:
            data = self.codec.decode(shards_with_nones, data_shards=6, parity_shards=3)
        except Exception as e:
            logger.error(f"Decoding failed for {file_id}: {e}")
            raise AppError("Retrieval failed: data unrecoverable", status_code=503, code="retrieval_failed")

        # 4. Verify sha256
        sha256 = hashlib.sha256(data).hexdigest()
        expected_sha256 = manifest.provider_mapping.get("_metadata", {}).get("sha256")
        if expected_sha256 and sha256 != expected_sha256:
            raise AppError("Data corruption detected", status_code=500, code="data_corrupt")

        # 5. Return data
        return data

    async def delete(self, db: AsyncSession, file_id: str) -> bool:
        # 1. Load manifest
        manifest = await self.manifests.get(db, file_id)
        if not manifest:
            return False

        shard_locations = manifest.provider_mapping.get("shards", [])

        # 2. Delete all shards from providers in parallel
        async def _delete_one(loc):
            try:
                return await self.pool.delete_shard(loc["provider_id"], loc["file_id"])
            except Exception as e:
                logger.error(f"Failed to delete shard {loc['shard_index']} from {loc['provider_id']}: {e}")
                return False

        await asyncio.gather(*[_delete_one(loc) for loc in shard_locations], return_exceptions=True)

        # 3. Mark manifest deleted
        await self.manifests.mark_deleted(db, file_id)

        # 4. Publish: vit:tachyon:deleted {file_id}
        try:
            from app.services.cache import _get_redis
            redis = _get_redis()
            if redis:
                await redis.publish("vit:tachyon:deleted", json.dumps({"file_id": file_id}))
        except Exception as e:
            logger.warning(f"Failed to publish delete event: {e}")

        return True

    async def verify(self, db: AsyncSession,
                      file_id: str) -> dict:
        """Challenge-response verification."""
        # 1. Load manifest
        manifest = await self.manifests.get(db, file_id)
        if not manifest:
            raise AppError("Manifest not found", status_code=404, code="not_found")

        shard_locations = manifest.provider_mapping.get("shards", [])
        if not shard_locations:
            return {"verified": False, "shards_checked": 0, "shards_healthy": 0, "degraded": True}

        # 2. Pick 3 random shard_locations
        to_check = random.sample(shard_locations, min(3, len(shard_locations)))

        # 3. Download those shards
        downloaded = await self.retriever.retrieve_shards_parallel(to_check, self.pool)

        # 4. Verify each hash matches manifest shard_hash
        shards_healthy = 0
        for i, shard_data in enumerate(downloaded):
            if shard_data:
                actual_hash = self.codec.shard_hash(shard_data)
                if actual_hash == to_check[i]["shard_hash"]:
                    shards_healthy += 1

        shards_checked = len(to_check)
        health_score = shards_healthy / shards_checked if shards_checked > 0 else 0.0
        verified = health_score == 1.0
        degraded = health_score < 0.8

        # Update manifest health_score
        await self.manifests.update_health(db, file_id, health_score, datetime.now(timezone.utc))

        return {
            "verified": verified,
            "shards_checked": shards_checked,
            "shards_healthy": shards_healthy,
            "degraded": degraded
        }
