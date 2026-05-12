"""app/api/routes/ai_upload.py — Analyst AI Upload API.

Wraps the existing /admin/ai-sources endpoint with a friendlier
/api/ai-upload prefix and public listing endpoints.

POST /api/ai-upload/submit    — Submit AI analysis for a match
GET  /api/ai-upload/list      — List recent AI uploads
GET  /api/ai-upload/sources   — List available AI sources
GET  /api/ai-upload/match/{match_id} — All AI uploads for a match
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import AIPrediction, Match, User
from app.api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-upload", tags=["ai-upload"])

ALLOWED_SOURCES = {
    "chatgpt", "gemini", "claude", "grok",
    "deepseek", "perplexity", "mistral", "manual", "server",
}


class AIUploadPayload(BaseModel):
    match_id:    int            = Field(..., gt=0)
    source:      str            = Field(..., min_length=2, max_length=50)
    home_prob:   float          = Field(..., ge=0.0, le=1.0)
    draw_prob:   float          = Field(..., ge=0.0, le=1.0)
    away_prob:   float          = Field(..., ge=0.0, le=1.0)
    confidence:  float          = Field(0.70, ge=0.0, le=1.0)
    reason:      Optional[str]  = Field(None, max_length=1000)
    raw_content: Optional[str]  = Field(None, max_length=20000)

    @validator("source")
    def _clean_source(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ALLOWED_SOURCES:
            raise ValueError(f"source must be one of: {sorted(ALLOWED_SOURCES)}")
        return v

    @validator("away_prob")
    def _check_sum(cls, v, values):
        h = values.get("home_prob", 0)
        d = values.get("draw_prob", 0)
        total = (h or 0) + (d or 0) + (v or 0)
        if total <= 0:
            raise ValueError("Probabilities must sum to a positive value")
        return v


def _normalise(h: float, d: float, a: float):
    s = h + d + a
    if s <= 0:
        return 0.45, 0.27, 0.28
    return round(h / s, 4), round(d / s, 4), round(a / s, 4)


@router.post("/submit")
async def submit_ai_upload(
    payload: AIUploadPayload,
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """Submit an AI model's probability estimates for a specific match."""
    # Verify match exists
    match = (await db.execute(
        select(Match).where(Match.id == payload.match_id)
    )).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {payload.match_id} not found")

    hp, dp, ap = _normalise(payload.home_prob, payload.draw_prob, payload.away_prob)

    entry = AIPrediction(
        match_id   = payload.match_id,
        source     = payload.source,
        home_prob  = hp,
        draw_prob  = dp,
        away_prob  = ap,
        confidence = payload.confidence,
        reason     = payload.reason,
        raw_content = payload.raw_content,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    # Update AI performance tracker
    try:
        from app.services.ai_ingestion import AIIngestionService
        svc = AIIngestionService(db)
        await svc.ingest_prediction(
            match_id=payload.match_id,
            source=payload.source,
            home_prob=hp,
            draw_prob=dp,
            away_prob=ap,
            confidence=payload.confidence,
        )
    except Exception as exc:
        logger.debug("[ai-upload] performance upsert failed: %s", exc)

    return {
        "id":        entry.id,
        "match_id":  payload.match_id,
        "source":    payload.source,
        "home_prob": hp,
        "draw_prob": dp,
        "away_prob": ap,
        "confidence": payload.confidence,
        "created_at": entry.timestamp.isoformat() if entry.timestamp else None,
        "message": "AI prediction recorded successfully",
    }


@router.get("/list")
async def list_ai_uploads(
    source: Optional[str] = Query(None),
    limit:  int           = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """List recent AI uploads, optionally filtered by source."""
    q = (
        select(AIPrediction, Match)
        .join(Match, Match.id == AIPrediction.match_id)
        .order_by(desc(AIPrediction.timestamp))
        .limit(limit)
    )
    if source:
        q = q.where(AIPrediction.source == source.lower().strip())

    rows = list((await db.execute(q)).all())
    return {
        "count": len(rows),
        "uploads": [
            {
                "id":        p.id,
                "match_id":  p.match_id,
                "match":     f"{m.home_team} vs {m.away_team}",
                "source":    p.source,
                "home_prob": float(p.home_prob or 0),
                "draw_prob": float(p.draw_prob or 0),
                "away_prob": float(p.away_prob or 0),
                "confidence": float(p.confidence or 0),
                "created_at": p.timestamp.isoformat() if p.timestamp else None,
            }
            for p, m in rows
        ],
    }


@router.get("/sources")
async def list_ai_sources(
    _user=Depends(verify_api_key),
):
    """List all valid AI source identifiers."""
    return {
        "sources": sorted(ALLOWED_SOURCES),
        "count":   len(ALLOWED_SOURCES),
    }


@router.get("/match/{match_id}")
async def ai_uploads_for_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(verify_api_key),
):
    """Return all AI uploads for a specific match."""
    match = (await db.execute(
        select(Match).where(Match.id == match_id)
    )).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")

    q = (
        select(AIPrediction)
        .where(AIPrediction.match_id == match_id)
        .order_by(desc(AIPrediction.timestamp))
    )
    rows = list((await db.execute(q)).scalars().all())

    # Compute consensus if multiple sources
    consensus = None
    if len(rows) >= 2:
        h = sum(float(r.home_prob or 0) for r in rows) / len(rows)
        d = sum(float(r.draw_prob or 0) for r in rows) / len(rows)
        a = sum(float(r.away_prob or 0) for r in rows) / len(rows)
        s = h + d + a
        if s > 0:
            consensus = {
                "home_prob": round(h / s, 4),
                "draw_prob": round(d / s, 4),
                "away_prob": round(a / s, 4),
                "source_count": len(rows),
            }

    return {
        "match_id":  match_id,
        "match":     f"{match.home_team} vs {match.away_team}",
        "league":    match.league,
        "count":     len(rows),
        "consensus": consensus,
        "uploads": [
            {
                "id":         r.id,
                "source":     r.source,
                "home_prob":  float(r.home_prob or 0),
                "draw_prob":  float(r.draw_prob or 0),
                "away_prob":  float(r.away_prob or 0),
                "confidence": float(r.confidence or 0),
                "reasoning":  r.reason,
                "created_at": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in rows
        ],
    }
