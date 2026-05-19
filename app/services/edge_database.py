# app/services/edge_database.py
import logging
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.db.models import Edge

logger = logging.getLogger(__name__)


class EdgeDatabase:
    """
    Edge Database - Tracks profitable patterns and their decay over time.

    Edges are discovered patterns that consistently beat the market.
    They decay as bookmakers adjust.

    FIXED: Proper lifecycle management with ROI decay detection.
    """

    @staticmethod
    async def create_edge(
        db: AsyncSession,
        edge_id: str,
        description: str,
        league: Optional[str] = None,
        market: str = "1x2"
    ) -> Edge:
        """Create a new edge entry"""
        edge = Edge(
            edge_id=edge_id,
            description=description,
            league=league,
            market=market,
            roi=0.0,
            sample_size=0,
            confidence=0.0,
            status="active"
        )
        db.add(edge)
        await db.commit()
        await db.refresh(edge)
        logger.info(f"Created edge: {edge_id}")
        return edge

    @staticmethod
    async def update_edge_performance(
        db: AsyncSession,
        edge_id: str,
        new_roi: float,
        new_edge_value: float
    ) -> Optional[Edge]:
        """Update edge performance with new data point"""
        result = await db.execute(select(Edge).where(Edge.edge_id == edge_id))
        edge = result.scalar_one_or_none()

        if not edge:
            return None

        # Exponential moving average update
        alpha = 1.0 / (edge.sample_size + 1)
        edge.roi = edge.roi * (1 - alpha) + new_roi * alpha
        edge.avg_edge = edge.avg_edge * (1 - alpha) + new_edge_value * alpha
        edge.sample_size += 1

        # Update confidence based on sample size
        edge.confidence = min(0.95, edge.sample_size / 100)

        # Check for decay (ROI dropped significantly)
        if edge.sample_size > 20:
            if edge.roi < 0.01:
                edge.status = "declining"
                logger.warning(f"Edge {edge_id} is declining (ROI: {edge.roi:.4f})")
            elif edge.roi < 0.005:
                edge.status = "dead"
                logger.warning(f"Edge {edge_id} is dead (ROI: {edge.roi:.4f})")

        await db.commit()
        await db.refresh(edge)

        return edge

    @staticmethod
    async def get_active_edges(
        db: AsyncSession, 
        min_roi: float = 0.02,
        min_samples: int = 10
    ) -> List[Edge]:
        """Get all active edges with ROI above threshold and sufficient samples"""
        result = await db.execute(
            select(Edge)
            .where(Edge.status == "active")
            .where(Edge.roi >= min_roi)
            .where(Edge.sample_size >= min_samples)
            .order_by(Edge.roi.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_declining_edges(db: AsyncSession) -> List[Edge]:
        """Get edges that are declining"""
        result = await db.execute(
            select(Edge)
            .where(Edge.status == "declining")
            .order_by(Edge.roi)
        )
        return result.scalars().all()

    @staticmethod
    async def archive_dead_edges(db: AsyncSession) -> int:
        """Archive edges that have died"""
        from datetime import datetime, timezone

        result = await db.execute(
            select(Edge).where(Edge.status == "dead")
        )
        dead_edges = result.scalars().all()

        for edge in dead_edges:
            edge.status = "archived"
            edge.archived_at = datetime.now(timezone.utc)

        await db.commit()

        if dead_edges:
            logger.info(f"Archived {len(dead_edges)} dead edges")

        return len(dead_edges)

    @staticmethod
    async def get_edge_stats(db: AsyncSession) -> Dict:
        """Get edge database statistics"""
        total = await db.execute(select(func.count()).select_from(Edge))
        active = await db.execute(
            select(func.count()).select_from(Edge).where(Edge.status == "active")
        )
        declining = await db.execute(
            select(func.count()).select_from(Edge).where(Edge.status == "declining")
        )
        dead = await db.execute(
            select(func.count()).select_from(Edge).where(Edge.status == "dead")
        )
        avg_roi = await db.execute(
            select(func.avg(Edge.roi)).where(Edge.status == "active")
        )

        return {
            "total_edges": total.scalar() or 0,
            "active_edges": active.scalar() or 0,
            "declining_edges": declining.scalar() or 0,
            "dead_edges": dead.scalar() or 0,
            "avg_active_roi": float(avg_roi.scalar() or 0)
        }