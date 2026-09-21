"""
app/modules/evidence/schemas.py — Pydantic response schemas for the Evidence Module.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MarketRequirementResultSchema(BaseModel):
    id: Optional[int] = None
    market_key: str
    requirements_met: bool
    reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceSnapshotSchema(BaseModel):
    id: Optional[int] = None
    match_id: int
    feature_completeness_pct: int = Field(ge=0, le=100)
    quality_score: int = Field(ge=0, le=100)
    provider_data: Dict[str, Any] = Field(default_factory=dict)
    missing_critical_inputs: List[Any] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    market_requirement_results: List[MarketRequirementResultSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EvidenceBlockSchema(BaseModel):
    """Canonical evidence block in prediction responses."""
    snapshot_id: Optional[int] = None
    quality_score: int = Field(ge=0, le=100)
    feature_completeness_pct: int = Field(ge=0, le=100)
    missing_critical_inputs: List[Any] = Field(default_factory=list)
    market_requirements: Dict[str, bool] = Field(default_factory=dict)
    reasons: Dict[str, Optional[str]] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
