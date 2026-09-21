"""VIT Network Node models — tracks agent/validator node activity and network growth."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime, Float, Index, Integer, JSON, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class NodeActivity(Base):
    """One contribution record emitted by each agent/node per successful cycle."""
    __tablename__ = "node_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    # Node identity
    node_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(20), nullable=False)  # agent | validator | oracle

    # Contribution details
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # cycle | oracle_submit | validation | insight
    contribution_score: Mapped[float] = mapped_column(Float, default=1.0)
    activity_meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("idx_node_activity_node_id", "node_id"),
        Index("idx_node_activity_type", "activity_type"),
        Index("idx_node_activity_recorded_at", "recorded_at"),
    )


class NetworkSnapshot(Base):
    """Hourly snapshot of network-wide health and growth metrics."""
    __tablename__ = "network_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)

    total_nodes: Mapped[int] = mapped_column(Integer, default=0)
    active_nodes: Mapped[int] = mapped_column(Integer, default=0)
    total_contributions: Mapped[int] = mapped_column(Integer, default=0)
    oracle_submissions: Mapped[int] = mapped_column(Integer, default=0)
    validator_predictions: Mapped[int] = mapped_column(Integer, default=0)
    network_health_score: Mapped[float] = mapped_column(Float, default=0.0)
    growth_rate_24h: Mapped[float] = mapped_column(Float, default=0.0)

    top_nodes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("idx_network_snapshot_at", "snapshot_at"),
    )
