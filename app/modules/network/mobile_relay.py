"""Mobile Relay Coordination — selects and tasks active mobile nodes."""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.network.models import NodeActivity

logger = logging.getLogger(__name__)

class MobileRelayCoordinator:
    """Orchestrates bandwidth relay tasks across active Android nodes."""

    async def get_available_relays(self, db: AsyncSession, limit: int = 10):
        """
        Returns a list of node_ids that are currently 'available' for relay.
        Availability criteria:
          - Node type is 'android'
          - Heartbeat in last 10 minutes
          - is_charging = True (from latest heartbeat)
          - is_on_wifi = True (from latest heartbeat)
        """
        since_10m = datetime.now(timezone.utc) - timedelta(minutes=10)

        # Subquery for latest heartbeat/activity per android node
        subq = (
            select(
                NodeActivity.node_id,
                func.max(NodeActivity.recorded_at).label("latest_ts")
            )
            .where(
                NodeActivity.node_type == "android",
                NodeActivity.recorded_at >= since_10m
            )
            .group_by(NodeActivity.node_id)
            .subquery()
        )

        # Join to filter by metadata
        stmt = (
            select(NodeActivity)
            .join(subq, (NodeActivity.node_id == subq.c.node_id) & (NodeActivity.recorded_at == subq.c.latest_ts))
        )

        res = await db.execute(stmt)
        active_nodes = res.scalars().all()

        available_ids = []
        for node in active_nodes:
            meta = node.activity_meta or {}
            # We check both the original constraints and current status
            # Registration stores constraints, heartbeats store status.
            # Here we primarily care about the current status from heartbeat.
            is_charging = meta.get("charge_status") == "charging"
            is_on_wifi = meta.get("wifi_status") == "connected"

            if is_charging and is_on_wifi:
                available_ids.append(node.node_id)

            if len(available_ids) >= limit:
                break

        return available_ids

    async def assign_relay_task(self, db: AsyncSession, target_node_id: str, data_size_mb: int):
        """
        Logs a task assignment for a mobile relay.
        Future feature: This would trigger a push notification or WebSocket message.
        """
        # Record task assignment
        task_activity = NodeActivity(
            node_id=target_node_id,
            node_name="RelayTask",
            node_type="android",
            activity_type="relay_task_assigned",
            contribution_score=0.0,
            activity_meta={
                "task_size_mb": data_size_mb,
                "assigned_at": datetime.now(timezone.utc).isoformat()
            }
        )
        db.add(task_activity)
        # Note: commit handled by orchestration loop

        logger.info(f"Assigned {data_size_mb}MB relay task to node {target_node_id}")
