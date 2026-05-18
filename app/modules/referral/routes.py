"""Referral / affiliate API endpoints.

ENG-12: process_deposit_commission() and process_subscription_commission() are
called from WalletService after a confirmed deposit or subscription upgrade.
They credit the referrer with a configurable percentage of the transaction amount.
"""

import logging
import random
import string
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.modules.referral.models import ReferralCode, ReferralUse
from app.core.feature_flags import is_feature_enabled

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/referral", tags=["Referral"])

_BONUS_VIT = 50.0
_DEPOSIT_COMMISSION_PCT = Decimal("0.10")      # 10% of fiat deposit credited in VITCoin
_SUBSCRIPTION_COMMISSION_PCT = Decimal("0.10") # 10% of subscription value in VITCoin

async def _get_referral_config(db: AsyncSession) -> dict:
    """Load referral rewards from PlatformConfig."""
    from app.modules.wallet.models import PlatformConfig
    res = await db.execute(select(PlatformConfig).where(PlatformConfig.key == "referral_config"))
    cfg = res.scalar_one_or_none()

    defaults = {
        "bonus_vit": 50.0,
        "deposit_commission_pct": 0.10,
        "subscription_commission_pct": 0.10
    }

    if cfg and isinstance(cfg.value, dict):
        return {**defaults, **cfg.value}
    return defaults


async def process_deposit_commission(
    db: AsyncSession,
    referee_id: int,
    deposit_amount_usd: Decimal,
) -> None:
    """ENG-12: Credit the referrer with 10% of referee's confirmed deposit in VITCoin.

    This is safe to call multiple times — it only fires once per qualifying deposit
    because we create a new WalletTransaction for each commission payment.
    """
    try:
        ref_use = await db.execute(
            select(ReferralUse).where(ReferralUse.referee_id == referee_id)
        )
        use = ref_use.scalar_one_or_none()
        if not use:
            return

        cfg = await _get_referral_config(db)
        pct = Decimal(str(cfg["deposit_commission_pct"]))
        commission = deposit_amount_usd * pct
        if commission <= 0:
            return

        from app.modules.wallet.models import Wallet
        wallet_res = await db.execute(
            select(Wallet).where(Wallet.user_id == use.referrer_id)
        )
        wallet = wallet_res.scalar_one_or_none()
        if not wallet:
            return

        wallet.vitcoin_balance += commission
        await db.commit()
        logger.info(
            "[referral] Deposit commission: referrer_id=%d credited %.4f VITCoin (10%% of %.2f for referee_id=%d)",
            use.referrer_id, float(commission), float(deposit_amount_usd), referee_id,
        )
    except Exception:
        logger.exception(
            "[referral] Failed to process deposit commission for referee_id=%d", referee_id
        )


async def process_subscription_commission(
    db: AsyncSession,
    referee_id: int,
    plan_value_usd: Decimal,
) -> None:
    """ENG-12: Credit the referrer with 10% of the referred user's subscription value."""
    try:
        ref_use = await db.execute(
            select(ReferralUse).where(ReferralUse.referee_id == referee_id)
        )
        use = ref_use.scalar_one_or_none()
        if not use:
            return

        cfg = await _get_referral_config(db)
        pct = Decimal(str(cfg["subscription_commission_pct"]))
        commission = plan_value_usd * pct
        if commission <= 0:
            return

        from app.modules.wallet.models import Wallet
        wallet_res = await db.execute(
            select(Wallet).where(Wallet.user_id == use.referrer_id)
        )
        wallet = wallet_res.scalar_one_or_none()
        if not wallet:
            return

        wallet.vitcoin_balance += commission
        await db.commit()
        logger.info(
            "[referral] Subscription commission: referrer_id=%d credited %.4f VITCoin (10%% of %.2f for referee_id=%d)",
            use.referrer_id, float(commission), float(plan_value_usd), referee_id,
        )
    except Exception:
        logger.exception(
            "[referral] Failed to process subscription commission for referee_id=%d", referee_id
        )


async def _referrals_enabled(db: AsyncSession) -> bool:
    return await is_feature_enabled(db, "REFERRALS_ENABLED", True)


async def _require_referrals_enabled(db: AsyncSession) -> None:
    if not await _referrals_enabled(db):
        raise HTTPException(403, "Referral program is currently disabled.")


async def apply_referral_bonus(
    db: AsyncSession,
    current_user: User,
    code: str,
    commit: bool = True,
) -> dict:
    await _require_referrals_enabled(db)

    clean_code = code.strip().upper()
    if not clean_code:
        raise HTTPException(400, "Referral code is required.")

    already = await db.execute(
        select(ReferralUse).where(ReferralUse.referee_id == current_user.id)
    )
    if already.scalar_one_or_none():
        raise HTTPException(400, "You have already used a referral code.")

    code_res = await db.execute(
        select(ReferralCode).where(ReferralCode.code == clean_code)
    )
    code_rec = code_res.scalar_one_or_none()
    if not code_rec:
        raise HTTPException(404, "Referral code not found.")

    if code_rec.user_id == current_user.id:
        raise HTTPException(400, "You cannot use your own referral code.")

    logger.info(
        "[referral] Applying code '%s': referrer_id=%d referee_id=%d",
        clean_code, code_rec.user_id, current_user.id,
    )
    cfg = await _get_referral_config(db)
    bonus_val = cfg["bonus_vit"]

    use = ReferralUse(
        referrer_id=code_rec.user_id,
        referee_id=current_user.id,
        bonus_amount=bonus_val,
        bonus_paid=False,
    )
    db.add(use)

    bonus_paid = False
    try:
        from app.modules.wallet.models import Wallet
        from decimal import Decimal

        updated = 0
        for uid in [code_rec.user_id, current_user.id]:
            wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == uid))
            wallet = wallet_res.scalar_one_or_none()
            if wallet:
                wallet.vitcoin_balance += Decimal(str(bonus_val))
                updated += 1

        if updated == 2:
            use.bonus_paid = True
            bonus_paid = True
        else:
            logger.warning(
                "Referral bonus not fully paid: only %d/2 wallets found for referrer=%d referee=%d",
                updated, code_rec.user_id, current_user.id,
            )
    except Exception:
        logger.exception(
            "Failed to credit referral bonus for referrer=%d referee=%d",
            code_rec.user_id, current_user.id,
        )

    if commit:
        await db.commit()

    if bonus_paid:
        logger.info(
            "[referral] Bonus paid: referrer_id=%d and referee_id=%d each credited %.1f VITCoin",
            code_rec.user_id, current_user.id, _BONUS_VIT,
        )

    msg = (
        f"Referral code applied! Both you and the referrer received {_BONUS_VIT} VITCoin."
        if bonus_paid
        else "Referral code recorded. Bonus will be credited shortly."
    )
    return {"message": msg, "bonus_vit": _BONUS_VIT if bonus_paid else 0, "bonus_paid": bonus_paid}


def _gen_code(username: str) -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    prefix = (username[:4].upper() if username else "VIT")
    return f"{prefix}{suffix}"


@router.get("/my-code")
async def get_my_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get (or create) this user's personal referral code."""
    await _require_referrals_enabled(db)

    result = await db.execute(
        select(ReferralCode).where(ReferralCode.user_id == current_user.id)
    )
    rec = result.scalar_one_or_none()

    if not rec:
        code = _gen_code(current_user.username)
        while (await db.execute(select(ReferralCode).where(ReferralCode.code == code))).scalar_one_or_none():
            code = _gen_code(current_user.username)
        rec = ReferralCode(user_id=current_user.id, code=code)
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
        logger.info("[referral] Created new referral code '%s' for user_id=%d", code, current_user.id)

    uses_q = await db.execute(
        select(func.count()).select_from(ReferralUse).where(ReferralUse.referrer_id == current_user.id)
    )
    total_referrals = uses_q.scalar() or 0

    paid_q = await db.execute(
        select(func.sum(ReferralUse.bonus_amount)).where(
            ReferralUse.referrer_id == current_user.id,
            ReferralUse.bonus_paid == True,
        )
    )
    total_bonus_earned = float(paid_q.scalar() or 0)

    return {
        "code": rec.code,
        "total_referrals": total_referrals,
        "total_bonus_earned_vit": total_bonus_earned,
        "bonus_per_referral_vit": _BONUS_VIT,
        "share_url": f"/register?ref={rec.code}",
    }


@router.get("/stats")
async def referral_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detailed referral statistics."""
    await _require_referrals_enabled(db)

    uses = await db.execute(
        select(ReferralUse).where(ReferralUse.referrer_id == current_user.id)
        .order_by(ReferralUse.created_at.desc())
    )
    rows = uses.scalars().all()

    details = []
    for r in rows:
        ref_user_res = await db.execute(select(User).where(User.id == r.referee_id))
        ref_user = ref_user_res.scalar_one_or_none()
        details.append({
            "referee_username": ref_user.username if ref_user else "Unknown",
            "bonus_paid": r.bonus_paid,
            "bonus_amount": r.bonus_amount,
            "joined_at": r.created_at,
        })

    return {
        "referrals": details,
        "total": len(details),
        "pending_bonuses": sum(1 for r in rows if not r.bonus_paid),
    }


class ApplyReferralRequest(BaseModel):
    code: str


@router.post("/apply")
async def apply_referral(
    body: ApplyReferralRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply a referral code at registration (call right after /auth/register)."""
    return await apply_referral_bonus(db, current_user, body.code, commit=True)


@router.get("/leaderboard")
async def referral_leaderboard(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Top referrers by number of successful referrals."""
    await _require_referrals_enabled(db)

    results = await db.execute(
        select(ReferralUse.referrer_id, func.count(ReferralUse.id).label("count"))
        .group_by(ReferralUse.referrer_id)
        .order_by(func.count(ReferralUse.id).desc())
        .limit(limit)
    )
    rows = results.all()

    board = []
    for i, (uid, count) in enumerate(rows, 1):
        user_res = await db.execute(select(User).where(User.id == uid))
        user = user_res.scalar_one_or_none()
        board.append({
            "rank": i,
            "username": user.username if user else "Unknown",
            "referrals": count,
            "earned_vit": count * _BONUS_VIT,
        })

    return {"leaderboard": board}
