"""Security Service — anti-Sybil, fraud detection, multi-sig, wallet freeze."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.security.models import (
    FraudAlert,
    FraudSeverity,
    FreezeStatus,
    MultiSigOperation,
    MultiSigSignature,
    MultiSigStatus,
    RateLimitLedger,
    SybilProfile,
    SybilRisk,
    WalletFreeze,
)

logger = logging.getLogger(__name__)

SYBIL_WEIGHTS = {
    "prediction_velocity": 0.25,
    "stake_velocity": 0.20,
    "device_fingerprints": 0.15,
    "referral_cluster_score": 0.25,
    "account_age_days": 0.15,
}

RISK_THRESHOLDS = {
    SybilRisk.LOW:     0.20,
    SybilRisk.MEDIUM:  0.45,
    SybilRisk.HIGH:    0.65,
    SybilRisk.FLAGGED: 0.80,
}


def _compute_anomaly_score(profile: SybilProfile) -> Decimal:
    age_score = max(0.0, 1.0 - min(profile.account_age_days / 365, 1.0))
    fps_score = min((profile.device_fingerprints - 1) / 4, 1.0)
    pred_v = min(float(profile.prediction_velocity) / 50.0, 1.0)
    stake_v = min(float(profile.stake_velocity) / 20.0, 1.0)
    ref_score = float(profile.referral_cluster_score)

    composite = (
        pred_v * SYBIL_WEIGHTS["prediction_velocity"]
        + stake_v * SYBIL_WEIGHTS["stake_velocity"]
        + fps_score * SYBIL_WEIGHTS["device_fingerprints"]
        + ref_score * SYBIL_WEIGHTS["referral_cluster_score"]
        + age_score * SYBIL_WEIGHTS["account_age_days"]
    )
    return Decimal(str(round(composite, 4)))


def _risk_level(score: Decimal) -> SybilRisk:
    f = float(score)
    for level in [SybilRisk.FLAGGED, SybilRisk.HIGH, SybilRisk.MEDIUM, SybilRisk.LOW]:
        if f >= RISK_THRESHOLDS[level]:
            return level
    return SybilRisk.CLEAN


async def get_or_create_sybil_profile(
    db: AsyncSession, user_id: int
) -> SybilProfile:
    existing = await db.scalar(
        select(SybilProfile).where(SybilProfile.user_id == user_id)
    )
    if existing:
        return existing
    profile = SybilProfile(user_id=user_id, account_age_days=0)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def evaluate_sybil_risk(
    db: AsyncSession,
    user_id: int,
    prediction_velocity: float | None = None,
    stake_velocity: float | None = None,
    device_fingerprints: int | None = None,
    referral_cluster_score: float | None = None,
    account_age_days: int | None = None,
    ip_cluster_id: str | None = None,
) -> SybilProfile:
    profile = await get_or_create_sybil_profile(db, user_id)

    if prediction_velocity is not None:
        profile.prediction_velocity = Decimal(str(prediction_velocity))
    if stake_velocity is not None:
        profile.stake_velocity = Decimal(str(stake_velocity))
    if device_fingerprints is not None:
        profile.device_fingerprints = device_fingerprints
    if referral_cluster_score is not None:
        profile.referral_cluster_score = Decimal(str(referral_cluster_score))
    if account_age_days is not None:
        profile.account_age_days = account_age_days
    if ip_cluster_id is not None:
        profile.ip_cluster_id = ip_cluster_id

    score = _compute_anomaly_score(profile)
    profile.anomaly_score = score
    risk = _risk_level(score)
    profile.risk_level = risk
    profile.last_evaluated_at = datetime.now(timezone.utc)

    if risk in (SybilRisk.HIGH, SybilRisk.FLAGGED):
        await create_fraud_alert(
            db, user_id=user_id,
            severity=FraudSeverity.HIGH if risk == SybilRisk.HIGH else FraudSeverity.CRITICAL,
            alert_type="sybil_detection",
            description=f"High Sybil risk detected: score={score}, level={risk}",
            anomaly_score=score,
        )

    await db.commit()
    await db.refresh(profile)
    return profile


async def create_fraud_alert(
    db: AsyncSession,
    alert_type: str,
    description: str,
    severity: FraudSeverity = FraudSeverity.MEDIUM,
    user_id: int | None = None,
    evidence: str | None = None,
    anomaly_score: Decimal = Decimal("0"),
) -> FraudAlert:
    alert = FraudAlert(
        user_id=user_id,
        severity=severity,
        alert_type=alert_type,
        description=description,
        evidence=evidence,
        anomaly_score=anomaly_score,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def resolve_fraud_alert(
    db: AsyncSession,
    alert_id: int,
    resolved_by: int,
    action: str,
) -> FraudAlert:
    alert = await db.get(FraudAlert, alert_id)
    if not alert:
        raise ValueError("Alert not found")
    alert.resolved = True
    alert.resolved_by = resolved_by
    alert.resolution_action = action
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert


async def propose_multisig(
    db: AsyncSession,
    operation_type: str,
    description: str,
    payload: str,
    required_signers: int = 3,
    threshold: int = 2,
    proposer_user_id: int | None = None,
    ttl_hours: int = 48,
) -> MultiSigOperation:
    op = MultiSigOperation(
        operation_type=operation_type,
        description=description,
        payload=payload,
        required_signers=required_signers,
        threshold=threshold,
        proposer_user_id=proposer_user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    )
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return op


async def sign_multisig(
    db: AsyncSession,
    operation_id: int,
    signer_user_id: int,
    approved: bool = True,
) -> MultiSigOperation:
    op = await db.get(MultiSigOperation, operation_id)
    if not op:
        raise ValueError("Operation not found")
    if op.status == MultiSigStatus.EXECUTED:
        raise ValueError("Already executed")
    if op.expires_at and op.expires_at < datetime.now(timezone.utc):
        op.status = MultiSigStatus.EXPIRED
        await db.commit()
        raise ValueError("Operation expired")

    existing_sig = await db.scalar(
        select(MultiSigSignature).where(
            and_(
                MultiSigSignature.operation_id == operation_id,
                MultiSigSignature.signer_user_id == signer_user_id,
            )
        )
    )
    if existing_sig:
        raise ValueError("Already signed")

    sig_hash = "0x" + hashlib.sha3_256(
        f"{operation_id}:{signer_user_id}:{approved}:{secrets.token_hex(8)}".encode()
    ).hexdigest()

    sig = MultiSigSignature(
        operation_id=operation_id,
        signer_user_id=signer_user_id,
        signature_hash=sig_hash,
        approved=approved,
    )
    db.add(sig)

    sigs_q = await db.execute(
        select(func.count(MultiSigSignature.id)).where(
            and_(
                MultiSigSignature.operation_id == operation_id,
                MultiSigSignature.approved.is_(True),
            )
        )
    )
    approval_count = (sigs_q.scalar() or 0) + (1 if approved else 0)

    if approval_count >= op.threshold:
        op.status = MultiSigStatus.APPROVED
    elif not approved:
        op.status = MultiSigStatus.REJECTED
    else:
        op.status = MultiSigStatus.PARTIALLY_SIGNED

    await db.commit()
    await db.refresh(op)
    return op


async def freeze_wallet(
    db: AsyncSession,
    user_id: int,
    reason: str,
    freeze_type: str = "full",
    frozen_by: int | None = None,
    fraud_alert_id: int | None = None,
    frozen_amount: Decimal | None = None,
    auto_lift_hours: int | None = None,
) -> WalletFreeze:
    freeze = WalletFreeze(
        user_id=user_id,
        reason=reason,
        freeze_type=freeze_type,
        frozen_by=frozen_by,
        fraud_alert_id=fraud_alert_id,
        frozen_amount=frozen_amount,
        auto_lift_at=datetime.now(timezone.utc) + timedelta(hours=auto_lift_hours)
        if auto_lift_hours
        else None,
    )
    db.add(freeze)
    await db.commit()
    await db.refresh(freeze)
    return freeze


async def lift_freeze(
    db: AsyncSession,
    freeze_id: int,
    lifted_by: int,
    notes: str | None = None,
) -> WalletFreeze:
    freeze = await db.get(WalletFreeze, freeze_id)
    if not freeze:
        raise ValueError("Freeze not found")
    freeze.status = FreezeStatus.LIFTED
    freeze.lifted_by = lifted_by
    freeze.lift_notes = notes
    freeze.lifted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(freeze)
    return freeze


async def check_rate_limit(
    db: AsyncSession,
    endpoint: str,
    user_id: int | None = None,
    ip_address: str | None = None,
    window_minutes: int = 1,
    max_calls: int = 60,
) -> dict:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)

    q = select(func.sum(RateLimitLedger.call_count)).where(
        RateLimitLedger.endpoint == endpoint,
        RateLimitLedger.window_start >= window_start,
    )
    if user_id:
        q = q.where(RateLimitLedger.user_id == user_id)
    elif ip_address:
        q = q.where(RateLimitLedger.ip_address == ip_address)

    count = await db.scalar(q) or 0
    blocked = count >= max_calls

    ledger = RateLimitLedger(
        user_id=user_id,
        ip_address=ip_address,
        endpoint=endpoint,
        call_count=1,
        window_start=now,
        window_end=now + timedelta(minutes=window_minutes),
        blocked=blocked,
    )
    db.add(ledger)
    await db.commit()

    return {"allowed": not blocked, "current_count": count + 1, "limit": max_calls, "window_minutes": window_minutes}


async def get_security_dashboard(db: AsyncSession) -> dict:
    total_alerts = await db.scalar(select(func.count(FraudAlert.id))) or 0
    open_alerts = await db.scalar(
        select(func.count(FraudAlert.id)).where(FraudAlert.resolved.is_(False))
    ) or 0
    critical_alerts = await db.scalar(
        select(func.count(FraudAlert.id)).where(
            and_(FraudAlert.severity == FraudSeverity.CRITICAL, FraudAlert.resolved.is_(False))
        )
    ) or 0
    active_freezes = await db.scalar(
        select(func.count(WalletFreeze.id)).where(WalletFreeze.status == FreezeStatus.ACTIVE)
    ) or 0
    pending_multisig = await db.scalar(
        select(func.count(MultiSigOperation.id)).where(
            MultiSigOperation.status.in_([MultiSigStatus.PENDING, MultiSigStatus.PARTIALLY_SIGNED])
        )
    ) or 0
    flagged_users = await db.scalar(
        select(func.count(SybilProfile.id)).where(
            SybilProfile.risk_level.in_([SybilRisk.FLAGGED, SybilRisk.HIGH])
        )
    ) or 0
    return {
        "total_fraud_alerts": total_alerts,
        "open_alerts": open_alerts,
        "critical_alerts": critical_alerts,
        "active_wallet_freezes": active_freezes,
        "pending_multisig_operations": pending_multisig,
        "high_risk_users": flagged_users,
    }
