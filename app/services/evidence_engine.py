"""
Data & Evidence Quality Engine for VIT Prediction Infrastructure.

Calculates evidence quality scores (0-100) from verified match data, feature completeness,
odds coverage/freshness, bookmaker agreement, and ensemble agreement.
Enforces per-market input requirements and strictly prevents fake/default odds from
being manufactured as evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.services.odds_provider import ReconciledMarketOdds, OddsFreshness

logger = logging.getLogger(__name__)


class PredictionClassification(str, Enum):
    STRONG = "STRONG"          # 85 - 100
    STANDARD = "STANDARD"      # 70 - 84
    LIMITED = "LIMITED"        # 55 - 69
    UNAVAILABLE = "UNAVAILABLE" # < 55


# Market input requirement definitions
MARKET_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "match_winner": {
        "required_inputs": ["verified_fixture", "team_statistics", "form"],
        "odds_required": False,  # match_winner can model stats alone if form/stats exist
        "min_evidence_score": 55.0,
    },
    "over_2_5": {
        "required_inputs": ["verified_fixture", "team_statistics", "scoring_features", "current_market_odds"],
        "odds_required": True,
        "min_evidence_score": 60.0,
    },
    "btts": {
        "required_inputs": ["verified_fixture", "team_statistics", "scoring_features", "current_market_odds"],
        "odds_required": True,
        "min_evidence_score": 60.0,
    },
}


@dataclass
class EvidenceScoreBreakdown:
    total_score: float
    classification: PredictionClassification
    is_sufficient: bool
    verified_fixture: float = 0.0        # Max 20
    team_statistics: float = 0.0         # Max 20
    recent_form: float = 0.0             # Max 15
    current_odds: float = 0.0            # Max 20
    bookmaker_agreement: float = 0.0     # Max 10
    h2h_context: float = 0.0             # Max 5
    model_agreement: float = 0.0         # Max 10
    checklist: Dict[str, bool] = field(default_factory=dict)
    missing_elements: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None


class EvidenceEngine:
    """
    Evaluates data quality and computes Evidence Score for upcoming predictions.
    """

    @staticmethod
    def evaluate(
        match_source: Optional[str],
        match_features: Dict[str, Any],
        reconciled_odds: Optional[ReconciledMarketOdds] = None,
        h2h_data: Optional[Dict[str, Any]] = None,
        recent_form_data: Optional[Dict[str, Any]] = None,
        model_agreement_pct: float = 0.0,
        market: str = "match_winner",
    ) -> EvidenceScoreBreakdown:
        """
        Evaluate match features, odds, and model metadata to produce an EvidenceScoreBreakdown.
        """
        missing = []
        checklist = {}

        # 1. Verified Fixture (Max 20)
        # Fixture must come from a verified provider source
        verified_sources = {"isports", "sportsdb", "footballdata", "football-data.org", "the_odds_api", "provider"}
        is_verified = bool(match_source and match_source.lower() in verified_sources)
        score_fixture = 20.0 if is_verified else 0.0
        checklist["verified_fixture"] = is_verified
        if not is_verified:
            missing.append("Verified provider fixture identity")

        # 2. Team Statistics / Feature Completeness (Max 20)
        completeness = float(match_features.get("feature_completeness", 0.0) or 0.0)
        score_stats = round(min(20.0, completeness * 20.0), 1)
        checklist["team_statistics"] = completeness >= 0.5
        if completeness < 0.5:
            missing.append("Comprehensive team statistics (rolling features)")

        # 3. Recent Form Data (Max 15)
        has_home_form = bool(recent_form_data and recent_form_data.get("home", {}).get("matches_played", 0) >= 3)
        has_away_form = bool(recent_form_data and recent_form_data.get("away", {}).get("matches_played", 0) >= 3)
        if has_home_form and has_away_form:
            score_form = 15.0
            checklist["recent_form"] = True
        elif has_home_form or has_away_form:
            score_form = 7.5
            checklist["recent_form"] = False
            missing.append("Full recent form history for both teams")
        else:
            score_form = 0.0
            checklist["recent_form"] = False
            missing.append("Recent match form data")

        # 4. Current Market Odds & Freshness (Max 20)
        score_odds = 0.0
        checklist["current_market_odds"] = False
        if reconciled_odds and reconciled_odds.consensus_odds:
            freshness = reconciled_odds.freshness
            if freshness == OddsFreshness.LIVE:
                score_odds = 20.0
            elif freshness == OddsFreshness.FRESH:
                score_odds = 18.0
            elif freshness == OddsFreshness.ACCEPTABLE:
                score_odds = 14.0
            elif freshness == OddsFreshness.STALE:
                score_odds = 8.0
            checklist["current_market_odds"] = freshness in (OddsFreshness.LIVE, OddsFreshness.FRESH, OddsFreshness.ACCEPTABLE)
            if freshness in (OddsFreshness.STALE, OddsFreshness.INVALID):
                missing.append(f"Fresh market odds (currently {freshness.value.lower()})")
        else:
            missing.append("Current market odds")

        # 5. Multiple Bookmaker Agreement (Max 10)
        score_bm = 0.0
        checklist["bookmaker_agreement"] = False
        if reconciled_odds and reconciled_odds.bookmaker_count > 0:
            bm_count = reconciled_odds.bookmaker_count
            if bm_count >= 5 and not reconciled_odds.has_anomaly:
                score_bm = 10.0
                checklist["bookmaker_agreement"] = True
            elif bm_count >= 2 and not reconciled_odds.has_anomaly:
                score_bm = 7.0
                checklist["bookmaker_agreement"] = True
            elif bm_count >= 1 and not reconciled_odds.has_anomaly:
                score_bm = 4.0
                checklist["bookmaker_agreement"] = False
            else:
                score_bm = 2.0  # Has anomaly or 0 bookmakers
                checklist["bookmaker_agreement"] = False
                if reconciled_odds.has_anomaly:
                    missing.append("Consistent bookmaker odds agreement (anomaly detected)")

        # 6. H2H / Contextual Data (Max 5)
        has_h2h = bool(h2h_data and h2h_data.get("matches_played", 0) >= 1)
        score_h2h = 5.0 if has_h2h else 0.0
        checklist["h2h_context"] = has_h2h

        # 7. Model Ensemble Agreement (Max 10)
        score_model = round(min(10.0, max(0.0, model_agreement_pct * 10.0)), 1)
        checklist["model_agreement"] = model_agreement_pct >= 0.60

        total_score = round(
            score_fixture + score_stats + score_form + score_odds + score_bm + score_h2h + score_model, 1
        )

        # Determine classification
        if total_score >= 85.0:
            classification = PredictionClassification.STRONG
        elif total_score >= 70.0:
            classification = PredictionClassification.STANDARD
        elif total_score >= 55.0:
            classification = PredictionClassification.LIMITED
        else:
            classification = PredictionClassification.UNAVAILABLE

        # Check market specific requirements
        reqs = MARKET_REQUIREMENTS.get(market.lower(), MARKET_REQUIREMENTS["match_winner"])
        min_required_score = reqs["min_evidence_score"]
        needs_odds = reqs["odds_required"]

        is_sufficient = total_score >= min_required_score
        rejection_reason = None

        if needs_odds and score_odds <= 0.0:
            is_sufficient = False
            classification = PredictionClassification.UNAVAILABLE
            rejection_reason = f"Market '{market}' strictly requires market odds which are unavailable"
        elif not is_sufficient:
            classification = PredictionClassification.UNAVAILABLE
            rejection_reason = f"Evidence score {total_score:.1f} is below minimum threshold {min_required_score:.1f}"

        return EvidenceScoreBreakdown(
            total_score=total_score,
            classification=classification,
            is_sufficient=is_sufficient,
            verified_fixture=score_fixture,
            team_statistics=score_stats,
            recent_form=score_form,
            current_odds=score_odds,
            bookmaker_agreement=score_bm,
            h2h_context=score_h2h,
            model_agreement=score_model,
            checklist=checklist,
            missing_elements=missing,
            rejection_reason=rejection_reason,
        )
