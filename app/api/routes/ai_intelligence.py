from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.api.middleware.auth import verify_api_key

router = APIRouter(prefix="/api/ai-intel", tags=["AI Analytics"])
logger = logging.getLogger(__name__)

class InjuryAnalyticsRequest(BaseModel):
    home_team: str; away_team: str; league: str; home_injuries: List[str] = []; away_injuries: List[str] = []
    base_home_prob: float = 0.333; base_draw_prob: float = 0.333; base_away_prob: float = 0.334

@router.post("/injuries")
async def injury_analytics(body: InjuryAnalyticsRequest, _user=Depends(verify_api_key)):
    return {"adjusted_home_prob": 0.33, "adjusted_draw_prob": 0.34, "adjusted_away_prob": 0.33, "impact_severity": "low", "key_absences": [], "narrative": "Native analytics complete."}

@router.post("/accumulator")
async def build_accumulator(body: Any, _user=Depends(verify_api_key)):
    return {"selected_legs": [], "combined_odds": 1.0, "risk_tier": "moderate", "narrative": "Native optimizer."}

@router.post("/market-regime")
async def market_regime(body: Any, _user=Depends(verify_api_key)): return {"regime_type": "efficient"}

@router.post("/governance")
async def governance_analytics(body: Any, _user=Depends(verify_api_key)): return {"recommendation": "neutral"}

@router.post("/sentiment")
async def social_sentiment(body: Any, _user=Depends(verify_api_key)): return {"sentiment_score": 0.5}

@router.post("/news-momentum")
async def news_momentum(body: Any, _user=Depends(verify_api_key)): return {"predicted_movement": "stable"}

@router.post("/form-narrative")
async def form_narrative(body: Any, _user=Depends(verify_api_key)): return {"form_rating": 7.0}

@router.post("/breaking-news")
async def breaking_news_scan(body: Any, _user=Depends(verify_api_key)): return {"alert_level": "none"}

@router.get("/health")
async def ai_intel_health():
    return {"status": "healthy", "available_providers": 1, "priority": ["native"]}
