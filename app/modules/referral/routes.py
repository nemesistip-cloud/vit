"""Referral / affiliate API endpoints."""

import logging
import random
import string
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
    use = ReferralUse(
        referrer_id=code_rec.user_id,
        referee_id=current_user.id,
        bonus_amount=_BONUS_VIT,
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
                wallet.vitcoin_balance += Decimal(str(_BONUS_VIT))
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
