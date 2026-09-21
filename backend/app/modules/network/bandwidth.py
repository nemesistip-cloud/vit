"""Bandwidth Tracker — records and aggregates data relayed by mobile/relay nodes."""

import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.network.models import NodeActivity

logger = logging.getLogger(__name__)

class BandwidthTracker:
    """Records bandwidth contributed by relay nodes in MB per epoch."""

    # Reward rate (future feature)
    REWARD_RATE_VIT_PER_MB = 0.0001

    async def record_relay(self, db: AsyncSession, node_id: str, bytes_relayed: int, epoch: int):
        """
        Persists bandwidth contribution for a node in a specific epoch.
        Unit: bytes are converted to MB for the record.
        """
        mb_relayed = bytes_relayed / (1024 * 1024)

        # Record as a NodeActivity entry
        activity = NodeActivity(
            node_id=node_id,
            node_name=f"Relay_{node_id[:8]}",
            node_type="relay",
            activity_type="bandwidth_relay",
            contribution_score=float(mb_relayed), # Use MB as contribution score for easy aggregation
            activity_meta={
                "epoch": epoch,
                "bytes_relayed": bytes_relayed,
                "mb_relayed": mb_relayed
            }
        )
        db.add(activity)
        # Note: Caller handles commit for batching/performance

        logger.debug(f"Recorded {mb_relayed:.2f} MB relay for node {node_id} in epoch {epoch}")

    async def get_epoch_contribution(self, db: AsyncSession, node_id: str, epoch: int) -> int:
        """
        Aggregates total bandwidth contributed (in MB) by a node in a specific epoch.
        """
        # Search NodeActivity for bandwidth_relay records in this epoch
        # Using contribution_score as the MB value for efficiency
        stmt = (
            select(func.sum(NodeActivity.contribution_score))
            .where(
                NodeActivity.node_id == node_id,
                NodeActivity.activity_type == "bandwidth_relay",
                NodeActivity.activity_meta["epoch"].as_integer() == epoch
            )
        )
        res = await db.execute(stmt)
        total_mb = res.scalar() or 0
        return int(total_mb)

    async def get_daily_usage_mb(self, db: AsyncSession, node_id: str) -> float:
        """
        Returns total MB relayed by a node in the last 24 hours.
        Used to enforce caps.
        """
        from datetime import datetime, timedelta, timezone
        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

        stmt = (
            select(func.sum(NodeActivity.contribution_score))
            .where(
                NodeActivity.node_id == node_id,
                NodeActivity.activity_type == "bandwidth_relay",
                NodeActivity.recorded_at >= since_24h
            )
        )
        res = await db.execute(stmt)
        total_mb = res.scalar() or 0.0
        return float(total_mb)
