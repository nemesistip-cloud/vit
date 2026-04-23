"""Settlement engine — Module C3.

Distributes staking rewards after oracle confirms a match result.

Fee split:
  40% → validator fund
  30% → treasury
  20% → burn
  10% → AI fund
"""

import logging
from datetime import datetime, timezone
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
from app.modules.wallet.models import Currency, TransactionType, Wallet
from app.modules.wallet.services import WalletService
from app.modules.notifications.service import NotificationService
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

    def _market_resolvable(stake: UserStake) -> bool:
        market = _MARKET_BY_PREDICTION.get(stake.prediction, "1x2")
        return market_oracle.get(market) is not None

    def _is_winner(stake: UserStake) -> bool:
        market = _MARKET_BY_PREDICTION.get(stake.prediction, "1x2")
        target = market_oracle.get(market)
        return target is not None and stake.prediction == target

    # Refundable stakes (oracle data missing for that market) come out of the pool
    refundable_stakes = [s for s in stakes if not _market_resolvable(s)]
    settled_stakes = [s for s in stakes if _market_resolvable(s)]

    total_pool = sum(s.stake_amount for s in settled_stakes) or Decimal("0")
    platform_fee = total_pool * _PLATFORM_FEE_PCT
    net_pool = total_pool - platform_fee

    winning_stakes = [s for s in settled_stakes if _is_winner(s)]
    winning_pool = sum(s.stake_amount for s in winning_stakes) or Decimal("0")

    validator_fund = platform_fee * _VALIDATOR_SHARE
    treasury_fund = platform_fee * _TREASURY_SHARE
    burn_amount = platform_fee * _BURN_SHARE
    ai_fund = platform_fee * _AI_SHARE

    # Batch-load all involved wallets up front (fixes N+1)
    user_ids = list({s.user_id for s in stakes})
    wallets_by_user: dict[int, Wallet] = {}
    if user_ids:
        wres = await db.execute(select(Wallet).where(Wallet.user_id.in_(user_ids)))
        for w in wres.scalars().all():
            wallets_by_user[w.user_id] = w

    ws = WalletService(db)
    settle_notifications: list[tuple[int, str, str]] = []  # (user_id, title, body)

    for stake in stakes:
        wallet = wallets_by_user.get(stake.user_id)
        if not _market_resolvable(stake):
            # Refund — oracle could not resolve this market
            stake.status = StakeStatus.REFUNDED.value
            stake.payout_amount = stake.stake_amount
            if wallet and stake.stake_amount > 0:
                try:
                    await ws.credit(
                        wallet_id=wallet.id, user_id=stake.user_id,
                        currency=Currency.VITCOIN, amount=stake.stake_amount,
                        tx_type=TransactionType.REWARD.value,
                        reference=f"stake-refund:{stake.id}",
                        metadata={"match_id": match_id, "reason": "oracle_unresolvable", "market": _MARKET_BY_PREDICTION.get(stake.prediction, "1x2")},
                    )
                except ValueError as e:
                    logger.warning(f"Refund failed for stake {stake.id}: {e}")
            settle_notifications.append((
                stake.user_id, "Stake Refunded",
                f"Your {float(stake.stake_amount):.2f} VIT stake on match {match_id} was refunded — outcome could not be resolved.",
            ))
        elif _is_winner(stake):
            if winning_pool > 0:
                payout = (stake.stake_amount / winning_pool) * net_pool
            else:
                payout = stake.stake_amount
            stake.payout_amount = payout
            stake.status = StakeStatus.WON.value
            if wallet and payout > 0:
                try:
                    await ws.credit(
                        wallet_id=wallet.id, user_id=stake.user_id,
                        currency=Currency.VITCOIN, amount=payout,
                        tx_type=TransactionType.REWARD.value,
                        reference=f"stake-win:{stake.id}",
                        metadata={"match_id": match_id, "stake_amount": float(stake.stake_amount), "prediction": stake.prediction},
                    )
                except ValueError as e:
                    logger.warning(f"Payout failed for stake {stake.id}: {e}")
            pnl = payout - stake.stake_amount
            settle_notifications.append((
                stake.user_id, "Stake Won",
                f"Your {stake.prediction.upper()} stake on match {match_id} won! Payout: {float(payout):.2f} VIT (P&L: {'+' if pnl >= 0 else ''}{float(pnl):.2f} VIT).",
            ))
        else:
            stake.status = StakeStatus.LOST.value
            stake.payout_amount = Decimal("0")
            settle_notifications.append((
                stake.user_id, "Stake Lost",
                f"Your {stake.prediction.upper()} stake of {float(stake.stake_amount):.2f} VIT on match {match_id} did not win.",
            ))

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

    # Batch-load validator wallets too
    val_user_ids = list({vpr.user_id for _, vpr in accurate_rows})
    val_wallets: dict[int, Wallet] = {}
    if val_user_ids:
        wres = await db.execute(select(Wallet).where(Wallet.user_id.in_(val_user_ids)))
        for w in wres.scalars().all():
            val_wallets[w.user_id] = w

    for vp, vpr in accurate_rows:
        if total_accurate_influence > 0:
            share = (vpr.influence_score / total_accurate_influence) * validator_fund
        else:
            share = Decimal("0")
        # Accumulate lifetime rewards (was overwriting before)
        vp.reward_earned = (vp.reward_earned or Decimal("0")) + share

        wallet = val_wallets.get(vpr.user_id)
        if wallet and share > 0:
            try:
                await ws.credit(
                    wallet_id=wallet.id, user_id=vpr.user_id,
                    currency=Currency.VITCOIN, amount=share,
                    tx_type=TransactionType.REWARD.value,
                    reference=f"validator-reward:{match_id}:{vp.id}",
                    metadata={"match_id": match_id, "validator_id": vp.id, "influence_score": float(vpr.influence_score)},
                )
            except ValueError as e:
                logger.warning(f"Validator reward failed for vp {vp.id}: {e}")

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
        settled_at=datetime.now(timezone.utc),
    )
    db.add(settlement)

    cp.status = ConsensusStatus.SETTLED.value
    cp.settled_at = datetime.now(timezone.utc)

    await db.flush()
    await update_trust_scores(match_id, oracle_result, db)

    # Dispatch per-stake settlement notifications (after all financial state is flushed).
    # NotificationService.create commits internally; that is safe here because by this
    # point every wallet credit + stake status update is already persisted via flush().
    from app.modules.notifications.models import NotificationType
    for uid, title, body in settle_notifications:
        try:
            await NotificationService.create(
                db, uid, NotificationType.MATCH_RESULT,
                {"match": match_id, "outcome": title.lower().replace("stake ", "")},
                title=title, body=body,
            )
        except Exception as e:
            logger.warning(f"Stake-settle notification failed for user {uid}: {e}")

    logger.info(
        f"Settled match {match_id}: pool={total_pool} VIT, "
        f"winners={len(winning_stakes)}, refunds={len(refundable_stakes)}, "
        f"validators={len(accurate_rows)}, burn={burn_amount}"
    )
    return settlement
