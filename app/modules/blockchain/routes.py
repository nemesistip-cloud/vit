"""Blockchain economy API routes — Module C4."""

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.blockchain.consensus import calculate_consensus
from app.modules.blockchain.models import (
    ConsensusPrediction,
    ConsensusStatus,
    MatchSettlement,
    UserStake,
    StakeStatus,
    ValidatorPrediction,
    ValidatorProfile,
    ValidatorStatus,
)
from app.modules.wallet.models import Wallet
from app.modules.wallet.pricing import VITCoinPricingEngine

router = APIRouter(prefix="/api/blockchain", tags=["Blockchain"])
logger = logging.getLogger(__name__)


# ── GET /predictions/{match_id} ────────────────────────────────────────

@router.get("/predictions/{match_id}")
async def get_consensus_prediction(
    match_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConsensusPrediction).where(ConsensusPrediction.match_id == match_id)
    )
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(404, "No consensus prediction for this match")
    return {
        "match_id": match_id,
        "status": cp.status,
        "ai": {
            "p_home": float(cp.ai_p_home),
            "p_draw": float(cp.ai_p_draw),
            "p_away": float(cp.ai_p_away),
            "confidence": float(cp.ai_confidence),
            "risk": float(cp.ai_risk),
        },
        "validators": {
            "count": cp.validator_count,
            "total_influence": float(cp.total_influence),
            "consensus_p_home": float(cp.consensus_p_home),
            "consensus_p_draw": float(cp.consensus_p_draw),
            "consensus_p_away": float(cp.consensus_p_away),
        },
        "final": {
            "p_home": float(cp.final_p_home),
            "p_draw": float(cp.final_p_draw),
            "p_away": float(cp.final_p_away),
        },
        "published_at": cp.published_at.isoformat(),
        "settled_at": cp.settled_at.isoformat() if cp.settled_at else None,
    }


# ── POST /predictions/{match_id}/stake ────────────────────────────────

class StakeRequest(BaseModel):
    # v4.11.0: extend stake markets beyond 1X2 to also support over/under 2.5
    # and BTTS yes/no, mirroring the markets exposed in the frontend match-detail
    # and PredictionFlow components.
    prediction: str = Field(
        ...,
        pattern="^(home|draw|away|over_25|under_25|btts_yes|btts_no)$",
    )
    amount: float = Field(..., gt=0)


@router.post("/predictions/{match_id}/stake")
async def stake_on_prediction(
    match_id: str,
    body: StakeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cp_res = await db.execute(
        select(ConsensusPrediction).where(ConsensusPrediction.match_id == match_id)
    )
    cp = cp_res.scalar_one_or_none()
    if not cp or cp.status not in (ConsensusStatus.OPEN.value,):
        raise HTTPException(400, "Match is not open for staking")

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        raise HTTPException(400, "No wallet found — please create one first")

    amount = Decimal(str(body.amount))
    if wallet.vitcoin_balance < amount:
        raise HTTPException(400, "Insufficient VITCoin balance")
    if wallet.is_frozen:
        raise HTTPException(403, "Wallet is frozen")

    wallet.vitcoin_balance -= amount
    stake = UserStake(
        user_id=current_user.id,
        match_id=match_id,
        prediction=body.prediction,
        stake_amount=amount,
        currency="VITCoin",
        status=StakeStatus.ACTIVE.value,
    )
    db.add(stake)
    await db.commit()
    await db.refresh(stake)

    return {
        "stake_id": stake.id,
        "match_id": match_id,
        "prediction": body.prediction,
        "amount": float(amount),
        "vitcoin_balance": float(wallet.vitcoin_balance),
    }


# ── GET /stakes/my ─────────────────────────────────────────────────────

@router.get("/stakes/my")
async def my_stakes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserStake)
        .where(UserStake.user_id == current_user.id)
        .order_by(UserStake.created_at.desc())
    )
    stakes = result.scalars().all()
    return [
        {
            "id": s.id,
            "match_id": s.match_id,
            "prediction": s.prediction,
            "stake_amount": float(s.stake_amount),
            "status": s.status,
            "payout_amount": float(s.payout_amount),
            "created_at": s.created_at.isoformat(),
        }
        for s in stakes
    ]


# ── GET /validators ────────────────────────────────────────────────────

@router.get("/validators")
async def list_validators(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ValidatorProfile, User)
        .join(User, ValidatorProfile.user_id == User.id)
        .where(ValidatorProfile.status == ValidatorStatus.ACTIVE.value)
        .order_by(ValidatorProfile.trust_score.desc())
    )
    rows = result.all()
    return [
        {
            "username": user.username,
            "trust_score": float(vp.trust_score),
            "stake": float(vp.stake_amount),
            "total_predictions": vp.total_predictions,
            "accuracy_rate": (
                round(vp.accurate_predictions / vp.total_predictions, 4)
                if vp.total_predictions > 0 else 0.0
            ),
            "influence_score": float(vp.influence_score),
            "joined_at": vp.joined_at.isoformat(),
        }
        for vp, user in rows
    ]


# ── POST /validators/apply ─────────────────────────────────────────────

class ValidatorApplyRequest(BaseModel):
    stake_amount: float = Field(..., gt=0)


@router.post("/validators/apply")
async def apply_as_validator(
    body: ValidatorApplyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in ("analyst", "admin", "validator"):
        raise HTTPException(403, "Analyst role or higher required to become a validator")

    existing = await db.execute(
        select(ValidatorProfile).where(ValidatorProfile.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Already applied or registered as validator")

    wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_res.scalar_one_or_none()
    if not wallet:
        raise HTTPException(400, "No wallet found")

    amount = Decimal(str(body.stake_amount))
    if wallet.vitcoin_balance < amount:
        raise HTTPException(400, "Insufficient VITCoin balance to stake")

    wallet.vitcoin_balance -= amount

    vp = ValidatorProfile(
        user_id=current_user.id,
        stake_amount=amount,
        trust_score=Decimal("0.5"),
        influence_score=amount * Decimal("0.5"),
        status=ValidatorStatus.PENDING.value,
    )
    db.add(vp)
    await db.commit()
    await db.refresh(vp)

    return {
        "validator_id": vp.id,
        "status": vp.status,
        "stake_amount": float(vp.stake_amount),
        "trust_score": float(vp.trust_score),
        "message": "Application submitted — pending admin review",
    }


# ── POST /validators/predict ───────────────────────────────────────────

class ValidatorPredictRequest(BaseModel):
    match_id: str
    p_home: float = Field(..., ge=0, le=1)
    p_draw: float = Field(..., ge=0, le=1)
    p_away: float = Field(..., ge=0, le=1)
    confidence: float = Field(0.5, ge=0, le=1)


@router.post("/validators/predict")
async def submit_validator_prediction(
    body: ValidatorPredictRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vp_res = await db.execute(
        select(ValidatorProfile).where(ValidatorProfile.user_id == current_user.id)
    )
    vp = vp_res.scalar_one_or_none()
    if not vp or vp.status != ValidatorStatus.ACTIVE.value:
        raise HTTPException(403, "Active validator profile required")

    existing = await db.execute(
        select(ValidatorPrediction).where(
            ValidatorPrediction.validator_id == vp.id,
            ValidatorPrediction.match_id == body.match_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Already submitted prediction for this match")

    total = body.p_home + body.p_draw + body.p_away
    if not (0.98 <= total <= 1.02):
        raise HTTPException(400, "Probabilities must sum to approximately 1.0")

    norm = total
    pred = ValidatorPrediction(
        validator_id=vp.id,
        match_id=body.match_id,
        p_home=Decimal(str(body.p_home / norm)),
        p_draw=Decimal(str(body.p_draw / norm)),
        p_away=Decimal(str(body.p_away / norm)),
        confidence=Decimal(str(body.confidence)),
    )
    db.add(pred)
    await db.flush()

    cp = await calculate_consensus(body.match_id, db)
    await db.commit()

    return {
        "prediction_id": pred.id,
        "match_id": body.match_id,
        "p_home": float(pred.p_home),
        "p_draw": float(pred.p_draw),
        "p_away": float(pred.p_away),
        "consensus_updated": True,
        "new_final": {
            "p_home": float(cp.final_p_home),
            "p_draw": float(cp.final_p_draw),
            "p_away": float(cp.final_p_away),
        },
    }


# ── GET /validators/my ────────────────────────────────────────────────

@router.get("/validators/my")
async def my_validator_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    vp_res = await db.execute(
        select(ValidatorProfile).where(ValidatorProfile.user_id == current_user.id)
    )
    vp = vp_res.scalar_one_or_none()
    if not vp:
        raise HTTPException(404, "No validator profile found")

    preds_res = await db.execute(
        select(ValidatorPrediction)
        .where(ValidatorPrediction.validator_id == vp.id)
        .order_by(ValidatorPrediction.submitted_at.desc())
        .limit(50)
    )
    preds = preds_res.scalars().all()
    total_rewards = sum(p.reward_earned for p in preds)

    return {
        "id": vp.id,
        "status": vp.status,
        "stake_amount": float(vp.stake_amount),
        "trust_score": float(vp.trust_score),
        "influence_score": float(vp.influence_score),
        "total_predictions": vp.total_predictions,
        "accurate_predictions": vp.accurate_predictions,
        "accuracy_rate": (
            round(vp.accurate_predictions / vp.total_predictions, 4)
            if vp.total_predictions > 0 else 0.0
        ),
        "total_rewards_earned": float(total_rewards),
        "joined_at": vp.joined_at.isoformat(),
        "recent_predictions": [
            {
                "match_id": p.match_id,
                "p_home": float(p.p_home),
                "p_draw": float(p.p_draw),
                "p_away": float(p.p_away),
                "result": p.result,
                "reward_earned": float(p.reward_earned),
                "submitted_at": p.submitted_at.isoformat(),
            }
            for p in preds
        ],
    }


# ── GET /economy ───────────────────────────────────────────────────────

@router.get("/economy")
async def economy_dashboard(db: AsyncSession = Depends(get_db)):
    validator_count = (
        await db.execute(
            select(func.count(ValidatorProfile.id)).where(
                ValidatorProfile.status == ValidatorStatus.ACTIVE.value
            )
        )
    ).scalar() or 0

    total_staked = (
        await db.execute(select(func.sum(ValidatorProfile.stake_amount)))
    ).scalar() or Decimal("0")

    matches_settled = (
        await db.execute(select(func.count(MatchSettlement.id)))
    ).scalar() or 0

    total_rewards = (
        await db.execute(
            select(func.sum(UserStake.payout_amount)).where(
                UserStake.status == StakeStatus.WON.value
            )
        )
    ).scalar() or Decimal("0")

    total_burned = (
        await db.execute(select(func.sum(MatchSettlement.burn_amount)))
    ).scalar() or Decimal("0")

    pricing = VITCoinPricingEngine(db)
    prices = await pricing.get_current_price()
    circulating_supply = await pricing.get_circulating_supply()

    return {
        "active_validators": validator_count,
        "total_staked_vitcoin": float(total_staked),
        "matches_settled": matches_settled,
        "total_rewards_distributed": float(total_rewards),
        "vitcoin_burned": float(total_burned),
        "vitcoin_price_usd": float(prices["usd"]),
        "vitcoin_price_ngn": float(prices["ngn"]),
        "circulating_supply": float(circulating_supply),
    }
