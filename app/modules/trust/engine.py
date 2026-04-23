"""
Module I — Trust engine: async score calculation + fraud detection rules.

Trust Score (0–100):
  - transaction_score  (weight 0.30) — wallet behaviour
  - prediction_score   (weight 0.30) — prediction accuracy & consistency
  - activity_score     (weight 0.20) — account age & engagement
  - 20% is headroom reduced by fraud_penalty

Fraud Detection Rules (I2):
  RULE-WD-01  Rapid withdrawals   — > 3 withdrawals within 1 hour
  RULE-WD-02  Abnormal withdrawal — single withdrawal > 3× 30-day avg
  RULE-WD-03  Cold account drain  — account < 7 days old + any withdrawal
  RULE-BET-01 Bet bombing         — > 20 marketplace model calls in 10 minutes
  RULE-VAL-01 Clone predictions   — validator submits same outcome > 95% of time
  RULE-ACC-01 Dormant spike       — no activity 30 days then sudden large tx
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.trust.models import UserTrustScore, FraudFlag, RiskEvent
from app.modules.wallet.models import WalletTransaction

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------
W_TRANSACTION  = 0.30
W_PREDICTION   = 0.30
W_ACTIVITY     = 0.20
W_FRAUD        = 0.20   # headroom reduced by fraud penalty

TIER_THRESHOLDS = {
    "critical": 30,
    "high":     50,
    "medium":   70,
    "low":      101,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _risk_tier(score: float) -> str:
    for tier, upper in TIER_THRESHOLDS.items():
        if score < upper:
            return tier
    return "low"


# ---------------------------------------------------------------------------
# Internal flag helper
# ---------------------------------------------------------------------------

async def _flag(
    db: AsyncSession,
    user_id: int,
    rule_code: str,
    category: str,
    severity: str,
    title: str,
    detail: str,
    evidence: dict[str, Any],
    score_impact: float = -5.0,
) -> Optional[FraudFlag]:
    """Create FraudFlag + RiskEvent only if the rule is not already open."""
    result = await db.execute(
        select(FraudFlag).where(
            FraudFlag.user_id == user_id,
            FraudFlag.rule_code == rule_code,
            FraudFlag.status == "open",
        )
    )
    if result.scalars().first():
        return None

    evidence_json = json.dumps(evidence)
    flag = FraudFlag(
        user_id=user_id,
        category=category,
        severity=severity,
        rule_code=rule_code,
        title=title,
        detail=detail,
        evidence_json=evidence_json,
        flagged_by="system",
    )
    db.add(flag)

    event = RiskEvent(
        user_id=user_id,
        rule_code=rule_code,
        score_impact=score_impact,
        detail=detail,
        evidence_json=evidence_json,
    )
    db.add(event)
    await db.flush()
    return flag


# ---------------------------------------------------------------------------
# Sub-score calculators
# ---------------------------------------------------------------------------

async def _calc_transaction_score(db: AsyncSession, user_id: int) -> float:
    now = _utcnow()
    window_90 = now - timedelta(days=90)

    result = await db.execute(
        select(WalletTransaction).where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.created_at >= window_90,
        )
    )
    txs = result.scalars().all()

    if not txs:
        return 40.0

    tx_count   = len(txs)
    types      = set(t.type for t in txs)
    directions = set(t.direction for t in txs)
    successful = sum(1 for t in txs if t.status in ("completed", "confirmed", "success"))

    score = 40.0
    score += min(tx_count * 0.5, 20)
    score += min(len(types) * 3, 15)
    score += 5 if len(directions) > 1 else 0
    if tx_count > 0:
        score += (successful / tx_count) * 20

    return min(max(score, 0.0), 100.0)


async def _calc_prediction_score(db: AsyncSession, user_id: int) -> float:
    try:
        from app.modules.blockchain.models import ValidatorPrediction
        result = await db.execute(
            select(ValidatorPrediction).where(ValidatorPrediction.validator_id == user_id)
        )
        preds = result.scalars().all()
    except Exception:
        return 50.0

    if not preds:
        return 50.0

    total   = len(preds)
    correct = sum(1 for p in preds if getattr(p, "is_correct", False))
    acc     = correct / total

    return min(max(30.0 + acc * 50 + min(total * 0.2, 20), 0.0), 100.0)


async def _calc_activity_score(db: AsyncSession, user_id: int) -> float:
    from app.db.models import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        return 0.0

    now = _utcnow()
    created = user.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_days = (now - created).days

    score = 30.0 + min(age_days * 0.2, 30)

    if user.last_login:
        last = user.last_login
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days_since = (now - last).days
        if days_since < 7:
            score += 20
        elif days_since < 30:
            score += 10
        elif days_since < 90:
            score += 5

    if user.is_verified:
        score += 10
    if user.role in ("admin", "validator"):
        score += 10

    return min(max(score, 0.0), 100.0)


# ---------------------------------------------------------------------------
# Fraud detection rules
# ---------------------------------------------------------------------------

async def _detect_rapid_withdrawals(db: AsyncSession, user_id: int) -> list[FraudFlag]:
    window = _utcnow() - timedelta(hours=1)
    result = await db.execute(
        select(func.count(WalletTransaction.id)).where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.type == "withdrawal",
            WalletTransaction.created_at >= window,
        )
    )
    count = result.scalar() or 0
    if count > 3:
        f = await _flag(
            db, user_id,
            rule_code="RULE-WD-01", category="withdrawal", severity="high",
            title="Rapid Withdrawal Pattern",
            detail=f"{count} withdrawals detected within the last hour (threshold: 3).",
            evidence={"withdrawal_count_1h": count, "threshold": 3},
            score_impact=-10.0,
        )
        return [f] if f else []
    return []


async def _detect_abnormal_withdrawal(db: AsyncSession, user_id: int) -> list[FraudFlag]:
    window_30 = _utcnow() - timedelta(days=30)
    result = await db.execute(
        select(WalletTransaction).where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.type == "withdrawal",
            WalletTransaction.created_at >= window_30,
        )
    )
    txs = result.scalars().all()

    if len(txs) < 2:
        return []

    amounts = [float(t.amount) for t in txs]
    avg = sum(amounts) / len(amounts)
    max_amt = max(amounts)

    if avg > 0 and max_amt > avg * 3:
        f = await _flag(
            db, user_id,
            rule_code="RULE-WD-02", category="withdrawal", severity="medium",
            title="Abnormally Large Withdrawal",
            detail=f"Max withdrawal {max_amt:.2f} is {max_amt/avg:.1f}× the 30-day average ({avg:.2f}).",
            evidence={"max_withdrawal": max_amt, "avg_30d": round(avg, 2), "ratio": round(max_amt / avg, 2)},
            score_impact=-7.0,
        )
        return [f] if f else []
    return []


async def _detect_cold_account_drain(db: AsyncSession, user_id: int) -> list[FraudFlag]:
    from app.db.models import User
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalars().first()
    if not user:
        return []

    now = _utcnow()
    created = user.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_days = (now - created).days
    if age_days >= 7:
        return []

    wd_result = await db.execute(
        select(func.count(WalletTransaction.id)).where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.type == "withdrawal",
        )
    )
    recent_wd = wd_result.scalar() or 0
    if recent_wd > 0:
        f = await _flag(
            db, user_id,
            rule_code="RULE-WD-03", category="withdrawal", severity="high",
            title="New Account Withdrawal Attempt",
            detail=f"Account is only {age_days} day(s) old with {recent_wd} withdrawal(s).",
            evidence={"account_age_days": age_days, "withdrawal_count": recent_wd},
            score_impact=-15.0,
        )
        return [f] if f else []
    return []


async def _detect_bet_bombing(db: AsyncSession, user_id: int) -> list[FraudFlag]:
    try:
        from app.modules.marketplace.models import ModelUsageLog
        window = _utcnow() - timedelta(minutes=10)
        result = await db.execute(
            select(func.count(ModelUsageLog.id)).where(
                ModelUsageLog.caller_id == user_id,
                ModelUsageLog.called_at >= window,
            )
        )
        count = result.scalar() or 0
        if count > 20:
            f = await _flag(
                db, user_id,
                rule_code="RULE-BET-01", category="betting", severity="medium",
                title="High-Frequency Model Call Pattern",
                detail=f"{count} model calls in the last 10 minutes (threshold: 20).",
                evidence={"calls_10min": count, "threshold": 20},
                score_impact=-6.0,
            )
            return [f] if f else []
    except Exception:
        pass
    return []


async def _detect_validator_clone_predictions(db: AsyncSession, user_id: int) -> list[FraudFlag]:
    try:
        from app.modules.blockchain.models import ValidatorPrediction
        result = await db.execute(
            select(ValidatorPrediction).where(ValidatorPrediction.validator_id == user_id)
        )
        preds = result.scalars().all()
        if len(preds) < 20:
            return []

        outcomes = [p.predicted_outcome for p in preds if hasattr(p, "predicted_outcome")]
        if not outcomes:
            return []

        mode_count = max(outcomes.count(o) for o in set(outcomes))
        ratio = mode_count / len(outcomes)

        if ratio > 0.95:
            f = await _flag(
                db, user_id,
                rule_code="RULE-VAL-01", category="validator", severity="high",
                title="Validator Clone Prediction Pattern",
                detail=f"Same outcome submitted in {ratio*100:.1f}% of {len(outcomes)} predictions.",
                evidence={"identical_ratio": round(ratio, 3), "total_predictions": len(outcomes)},
                score_impact=-12.0,
            )
            return [f] if f else []
    except Exception:
        pass
    return []


async def _detect_dormant_spike(db: AsyncSession, user_id: int) -> list[FraudFlag]:
    now = _utcnow()
    window_30 = now - timedelta(days=30)
    window_7  = now - timedelta(days=7)

    mid_result = await db.execute(
        select(func.count(WalletTransaction.id)).where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.created_at.between(window_30, window_7),
        )
    )
    if (mid_result.scalar() or 0) > 0:
        return []

    recent_result = await db.execute(
        select(WalletTransaction).where(
            WalletTransaction.user_id == user_id,
            WalletTransaction.created_at >= window_7,
        )
    )
    recent = recent_result.scalars().all()
    if not recent:
        return []

    max_recent = max(float(t.amount) for t in recent)
    if max_recent > 500:
        f = await _flag(
            db, user_id,
            rule_code="RULE-ACC-01", category="account", severity="medium",
            title="Dormant Account Spike",
            detail=f"No activity for 23–30 days; largest recent transaction: {max_recent:.2f}.",
            evidence={"max_recent_amount": max_recent, "dormant_period_days": 23},
            score_impact=-8.0,
        )
        return [f] if f else []
    return []


# ---------------------------------------------------------------------------
# Master calculate function
# ---------------------------------------------------------------------------

DETECTORS = [
    _detect_rapid_withdrawals,
    _detect_abnormal_withdrawal,
    _detect_cold_account_drain,
    _detect_bet_bombing,
    _detect_validator_clone_predictions,
    _detect_dormant_spike,
]


async def calculate_trust_score(db: AsyncSession, user_id: int) -> UserTrustScore:
    """Run all detectors, compute sub-scores, write/update UserTrustScore."""
    new_flags: list[FraudFlag] = []
    for detector in DETECTORS:
        try:
            new_flags.extend(await detector(db, user_id))
        except Exception as exc:
            log.warning("Trust detector error for user %s: %s", user_id, exc)

    tx_score   = await _calc_transaction_score(db, user_id)
    pred_score = await _calc_prediction_score(db, user_id)
    act_score  = await _calc_activity_score(db, user_id)

    open_result = await db.execute(
        select(FraudFlag).where(FraudFlag.user_id == user_id, FraudFlag.status == "open")
    )
    open_flags = open_result.scalars().all()

    severity_weight = {"low": 2.0, "medium": 5.0, "high": 10.0, "critical": 20.0}
    raw_penalty = sum(severity_weight.get(f.severity, 5.0) for f in open_flags)
    fraud_penalty = min(raw_penalty, 40.0)

    composite = (
        tx_score   * W_TRANSACTION +
        pred_score * W_PREDICTION  +
        act_score  * W_ACTIVITY    +
        50.0       * W_FRAUD
        - fraud_penalty
    )
    composite = min(max(composite, 0.0), 100.0)

    record_result = await db.execute(
        select(UserTrustScore).where(UserTrustScore.user_id == user_id)
    )
    record = record_result.scalars().first()
    if not record:
        record = UserTrustScore(user_id=user_id)
        db.add(record)

    total_flags_result = await db.execute(
        select(func.count(FraudFlag.id)).where(FraudFlag.user_id == user_id)
    )

    record.transaction_score  = round(tx_score,   2)
    record.prediction_score   = round(pred_score, 2)
    record.activity_score     = round(act_score,  2)
    record.fraud_penalty      = round(fraud_penalty, 2)
    record.composite_score    = round(composite,  2)
    record.risk_tier          = _risk_tier(composite)
    record.total_flags        = total_flags_result.scalar() or 0
    record.open_flags         = len(open_flags) + len(new_flags)
    record.last_calculated_at = _utcnow()

    await db.commit()
    await db.refresh(record)

    # ── v4.5: Auto-suspension for critical trust scores ───────────────────
    # If composite drops below 30 and there are open fraud flags, auto-suspend
    # the user and create a system notification for admin review.
    if composite < 30 and len(open_flags) + len(new_flags) > 0:
        try:
            from app.db.models import User
            user_res = await db.execute(select(User).where(User.id == user_id))
            user = user_res.scalars().first()
            if user and user.is_active and not getattr(user, "is_banned", False):
                user.is_active = False
                await db.commit()
                log.warning(
                    "[trust] AUTO-SUSPENDED user %s (score=%.1f, open_flags=%d)",
                    user_id, composite, len(open_flags) + len(new_flags),
                )
                try:
                    from app.modules.notifications.service import NotificationService
                    await NotificationService.create(
                        db=db,
                        user_id=user_id,
                        type="account_suspended",
                        title="Account Temporarily Suspended",
                        body=(
                            "Your account has been temporarily suspended due to suspicious activity. "
                            "Please contact support to appeal."
                        ),
                        channel="in_app",
                    )
                except Exception:
                    pass
        except Exception as exc:
            log.error("[trust] Auto-suspension failed for user %s: %s", user_id, exc)

    return record


# ---------------------------------------------------------------------------
# Batch refresh
# ---------------------------------------------------------------------------

async def refresh_all_trust_scores(db: AsyncSession) -> int:
    from app.db.models import User
    result = await db.execute(select(User.id).where(User.is_active == True))
    user_ids = [row[0] for row in result.all()]
    count = 0
    for uid in user_ids:
        try:
            await calculate_trust_score(db, uid)
            count += 1
        except Exception as exc:
            log.error("Failed trust score for user %s: %s", uid, exc)
    return count
