"""Evidence Module ORM Models — EvidenceSnapshot and MarketRequirementResult."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EvidenceSnapshot(Base):
    """Snapshot of evidence data and quality evaluations for a match prediction."""

    __tablename__ = "evidence_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feature_completeness_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_critical_inputs: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)

    market_requirement_results: Mapped[List[MarketRequirementResult]] = relationship(
        back_populates="evidence_snapshot", cascade="all, delete-orphan"
    )


class MarketRequirementResult(Base):
    """Evaluation result for market requirements on a given evidence snapshot."""

    __tablename__ = "market_requirement_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    market_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    requirements_met: Mapped[bool] = mapped_column(nullable=False, default=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow_naive)

    evidence_snapshot: Mapped[EvidenceSnapshot] = relationship(
        back_populates="market_requirement_results"
    )
