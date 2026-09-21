import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.modules.storage_verification.models import TachyonManifest

logger = logging.getLogger(__name__)

class ManifestManager:
    async def create(self, db: AsyncSession,
                      file_id: str,
                      filename: str,
                      original_size: int,
                      sha256: str,
                      shard_locations: List[dict],
                      owner_user_id: int = None) -> TachyonManifest:
        """
        Create and persist a TachyonManifest.
        shard_locations: [{shard_index, provider_id, file_id, shard_hash, size_bytes}]
        """
        # Removed begin_nested() to avoid savepoint issues
        # In Session 4.2 spec, we need health_score, status, etc.
        # We store them in provider_mapping to respect model constraints.
        provider_mapping = {
            "shards": shard_locations,
            "_metadata": {
                "sha256": sha256,
                "health_score": 1.0,
                "status": "active",
                "last_verified_at": None
            }
        }

        # For compatibility with existing TachyonManifest (v5.5.0 router.py)
        fragment_names = [s["file_id"] for s in shard_locations]

        manifest = TachyonManifest(
            file_id=file_id,
            filename=filename,
            size_bytes=original_size,
            fragment_names=fragment_names,
            provider_mapping=provider_mapping,
            owner_user_id=owner_user_id,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.add(manifest)
        await db.flush()
        return manifest

    async def get(self, db: AsyncSession,
                   file_id: str) -> Optional[TachyonManifest]:
        stmt = select(TachyonManifest).where(TachyonManifest.file_id == file_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_deleted(self, db: AsyncSession, file_id: str):
        manifest = await self.get(db, file_id)
        if manifest:
            if "_metadata" not in manifest.provider_mapping:
                manifest.provider_mapping["_metadata"] = {}
            manifest.provider_mapping["_metadata"]["status"] = "deleted"
            flag_modified(manifest, "provider_mapping")
            await db.flush()

    async def get_degraded(self, db: AsyncSession,
                            limit: int = 50) -> List[TachyonManifest]:
        """
        Returns manifests where health_score < 0.8 and status is active.
        """
        # Using JSON extraction for filtering
        stmt = select(TachyonManifest).where(
            TachyonManifest.provider_mapping["_metadata"]["status"].as_string() == "active",
            TachyonManifest.provider_mapping["_metadata"]["health_score"].as_float() < 0.8
        ).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_health(self, db: AsyncSession,
                             file_id: str,
                             health_score: float,
                             last_verified_at: datetime):
        manifest = await self.get(db, file_id)
        if manifest:
            if "_metadata" not in manifest.provider_mapping:
                manifest.provider_mapping["_metadata"] = {}

            manifest.provider_mapping["_metadata"]["health_score"] = health_score
            manifest.provider_mapping["_metadata"]["last_verified_at"] = last_verified_at.isoformat()
            flag_modified(manifest, "provider_mapping")
            await db.flush()
