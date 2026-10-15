"""
Result Verification Service — Wave 2 Prediction Intelligence Infrastructure.

Handles canonical result ingestion, provider score/status normalization,
idempotent observation versioning, independent cross-provider verification,
correction detection, and auditable evidence preservation.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Match
from app.modules.sports.models import ResultObservation, ResultVerification, MarketMapping

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_status(raw_status: str, sport: str = "football") -> str:
    """
    Normalize status strings across external providers.
    Football statuses: full_time, extra_time, penalty, in_progress, scheduled, postponed, abandoned, cancelled, unknown.
    """
    st = (raw_status or "").strip().lower().replace("-", "_").replace(" ", "_")

    if st in ("finished", "ft", "full_time", "fulltime", "completed", "final"):
        return "full_time"
    if st in ("aet", "extra_time", "extratime"):
        return "extra_time"
    if st in ("pen", "penalties", "penalty"):
        return "penalty"
    if st in ("in_play", "live", "playing", "halftime", "ht", "in_progress", "1h", "2h"):
        return "in_progress"
    if st in ("scheduled", "timed", "ns", "not_started", "fixture"):
        return "scheduled"
    if st in ("postponed", "pst", "postp"):
        return "postponed"
    if st in ("abandoned", "abn", "abnd"):
        return "abandoned"
    if st in ("cancelled", "canceled", "canc"):
        return "cancelled"

    return "unknown"


def compute_content_hash(
    provider_name: str,
    provider_event_id: Optional[str],
    home_goals: Optional[int],
    away_goals: Optional[int],
    status: str,
    raw_payload: Optional[Dict[str, Any]] = None
) -> str:
    """Generate SHA256 content hash for result observation state."""
    payload_str = json.dumps(raw_payload, sort_keys=True) if raw_payload else ""
    raw = f"{provider_name}:{provider_event_id}:{home_goals}:{away_goals}:{status}:{payload_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ResultVerificationService:
    @staticmethod
    async def record_observation(
        db: AsyncSession,
        match_id: int,
        provider_name: str,
        provider_event_id: Optional[str],
        home_goals: Optional[int],
        away_goals: Optional[int],
        raw_status: str,
        competition_name: Optional[str] = None,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        provider_timestamp: Optional[datetime] = None,
        raw_payload: Optional[Dict[str, Any]] = None,
        sport: str = "football",
    ) -> ResultObservation:
        """
        Record a result observation from an external provider idempotently.
        Creates a new version if scores or status changed for this provider & match.
        """
        norm_status = normalize_status(raw_status, sport=sport)

        # Do NOT classify match as completed solely because scores exist if raw status is scheduled
        if norm_status not in ("full_time", "extra_time", "penalty") and norm_status != "in_progress":
            reported_outcome = None
        else:
            if home_goals is not None and away_goals is not None:
                if home_goals > away_goals:
                    reported_outcome = "home"
                elif home_goals == away_goals:
                    reported_outcome = "draw"
                else:
                    reported_outcome = "away"
            else:
                reported_outcome = None

        content_hash = compute_content_hash(
            provider_name, provider_event_id, home_goals, away_goals, norm_status, raw_payload
        )

        # Check existing observations for this provider and match
        stmt = (
            select(ResultObservation)
            .where(
                ResultObservation.match_id == match_id,
                ResultObservation.provider_name == provider_name,
            )
            .order_by(ResultObservation.version.desc())
        )
        res = await db.execute(stmt)
        existing_obs = res.scalars().all()

        if existing_obs:
            latest = existing_obs[0]
            # Exact idempotent match
            if latest.content_hash == content_hash:
                return latest

            # Check if score or status actually changed -> bump version
            next_version = latest.version + 1
            val_outcome = "correction" if (latest.home_goals != home_goals or latest.away_goals != away_goals) else "update"
        else:
            next_version = 1
            val_outcome = "initial"

        obs = ResultObservation(
            match_id=match_id,
            provider_name=provider_name,
            provider_event_id=provider_event_id,
            competition_name=competition_name,
            home_team=home_team,
            away_team=away_team,
            home_goals=home_goals,
            away_goals=away_goals,
            reported_outcome=reported_outcome,
            status=norm_status,
            provider_timestamp=provider_timestamp,
            local_timestamp=_utcnow(),
            validation_outcome=val_outcome,
            content_hash=content_hash,
            version=next_version,
            raw_payload=raw_payload,
        )
        db.add(obs)
        await db.flush()
        return obs

    @staticmethod
    async def verify_match_result(
        db: AsyncSession,
        match_id: int
    ) -> ResultVerification:
        """
        Evaluate all observations for a match, compare independent sources,
        and update consolidated ResultVerification record.
        """
        # Fetch match
        m_stmt = select(Match).where(Match.id == match_id)
        match_res = await db.execute(m_stmt)
        match = match_res.scalar_one_or_none()
        if not match:
            raise ValueError(f"Match ID {match_id} not found")

        # Fetch latest observation for each provider
        obs_stmt = (
            select(ResultObservation)
            .where(ResultObservation.match_id == match_id)
            .order_by(ResultObservation.provider_name, ResultObservation.version.desc())
        )
        res = await db.execute(obs_stmt)
        all_obs = res.scalars().all()

        # Group by provider_name -> latest observation
        latest_by_provider: Dict[str, ResultObservation] = {}
        for obs in all_obs:
            if obs.provider_name not in latest_by_provider:
                latest_by_provider[obs.provider_name] = obs

        providers = list(latest_by_provider.keys())
        source_count = len(providers)

        # Get existing verification record or create one
        ver_stmt = select(ResultVerification).where(ResultVerification.match_id == match_id)
        ver_res = await db.execute(ver_stmt)
        verification = ver_res.scalar_one_or_none()
        if not verification:
            verification = ResultVerification(
                match_id=match_id,
                verification_status="PENDING_RESULT",
                correction_history=[],
            )
            db.add(verification)

        prev_status = verification.verification_status
        prev_home = verification.verified_home_goals
        prev_away = verification.verified_away_goals

        if source_count == 0:
            verification.verification_status = "PENDING_RESULT"
            verification.source_count = 0
            verification.verification_reason = "No result observations recorded"
            await db.flush()
            return verification

        # Filter to completed/terminal observations (full_time, extra_time, penalty)
        terminal_obs = [
            o for o in latest_by_provider.values()
            if o.status in ("full_time", "extra_time", "penalty") and o.home_goals is not None and o.away_goals is not None
        ]

        non_terminal_obs = [
            o for o in latest_by_provider.values()
            if o.status in ("postponed", "abandoned", "cancelled")
        ]

        if non_terminal_obs and not terminal_obs:
            first_nt = non_terminal_obs[0]
            verification.verification_status = "UNAVAILABLE"
            verification.source_count = source_count
            verification.primary_provider = first_nt.provider_name
            verification.verification_reason = f"Event status is non-terminal: {first_nt.status}"
            await db.flush()
            return verification

        if not terminal_obs:
            verification.verification_status = "PENDING_RESULT"
            verification.source_count = source_count
            verification.verification_reason = "Observations present but none indicate terminal full_time completion"
            await db.flush()
            return verification

        # We have terminal observations
        primary_obs = terminal_obs[0]
        verification.primary_provider = primary_obs.provider_name

        if len(terminal_obs) == 1:
            # Single source terminal result
            verification.source_count = 1
            verification.agreement_ratio = 1.0
            verification.verified_home_goals = primary_obs.home_goals
            verification.verified_away_goals = primary_obs.away_goals
            verification.verified_outcome = primary_obs.reported_outcome

            # Do NOT claim 2-source verification. Indicate unverified / single-source PENDING_VERIFICATION or VERIFIED with single source warning.
            # Per prompt: "A missing second source must remain visibly unverified rather than silently being treated as confirmed."
            verification.verification_status = "PENDING_VERIFICATION"
            verification.verification_reason = (
                f"Single source result recorded from '{primary_obs.provider_name}' "
                f"({primary_obs.home_goals}-{primary_obs.away_goals}). Pending independent second source verification."
            )
            verification.secondary_provider = None

        else:
            # Multiple independent sources
            secondary_obs = terminal_obs[1]
            verification.source_count = len(terminal_obs)
            verification.secondary_provider = secondary_obs.provider_name

            # Compare terminal scores across all terminal sources
            scores = [(o.home_goals, o.away_goals) for o in terminal_obs]
            matching_count = sum(1 for s in scores if s == (primary_obs.home_goals, primary_obs.away_goals))
            ratio = matching_count / float(len(terminal_obs))
            verification.agreement_ratio = ratio

            if ratio == 1.0:
                verification.verified_home_goals = primary_obs.home_goals
                verification.verified_away_goals = primary_obs.away_goals
                verification.verified_outcome = primary_obs.reported_outcome
                verification.verification_status = "VERIFIED"
                verification.verification_reason = (
                    f"Verified across {len(terminal_obs)} independent sources ({primary_obs.provider_name}, "
                    f"{secondary_obs.provider_name}). Outcome: {primary_obs.reported_outcome} ({primary_obs.home_goals}-{primary_obs.away_goals})."
                )

                # Sync match table if verified
                match.home_goals = primary_obs.home_goals
                match.away_goals = primary_obs.away_goals
                match.actual_outcome = primary_obs.reported_outcome
                match.status = "completed"

            else:
                verification.verification_status = "NEEDS_REVIEW"
                verification.verification_reason = (
                    f"Conflicting scores reported between sources. "
                    f"Primary '{primary_obs.provider_name}': {primary_obs.home_goals}-{primary_obs.away_goals}, "
                    f"Secondary '{secondary_obs.provider_name}': {secondary_obs.home_goals}-{secondary_obs.away_goals}."
                )

        # Check for corrections
        if prev_status == "VERIFIED" and (
            verification.verified_home_goals != prev_home or verification.verified_away_goals != prev_away
        ):
            verification.is_correction = True
            verification.verification_status = "CORRECTION_DETECTED"
            history = list(verification.correction_history or [])
            history.append({
                "timestamp": _utcnow().isoformat(),
                "previous_goals": [prev_home, prev_away],
                "new_goals": [verification.verified_home_goals, verification.verified_away_goals],
                "reason": verification.verification_reason
            })
            verification.correction_history = history

        verification.last_verified_at = _utcnow()
        await db.flush()
        return verification
