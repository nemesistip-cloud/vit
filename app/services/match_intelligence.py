from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationStatus(str, Enum):
    VALID = "valid"
    PARTIAL = "partial"
    INVALID = "invalid"


@dataclass
class MatchIntelligenceProfile:
    """Structured, truth-first snapshot for a prediction decision."""

    fixture_id: str
    home_team: str
    away_team: str
    competition: str = ""
    season: str = ""
    feature_completeness: float = 0.0
    data_quality_score: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.PARTIAL
    missing_data_reasons: List[str] = field(default_factory=list)
    conflicting_reasons: List[str] = field(default_factory=list)
    freshness_status: str = "unknown"
    odds_source: str = "unknown"
    history_samples: int = 0
    model_ready: bool = False
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_missing(self, reason: str) -> None:
        if reason and reason not in self.missing_data_reasons:
            self.missing_data_reasons.append(reason)
        self._refresh_status()

    def mark_conflict(self, reason: str) -> None:
        if reason and reason not in self.conflicting_reasons:
            self.conflicting_reasons.append(reason)
        self._refresh_status()

    def set_validation(self, status: ValidationStatus) -> None:
        self.validation_status = status

    def _refresh_status(self) -> None:
        if self.data_quality_score >= 70.0 and self.feature_completeness >= 0.7:
            if self.validation_status == ValidationStatus.INVALID:
                self.validation_status = ValidationStatus.PARTIAL
            else:
                self.validation_status = ValidationStatus.VALID
        elif self.missing_data_reasons or self.conflicting_reasons:
            if self.data_quality_score >= 55.0 and self.feature_completeness >= 0.55:
                self.validation_status = ValidationStatus.PARTIAL
            else:
                self.validation_status = ValidationStatus.INVALID
        elif self.data_quality_score >= 70.0 and self.feature_completeness >= 0.7:
            self.validation_status = ValidationStatus.VALID
        else:
            self.validation_status = ValidationStatus.PARTIAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "competition": self.competition,
            "season": self.season,
            "feature_completeness": self.feature_completeness,
            "data_quality_score": self.data_quality_score,
            "validation_status": self.validation_status.value,
            "missing_data_reasons": list(self.missing_data_reasons),
            "conflicting_reasons": list(self.conflicting_reasons),
            "freshness_status": self.freshness_status,
            "odds_source": self.odds_source,
            "history_samples": self.history_samples,
            "model_ready": self.model_ready,
            "generated_at": self.generated_at.isoformat(),
        }


@dataclass
class PredictionReadinessGate:
    """Fail-closed readiness gate used before emitting a prediction."""

    min_feature_completeness: float = 0.8
    min_evidence_score: float = 55.0
    min_history_samples: int = 3

    def evaluate(
        self,
        *,
        feature_completeness: float,
        evidence_score: float,
        odds_available: bool,
        historical_sample_size: int,
        data_freshness_ok: bool,
        model_ready: bool,
    ) -> Dict[str, Any]:
        reasons: List[str] = []

        if feature_completeness < self.min_feature_completeness:
            reasons.append(
                f"feature completeness {feature_completeness:.2f} is below minimum {self.min_feature_completeness:.2f}"
            )
        if evidence_score < self.min_evidence_score:
            reasons.append(
                f"evidence score {evidence_score:.1f} is below minimum threshold {self.min_evidence_score:.1f}"
            )
        if not odds_available:
            reasons.append("current market odds are unavailable")
        if historical_sample_size < self.min_history_samples:
            reasons.append(
                f"insufficient historical sample size {historical_sample_size} below minimum {self.min_history_samples}"
            )
        if not data_freshness_ok:
            reasons.append("data freshness check failed")
        if not model_ready:
            reasons.append("model is not ready")

        ready = not reasons
        return {
            "ready": ready,
            "prediction_status": "ready" if ready else "unavailable",
            "reasons": reasons,
        }