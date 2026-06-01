"""app/services/insight_store.py — Native Insight Storage.
Replaces external AI provider insights with native intelligence storage.
"""
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.modules.ai.models import AIInsight

CACHE_TTL_HOURS = 12
PROVIDERS = ("native",)
PROVIDER_LABELS = {"native": "Native VIT Intelligence"}

def _as_probability(value: Any, fallback: Optional[float] = None) -> Optional[float]:
    if value is None: return fallback
    try:
        numeric = float(value)
        if numeric > 1: numeric /= 100
        return max(0.0, min(1.0, numeric))
    except Exception: return fallback

def normalize_provider_insight(source: str, payload: Dict[str, Any], defaults: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    defaults = defaults or {}
    return {
        "available": True,
        "source": "native",
        "label": PROVIDER_LABELS["native"],
        "home_prob": _as_probability(payload.get("home_prob"), defaults.get("home_prob", 0.34)),
        "draw_prob": _as_probability(payload.get("draw_prob"), defaults.get("draw_prob", 0.33)),
        "away_prob": _as_probability(payload.get("away_prob"), defaults.get("away_prob", 0.33)),
        "confidence": _as_probability(payload.get("confidence"), 0.75),
        "summary": payload.get("summary") or "Native ensemble analysis complete.",
        "key_factors": payload.get("key_factors") or ["Native Signals"],
        "risk_level": payload.get("risk_level", "MEDIUM"),
        "error": None,
        "from_cache": True,
    }

async def save_match_insights(match_id: int, raw: Dict[str, Any]) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(AIInsight).where(AIInsight.match_id == match_id))
        existing = q.scalar_one_or_none()
        if existing:
            existing.insights = {"native": raw}
            existing.uploaded_at = datetime.now(timezone.utc)
        else:
            db.add(AIInsight(match_id=match_id, insights={"native": raw}, uploaded_at=datetime.now(timezone.utc)))
        await db.commit()
    return {"match_id": match_id, "sources": ["native"]}

async def load_match_insights(match_id: int, defaults: Optional[Dict[str, float]] = None) -> Dict[str, Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(AIInsight).where(AIInsight.match_id == match_id))
        row = q.scalar_one_or_none()
    if not row or (row.uploaded_at and datetime.now(timezone.utc) - row.uploaded_at.replace(tzinfo=timezone.utc) > timedelta(hours=CACHE_TTL_HOURS)):
        return {}
    return {"native": normalize_provider_insight("native", row.insights.get("native", {}), defaults)}
