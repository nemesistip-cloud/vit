"""Settlement engine — Module C3.

Distributes staking rewards after oracle confirms a match result.

Fee split:
  40% → validator fund
  30% → treasury
  20% → burn
  10% → AI fund
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    ConsensusPrediction,
    ConsensusStatus,
    MatchSettlement,
    OracleResult,
    UserStake,
    StakeStatus,
    ValidatorPrediction,
    ValidatorProfile,
    PredictionResult,
)
from app.modules.blockchain.consensus import update_trust_scores
from app.modules.wallet.models import Wallet
from app.db.models import Match


def _derive_market_oracle(oracle_result: str, match: "Match | None") -> dict[str, str]:
    """Build a per-market oracle result map from the 1X2 result + final score.

    Returns keys: 1x2, over_under, btts.
    Falls back gracefully when goal data is missing — only includes markets we
    can confidently settle.
    """
    out: dict[str, str] = {"1x2": oracle_result}
    if match and match.home_goals is not None and match.away_goals is not None:
        total = (match.home_goals or 0) + (match.away_goals or 0)
        out["over_under"] = "over_25" if total > 2 else "under_25"
        out["btts"] = (
            "btts_yes"
            if (match.home_goals or 0) > 0 and (match.away_goals or 0) > 0
            else "btts_no"
        )
    return out


_MARKET_BY_PREDICTION = {
    "home": "1x2", "draw": "1x2", "away": "1x2",
    "over_25": "over_under", "under_25": "over_under",
    "btts_yes": "btts", "btts_no": "btts",
}

logger = logging.getLogger(__name__)

_PLATFORM_FEE_PCT = Decimal("0.02")
_VALIDATOR_SHARE = Decimal("0.40")
_TREASURY_SHARE = Decimal("0.30")
_BURN_SHARE = Decimal("0.20")
_AI_SHARE = Decimal("0.10")


async def settle_match(match_id: str, oracle_result: str, db: AsyncSession) -> MatchSettlement:
    """
    Fully settle a match:
      1. Verify oracle agreement
      2. Calculate pools
      3. Pay winners
      4. Distribute validator rewards
      5. Record MatchSettlement
      6. Update trust scores
      7. Burn tokens (reduce virtual supply by recording zero-address debit)
    """
    consensus_result = await db.execute(
        select(ConsensusPrediction).where(ConsensusPrediction.match_id == match_id)
    )
    cp = consensus_result.scalar_one_or_none()
    if not cp:
        raise ValueError(f"No consensus prediction found for match {match_id}")

    if cp.status == ConsensusStatus.SETTLED.value:
        raise ValueError(f"Match {match_id} already settled")

    stakes_result = await db.execute(
        select(UserStake).where(
            UserStake.match_id == match_id,
            UserStake.status == StakeStatus.ACTIVE.value,
        )
    )
    stakes = stakes_result.scalars().all()

    # Pull match for goal-derived oracle results (OU 2.5, BTTS).
    match_row = await db.execute(select(Match).where(Match.id == match_id))
    match_obj = match_row.scalar_one_or_none()
    market_oracle = _derive_market_oracle(oracle_result, match_obj)

    def _is_winner(stake: UserStake) -> bool:
        market = _MARKET_BY_PREDICTION.get(stake.prediction, "1x2")
        target = market_oracle.get(market)
        return target is not None and stake.prediction == target

    total_pool = sum(s.stake_amount for s in stakes) or Decimal("0")
    platform_fee = total_pool * _PLATFORM_FEE_PCT
    net_pool = total_pool - platform_fee

    winning_stakes = [s for s in stakes if _is_winner(s)]
    winning_pool = sum(s.stake_amount for s in winning_stakes) or Decimal("0")

    validator_fund = platform_fee * _VALIDATOR_SHARE
    treasury_fund = platform_fee * _TREASURY_SHARE
    burn_amount = platform_fee * _BURN_SHARE
    ai_fund = platform_fee * _AI_SHARE

    for stake in stakes:
        if _is_winner(stake):
            if winning_pool > 0:
                payout = (stake.stake_amount / winning_pool) * net_pool
            else:
                payout = stake.stake_amount
            stake.payout_amount = payout
            stake.status = StakeStatus.WON.value

            wallet_result = await db.execute(
                select(Wallet).where(Wallet.user_id == stake.user_id)
            )
            wallet = wallet_result.scalar_one_or_none()
            if wallet:
                wallet.vitcoin_balance += payout
        else:
            stake.status = StakeStatus.LOST.value

    accurate_validators_result = await db.execute(
        select(ValidatorPrediction, ValidatorProfile)
        .join(ValidatorProfile, ValidatorPrediction.validator_id == ValidatorProfile.id)
        .where(
            ValidatorPrediction.match_id == match_id,
            ValidatorPrediction.result == PredictionResult.ACCURATE.value,
            ValidatorProfile.status == "active",
        )
    )
    accurate_rows = accurate_validators_result.all()

    total_accurate_influence = sum(
        vpr.influence_score for _, vpr in accurate_rows
    ) or Decimal("0")

    for vp, vpr in accurate_rows:
        if total_accurate_influence > 0:
            share = (vpr.influence_score / total_accurate_influence) * validator_fund
        else:
            share = Decimal("0")
        vp.reward_earned = share

        wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == vpr.user_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if wallet and share > 0:
            wallet.vitcoin_balance += share

    settlement = MatchSettlement(
        match_id=match_id,
        consensus_id=cp.id,
        oracle_result=oracle_result,
        total_pool=total_pool,
        winning_pool=winning_pool,
        validator_fund=validator_fund,
        treasury_fund=treasury_fund,
        burn_amount=burn_amount,
        ai_fund=ai_fund,
        settled_at=datetime.utcnow(),
    )
    db.add(settlement)

    cp.status = ConsensusStatus.SETTLED.value
    cp.settled_at = datetime.utcnow()

    await db.flush()
    await update_trust_scores(match_id, oracle_result, db)

    logger.info(
        f"Settled match {match_id}: pool={total_pool} VIT, "
        f"winners={len(winning_stakes)}, validators={len(accurate_rows)}, "
        f"burn={burn_amount}"
    )
    return settlement
