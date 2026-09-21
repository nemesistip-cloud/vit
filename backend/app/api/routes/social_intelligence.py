import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.social.models import SocialSignal, SocialOpportunity, SocialCandidate, SocialPublicationRecord, CandidateState
from app.services.social_intelligence import SocialIntelligenceService
from app.services.social_adapters import adapter_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/social-intelligence", tags=["Social Intelligence"])


class SignalIngestRequest(BaseModel):
    source: str
    title: str
    summary: Optional[str] = None
    url: Optional[str] = None
    topic: Optional[str] = None
    entities: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    verification_status: str = "VERIFIED"
    deduplication_key: Optional[str] = None


class OpportunityCreateRequest(BaseModel):
    score_breakdown: Optional[Dict[str, float]] = None
    reasoning: Optional[str] = None
    confidence: float = 1.0
    priority: str = "MEDIUM"
    risk_flags: List[str] = Field(default_factory=list)


class CandidateGenerateRequest(BaseModel):
    generated_content: str = Field(..., min_length=1, max_length=5000)
    content_format: str = "TEXT"
    risk_flags: List[str] = Field(default_factory=list)


class CandidateTransitionRequest(BaseModel):
    new_state: str
    note: Optional[str] = None


class PublishCandidateRequest(BaseModel):
    platform: str


@router.post("/signals", summary="Ingest information signal")
async def ingest_signal(
    body: SignalIngestRequest,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    svc = SocialIntelligenceService(db)
    sig = await svc.ingest_signal(
        source=body.source,
        title=body.title,
        summary=body.summary,
        url=body.url,
        topic=body.topic,
        entities=body.entities,
        evidence=body.evidence,
        confidence=body.confidence,
        verification_status=body.verification_status,
        deduplication_key=body.deduplication_key,
    )
    return {
        "id": sig.id,
        "source": sig.source,
        "title": sig.title,
        "deduplication_key": sig.deduplication_key,
        "verification_status": sig.verification_status,
        "created_at": sig.created_at.isoformat() if sig.created_at else None,
    }


@router.get("/signals", summary="List ingested signals")
async def list_signals(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    stmt = select(SocialSignal).order_by(SocialSignal.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    signals = res.scalars().all()
    return [
        {
            "id": s.id,
            "source": s.source,
            "title": s.title,
            "topic": s.topic,
            "confidence": s.confidence,
            "verification_status": s.verification_status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in signals
    ]


@router.post("/signals/{signal_id}/evaluate", summary="Evaluate signal to create opportunity")
async def evaluate_signal(
    signal_id: str,
    body: OpportunityCreateRequest,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    svc = SocialIntelligenceService(db)
    opp = await svc.create_opportunity(
        signal_id=signal_id,
        score_breakdown=body.score_breakdown,
        reasoning=body.reasoning,
        confidence=body.confidence,
        priority=body.priority,
        risk_flags=body.risk_flags,
    )
    return {
        "id": opp.id,
        "signal_id": opp.signal_id,
        "score": opp.score,
        "score_breakdown": opp.score_breakdown,
        "priority": opp.priority,
        "risk_flags": opp.risk_flags,
    }


@router.post("/opportunities/{opportunity_id}/candidates", summary="Generate candidate content from opportunity")
async def generate_candidate(
    opportunity_id: str,
    body: CandidateGenerateRequest,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    svc = SocialIntelligenceService(db)
    try:
        cand = await svc.generate_candidate(
            opportunity_id=opportunity_id,
            generated_content=body.generated_content,
            content_format=body.content_format,
            risk_flags=body.risk_flags,
            creator_id=str(me.id),
        )
        return {
            "id": cand.id,
            "opportunity_id": cand.opportunity_id,
            "generated_content": cand.generated_content,
            "provenance": cand.provenance,
            "state": cand.state,
            "risk_flags": cand.risk_flags,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/candidates", summary="Get editorial queue candidates")
async def get_editorial_queue(
    state: Optional[str] = Query(None, description="Filter queue by state: NEW, REVIEW, APPROVED, REJECTED, READY_FOR_DISTRIBUTION, PUBLISHED"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    stmt = select(SocialCandidate)
    if state:
        stmt = stmt.where(SocialCandidate.state == state.upper())
    stmt = stmt.order_by(SocialCandidate.created_at.desc()).limit(limit)

    res = await db.execute(stmt)
    candidates = res.scalars().all()
    return [
        {
            "id": c.id,
            "opportunity_id": c.opportunity_id,
            "generated_content": c.generated_content,
            "content_format": c.content_format,
            "state": c.state,
            "risk_flags": c.risk_flags,
            "reviewed_by": c.reviewed_by,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in candidates
    ]


@router.get("/candidates/{candidate_id}", summary="Get candidate detail with full provenance")
async def get_candidate_detail(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    svc = SocialIntelligenceService(db)
    cand = await svc.get_candidate_by_id(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    stmt = select(SocialPublicationRecord).where(SocialPublicationRecord.candidate_id == candidate_id)
    res = await db.execute(stmt)
    records = res.scalars().all()

    return {
        "id": cand.id,
        "opportunity_id": cand.opportunity_id,
        "generated_content": cand.generated_content,
        "content_format": cand.content_format,
        "provenance": cand.provenance,
        "risk_flags": cand.risk_flags,
        "state": cand.state,
        "review_history": cand.review_history,
        "created_by": cand.created_by,
        "reviewed_by": cand.reviewed_by,
        "reviewed_at": cand.reviewed_at.isoformat() if cand.reviewed_at else None,
        "publications": [
            {
                "id": r.id,
                "platform": r.platform,
                "status": r.status,
                "external_ref": r.external_ref,
                "url": r.url,
                "error_message": r.error_message,
                "published_at": r.published_at.isoformat() if r.published_at else None,
            }
            for r in records
        ],
    }


@router.post("/candidates/{candidate_id}/transition", summary="Transition candidate state in editorial workflow")
async def transition_candidate(
    candidate_id: str,
    body: CandidateTransitionRequest,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    svc = SocialIntelligenceService(db)
    try:
        cand = await svc.transition_candidate_state(
            candidate_id=candidate_id,
            new_state=body.new_state.upper(),
            actor=me.email or str(me.id),
            note=body.note,
        )
        return {
            "id": cand.id,
            "state": cand.state,
            "reviewed_by": cand.reviewed_by,
            "reviewed_at": cand.reviewed_at.isoformat() if cand.reviewed_at else None,
            "review_history": cand.review_history,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/candidates/{candidate_id}/publish", summary="Publish candidate to target social platform")
async def publish_candidate(
    candidate_id: str,
    body: PublishCandidateRequest,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    svc = SocialIntelligenceService(db)
    try:
        record = await svc.publish_candidate(
            candidate_id=candidate_id,
            platform=body.platform,
            actor=me.email or str(me.id),
        )
        return {
            "id": record.id,
            "candidate_id": record.candidate_id,
            "platform": record.platform,
            "status": record.status,
            "external_ref": record.external_ref,
            "url": record.url,
            "published_at": record.published_at.isoformat() if record.published_at else None,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/adapters", summary="List registered distribution adapters and support status")
async def list_adapters(me: User = Depends(get_current_user)):
    res = {}
    for name, adapter in adapter_registry.adapters.items():
        res[name] = {
            "platform": name,
            "status": adapter.get_status().value,
        }
    return res
