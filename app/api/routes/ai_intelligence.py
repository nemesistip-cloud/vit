"""app/api/routes/ai_intelligence.py — Advanced AI intelligence endpoints.

Exposes OpenAI and Grok advanced analytics via the REST API:

OpenAI endpoints:
  POST /api/ai-intel/injuries          — injury/suspension impact analysis
  POST /api/ai-intel/accumulator       — AI accumulator builder
  POST /api/ai-intel/market-regime     — market regime detection
  POST /api/ai-intel/governance        — governance proposal analysis

Grok endpoints:
  POST /api/ai-intel/sentiment         — social sentiment scoring
  POST /api/ai-intel/news-momentum     — news-driven odds movement
  POST /api/ai-intel/form-narrative    — team form narrative
  POST /api/ai-intel/breaking-news     — pre-match breaking news scanner

System:
  GET  /api/ai-intel/health            — provider health check
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.api.middleware.auth import verify_api_key

router = APIRouter(prefix="/api/ai-intel", tags=["AI Intelligence"])
logger = logging.getLogger(__name__)


# ── Request / Response models ──────────────────────────────────────────────────

class InjuryAnalysisRequest(BaseModel):
    home_team: str
    away_team: str
    league: str
    home_injuries: List[str] = Field(default_factory=list)
    away_injuries: List[str] = Field(default_factory=list)
    base_home_prob: float = Field(0.333, ge=0, le=1)
    base_draw_prob: float = Field(0.333, ge=0, le=1)
    base_away_prob: float = Field(0.334, ge=0, le=1)


class AccumulatorRequest(BaseModel):
    candidates: List[Dict[str, Any]]
    target_odds: float = Field(5.0, ge=1.5, le=100.0)
    max_legs: int = Field(5, ge=2, le=10)
    min_confidence: float = Field(0.55, ge=0.30, le=0.95)


class MarketRegimeRequest(BaseModel):
    league: str
    recent_results: List[Dict[str, Any]] = Field(default_factory=list)
    odds_movements: List[Dict[str, Any]] = Field(default_factory=list)
    public_betting_percentages: Optional[Dict[str, float]] = None


class GovernanceRequest(BaseModel):
    proposal_id: str
    title: str
    description: str
    proposer: str
    current_votes: Optional[Dict[str, Any]] = None
    token_supply: Optional[float] = None


class SentimentRequest(BaseModel):
    home_team: str
    away_team: str
    league: str
    recent_headlines: List[str] = Field(default_factory=list)
    match_date: Optional[str] = None


class NewsMomentumRequest(BaseModel):
    home_team: str
    away_team: str
    league: str
    news_items: List[Dict[str, Any]]
    current_odds: Dict[str, float] = Field(default_factory=dict)


class FormNarrativeRequest(BaseModel):
    team: str
    league: str
    recent_results: List[Dict[str, Any]]
    opponent: Optional[str] = None


class BreakingNewsRequest(BaseModel):
    home_team: str
    away_team: str
    league: str
    hours_before_kickoff: float = Field(24.0, ge=0, le=168)
    news_feed: List[Dict[str, Any]] = Field(default_factory=list)


# ── OpenAI endpoints ───────────────────────────────────────────────────────────

@router.post("/injuries")
async def injury_analysis(
    body: InjuryAnalysisRequest,
    _user=Depends(verify_api_key),
):
    """
    Analyse how reported injuries and suspensions affect match probabilities.
    Returns adjusted 1X2 probabilities, impact severity, and key absences.
    """
    try:
        from app.services.openai_advanced import analyze_injuries
        result = await analyze_injuries(
            home_team=body.home_team,
            away_team=body.away_team,
            league=body.league,
            home_injuries=body.home_injuries,
            away_injuries=body.away_injuries,
            base_home_prob=body.base_home_prob,
            base_draw_prob=body.base_draw_prob,
            base_away_prob=body.base_away_prob,
        )
        return result
    except Exception as exc:
        logger.error("injury_analysis error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/accumulator")
async def build_accumulator(
    body: AccumulatorRequest,
    _user=Depends(verify_api_key),
):
    """
    Build an optimal accumulator from candidate predictions.
    Returns selected legs, combined odds, EV, risk tier, and narrative.
    """
    try:
        from app.services.openai_advanced import build_accumulator as _build
        result = await _build(
            candidates=body.candidates,
            target_odds=body.target_odds,
            max_legs=body.max_legs,
            min_confidence=body.min_confidence,
        )
        return result
    except Exception as exc:
        logger.error("accumulator_builder error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/market-regime")
async def market_regime(
    body: MarketRegimeRequest,
    _user=Depends(verify_api_key),
):
    """
    Classify the current betting market regime for a league.
    Returns regime type, efficiency score, sharp signals, and trading recommendation.
    """
    try:
        from app.services.openai_advanced import detect_market_regime
        result = await detect_market_regime(
            league=body.league,
            recent_results=body.recent_results,
            odds_movements=body.odds_movements,
            public_betting_percentages=body.public_betting_percentages,
        )
        return result
    except Exception as exc:
        logger.error("market_regime error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/governance")
async def governance_analysis(
    body: GovernanceRequest,
    _user=Depends(verify_api_key),
):
    """
    AI analysis of a DAO governance proposal.
    Returns recommendation, stakeholder impact, pros/cons, and vote guidance.
    """
    try:
        from app.services.openai_advanced import analyze_governance_proposal
        result = await analyze_governance_proposal(
            proposal_id=body.proposal_id,
            title=body.title,
            description=body.description,
            proposer=body.proposer,
            current_votes=body.current_votes,
            token_supply=body.token_supply,
        )
        return result
    except Exception as exc:
        logger.error("governance_analysis error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Grok endpoints ─────────────────────────────────────────────────────────────

@router.post("/sentiment")
async def social_sentiment(
    body: SentimentRequest,
    _user=Depends(verify_api_key),
):
    """
    Score social/X sentiment for a fixture using Grok's real-time knowledge.
    Returns sentiment scores, market lean, contrarian signals, and narrative.
    """
    try:
        from app.services.grok_advanced import score_social_sentiment
        result = await score_social_sentiment(
            home_team=body.home_team,
            away_team=body.away_team,
            league=body.league,
            recent_headlines=body.recent_headlines,
            match_date=body.match_date,
        )
        return result
    except Exception as exc:
        logger.error("social_sentiment error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/news-momentum")
async def news_momentum(
    body: NewsMomentumRequest,
    _user=Depends(verify_api_key),
):
    """
    Predict odds direction based on recent news items.
    Returns predicted odds movement, trading signal, and time sensitivity.
    """
    try:
        from app.services.grok_advanced import predict_news_momentum
        result = await predict_news_momentum(
            home_team=body.home_team,
            away_team=body.away_team,
            league=body.league,
            news_items=body.news_items,
            current_odds=body.current_odds,
        )
        return result
    except Exception as exc:
        logger.error("news_momentum error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/form-narrative")
async def form_narrative(
    body: FormNarrativeRequest,
    _user=Depends(verify_api_key),
):
    """
    Generate an AI form narrative for a team with recency-weighted analysis.
    Returns form rating, trajectory, strengths, weaknesses, and betting implication.
    """
    try:
        from app.services.grok_advanced import generate_form_narrative
        result = await generate_form_narrative(
            team=body.team,
            league=body.league,
            recent_results=body.recent_results,
            opponent=body.opponent,
        )
        return result
    except Exception as exc:
        logger.error("form_narrative error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/breaking-news")
async def breaking_news_scan(
    body: BreakingNewsRequest,
    _user=Depends(verify_api_key),
):
    """
    Scan pre-match news for material events that could affect the prediction.
    Returns alert level, material events, and recommended action.
    """
    try:
        from app.services.grok_advanced import scan_breaking_news
        result = await scan_breaking_news(
            home_team=body.home_team,
            away_team=body.away_team,
            league=body.league,
            hours_before_kickoff=body.hours_before_kickoff,
            news_feed=body.news_feed,
        )
        return result
    except Exception as exc:
        logger.error("breaking_news_scanner error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Health / Provider status ───────────────────────────────────────────────────

@router.get("/health")
async def ai_intel_health():
    """
    Returns provider availability and AI cascade health for the intelligence layer.
    No auth required — used by monitoring dashboards.
    """
    try:
        from app.services.ai_client import provider_status, get_provider_priority
        providers = await provider_status()
        priority = get_provider_priority()
        available_count = sum(1 for p in providers.values() if p.get("available", False))
        return {
            "status": "healthy" if available_count > 0 else "degraded",
            "available_providers": available_count,
            "priority": priority,
            "providers": providers,
            "endpoints": {
                "openai": ["injuries", "accumulator", "market-regime", "governance"],
                "grok": ["sentiment", "news-momentum", "form-narrative", "breaking-news"],
            },
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
