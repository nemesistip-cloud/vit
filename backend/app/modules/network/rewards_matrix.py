"""Rewards Matrix — calculates node rewards based on type and performance."""

from decimal import Decimal
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.errors import AppError
from app.modules.network.node_types import NODE_TYPES
from app.modules.network.models import NodeActivity

class RewardsMatrix:
    """Calculates VIT rewards for nodes per epoch."""

    async def calculate(
        self,
        db: AsyncSession,
        node_id: str,
        epoch_stats: Dict[str, Any]
    ) -> Decimal:
        """
        Calculate rewards for a node based on its type and performance.

        Args:
            db: Database session.
            node_id: Unique ID of the node.
            epoch_stats: Dict containing performance metrics, e.g., {'success_rate': 0.95}.

        Returns:
            Decimal: Total VIT reward for this epoch.
        """
        # 1. Determine node type from latest activity
        # Note: In a full implementation, we might have a dedicated Node table,
        # but here we use NodeActivity as per existing models.py.
        stmt = (
            select(NodeActivity.node_type)
            .where(NodeActivity.node_id == node_id)
            .order_by(NodeActivity.recorded_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        node_type = result.scalar_one_or_none()

        if not node_type:
            raise AppError(
                f"Node {node_id} not found in activity registry.",
                status_code=404,
                code="node_not_found"
            )

        if node_type not in NODE_TYPES:
            raise AppError(
                f"Invalid node type: {node_type}",
                status_code=400,
                code="invalid_node_type"
            )

        # 2. Get multiplier from registry
        multiplier = Decimal(str(NODE_TYPES[node_type]["reward_multiplier"]))

        # 3. Base Reward (could be fetched from PlatformConfig in a real scenario)
        # For now, we'll use a standard base reward.
        base_reward = Decimal("10.0")

        # 4. Performance Factor: 0.5–1.5 based on challenge success rate
        # success_rate expected to be between 0.0 and 1.0
        success_rate = float(epoch_stats.get("success_rate", 1.0))

        # Linear mapping: 0.0 -> 0.5, 1.0 -> 1.5
        performance_factor = Decimal(str(max(0.5, min(1.5, 0.5 + success_rate))))

        # 5. Final Calculation
        total_reward = base_reward * multiplier * performance_factor

        return total_reward.quantize(Decimal("1.00000000"))
