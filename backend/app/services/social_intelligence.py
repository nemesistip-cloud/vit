import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.social.models import (
    SocialSignal,
    SocialOpportunity,
    SocialCandidate,
    SocialPublicationRecord,
    CandidateState,
    PublicationStatus,
)
from app.services.social_adapters import adapter_registry

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    CandidateState.NEW.value: [CandidateState.REVIEW.value],
    CandidateState.REVIEW.value: [CandidateState.APPROVED.value, CandidateState.REJECTED.value],
    CandidateState.APPROVED.value: [CandidateState.READY_FOR_DISTRIBUTION.value],
    CandidateState.READY_FOR_DISTRIBUTION.value: [CandidateState.PUBLISHED.value],
    CandidateState.REJECTED.value: [],
    CandidateState.PUBLISHED.value: [],
}


class SocialIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def validate_transition(self, current_state: str, new_state: str) -> None:
        allowed = VALID_TRANSITIONS.get(current_state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Invalid state transition from '{current_state}' to '{new_state}'. Allowed: {allowed}"
            )

    async def ingest_signal(
        self,
        source: str,
        title: str,
        summary: Optional[str] = None,
        url: Optional[str] = None,
        topic: Optional[str] = None,
        entities: Optional[List[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        verification_status: str = "VERIFIED",
        deduplication_key: Optional[str] = None,
    ) -> SocialSignal:
        if not deduplication_key:
            deduplication_key = f"{source}:{title}"

        stmt = select(SocialSignal).where(SocialSignal.deduplication_key == deduplication_key)
        res = await self.db.execute(stmt)
        existing = res.scalars().first()
        if existing:
            return existing

        signal = SocialSignal(
            source=source,
            url=url,
            title=title,
            summary=summary,
            topic=topic,
            entities=entities or [],
            evidence=evidence or {},
            freshness_seconds=int(time.time()),
            confidence=confidence,
            verification_status=verification_status,
            deduplication_key=deduplication_key,
        )
        self.db.add(signal)
        await self.db.flush()
        return signal

    async def create_opportunity(
        self,
        signal_id: str,
        score_breakdown: Optional[Dict[str, float]] = None,
        reasoning: Optional[str] = None,
        confidence: float = 1.0,
        priority: str = "MEDIUM",
        risk_flags: Optional[List[str]] = None,
    ) -> SocialOpportunity:
        breakdown = score_breakdown or {"relevance": 0.8, "timeliness": 0.9, "credibility": 0.85}
        total_score = round(sum(breakdown.values()) / max(len(breakdown), 1), 2)

        opp = SocialOpportunity(
            signal_id=signal_id,
            score=total_score,
            score_breakdown=breakdown,
            reasoning=reasoning or "Computed based on signal relevance, timeliness, and credibility.",
            confidence=confidence,
            priority=priority,
            risk_flags=risk_flags or [],
        )
        self.db.add(opp)
        await self.db.flush()
        return opp

    async def generate_candidate(
        self,
        opportunity_id: str,
        generated_content: str,
        content_format: str = "TEXT",
        risk_flags: Optional[List[str]] = None,
        creator_id: Optional[str] = None,
    ) -> SocialCandidate:
        stmt = select(SocialOpportunity).where(SocialOpportunity.id == opportunity_id)
        res = await self.db.execute(stmt)
        opp = res.scalars().first()
        if not opp:
            raise ValueError(f"Opportunity {opportunity_id} not found")

        signal_stmt = select(SocialSignal).where(SocialSignal.id == opp.signal_id)
        sig_res = await self.db.execute(signal_stmt)
        signal = sig_res.scalars().first()

        provenance = {
            "signal_id": signal.id if signal else None,
            "signal_source": signal.source if signal else None,
            "signal_title": signal.title if signal else None,
            "evidence": signal.evidence if signal else {},
            "opportunity_id": opp.id,
            "score": opp.score,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        merged_risk_flags = list(set((opp.risk_flags or []) + (risk_flags or [])))

        candidate = SocialCandidate(
            opportunity_id=opportunity_id,
            generated_content=generated_content,
            content_format=content_format,
            provenance=provenance,
            risk_flags=merged_risk_flags,
            state=CandidateState.NEW.value,
            review_history=[],
            created_by=creator_id or "system",
        )
        self.db.add(candidate)
        await self.db.flush()
        return candidate

    async def transition_candidate_state(
        self,
        candidate_id: str,
        new_state: str,
        actor: str,
        note: Optional[str] = None,
    ) -> SocialCandidate:
        stmt = select(SocialCandidate).where(SocialCandidate.id == candidate_id)
        res = await self.db.execute(stmt)
        candidate = res.scalars().first()
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")

        self.validate_transition(candidate.state, new_state)

        old_state = candidate.state
        candidate.state = new_state
        candidate.reviewed_by = actor
        candidate.reviewed_at = datetime.now(timezone.utc)

        history_entry = {
            "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from_state": old_state,
            "to_state": new_state,
            "note": note,
        }
        history = list(candidate.review_history or [])
        history.append(history_entry)
        candidate.review_history = history

        await self.db.flush()
        return candidate

    async def get_candidate_by_id(self, candidate_id: str) -> Optional[SocialCandidate]:
        stmt = select(SocialCandidate).where(SocialCandidate.id == candidate_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def publish_candidate(
        self,
        candidate_id: str,
        platform: str,
        actor: str,
    ) -> SocialPublicationRecord:
        candidate = await self.get_candidate_by_id(candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} not found")

        # Idempotency check FIRST: check if already published
        stmt = select(SocialPublicationRecord).where(
            SocialPublicationRecord.candidate_id == candidate_id,
            SocialPublicationRecord.platform == platform,
        )
        res = await self.db.execute(stmt)
        existing_record = res.scalars().first()

        if existing_record and existing_record.status == PublicationStatus.SUCCESS.value:
            raise ValueError(f"Candidate {candidate_id} is already published to {platform}")

        if candidate.state not in (CandidateState.READY_FOR_DISTRIBUTION.value, CandidateState.APPROVED.value, CandidateState.PUBLISHED.value):
            raise ValueError(f"Candidate state '{candidate.state}' is not ready for publication")

        adapter = adapter_registry.get_adapter(platform)
        valid, err = adapter.validate_content(candidate)
        if not valid:
            raise ValueError(f"Pre-publication validation failed for {platform}: {err}")

        record = existing_record or SocialPublicationRecord(
            candidate_id=candidate_id,
            platform=platform,
            status=PublicationStatus.PENDING.value,
        )
        if not existing_record:
            self.db.add(record)

        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError(f"Duplicate publication attempt detected for candidate {candidate_id} on {platform}")

        try:
            pub_result = await adapter.publish(candidate)
            record.status = PublicationStatus.SUCCESS.value
            record.external_ref = pub_result.get("external_ref")
            record.url = pub_result.get("url")
            record.published_at = datetime.now(timezone.utc)

            if candidate.state == CandidateState.READY_FOR_DISTRIBUTION.value:
                candidate.state = CandidateState.PUBLISHED.value
                history_entry = {
                    "actor": actor,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "from_state": CandidateState.READY_FOR_DISTRIBUTION.value,
                    "to_state": CandidateState.PUBLISHED.value,
                    "note": f"Published to {platform}",
                }
                history = list(candidate.review_history or [])
                history.append(history_entry)
                candidate.review_history = history

            await self.db.flush()
            return record
        except Exception as exc:
            record.status = PublicationStatus.FAILED.value
            record.error_message = str(exc)
            await self.db.flush()
            raise exc
