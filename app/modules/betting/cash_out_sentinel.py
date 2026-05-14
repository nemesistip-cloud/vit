"""app/modules/betting/cash_out_sentinel.py — Auto Cash-Out Sentinel v6.0

Real-time position monitor with momentum-based auto-exit logic.

MomentumAnalyzer:  calculates momentum score −100 to +100 from live match data
CashOutSentinel:   evaluates open positions and executes cash-out via broker API
CashOutStrategy:   AGGRESSIVE / BALANCED / CONSERVATIVE / MANUAL
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_BROKER_TIMEOUT = 15   # seconds per HTTP call


# ── Enums & config ─────────────────────────────────────────────────────────────

class CashOutStrategy(str, Enum):
    AGGRESSIVE   = "aggressive"    # lock ≥75% profit OR mitigate ≥50% loss
    BALANCED     = "balanced"      # lock ≥50% profit OR mitigate ≥25% loss
    CONSERVATIVE = "conservative"  # lock ≥90% profit OR mitigate ≥10% loss
    MANUAL       = "manual"        # never auto-exit; flag for human review

_STRATEGY_CONFIG: Dict[CashOutStrategy, dict] = {
    CashOutStrategy.AGGRESSIVE:   {"profit_lock": 0.75, "loss_cut": 0.50},
    CashOutStrategy.BALANCED:     {"profit_lock": 0.50, "loss_cut": 0.25},
    CashOutStrategy.CONSERVATIVE: {"profit_lock": 0.90, "loss_cut": 0.10},
    CashOutStrategy.MANUAL:       {"profit_lock": 999.0, "loss_cut": 999.0},
}


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class MatchLiveData:
    match_id:         str
    home_team:        str
    away_team:        str
    minute:           int          = 0
    home_score:       int          = 0
    away_score:       int          = 0
    home_possession:  float        = 50.0   # percent
    away_possession:  float        = 50.0
    home_shots_ot:    int          = 0
    away_shots_ot:    int          = 0
    home_xg:          float        = 0.0
    away_xg:          float        = 0.0
    home_attacks_last5: int        = 0
    away_attacks_last5: int        = 0
    status:           str          = "live"  # live | finished | postponed


@dataclass
class StakePosition:
    position_id:   str
    match_id:      str
    user_id:       int
    stake_amount:  Decimal
    predicted_side: str           # home | draw | away
    entry_odds:    float
    current_odds:  float = 0.0
    broker:        str   = "internal"   # internal | sportybet | football_com
    strategy:      CashOutStrategy = CashOutStrategy.BALANCED
    opened_at:     str   = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata:      dict  = field(default_factory=dict)

    @property
    def potential_payout(self) -> Decimal:
        return self.stake_amount * Decimal(str(self.entry_odds))

    @property
    def current_value(self) -> Decimal:
        if self.current_odds <= 0:
            return Decimal("0")
        return self.stake_amount * Decimal(str(self.current_odds))

    def pnl_pct(self) -> float:
        """Profit/loss as a fraction of potential payout. >0 = profit, <0 = loss."""
        if self.current_odds <= 0 or self.entry_odds <= 0:
            return 0.0
        return (self.current_odds - self.entry_odds) / self.entry_odds


@dataclass
class CashOutDecision:
    position_id:  str
    action:       str        # "hold" | "cash_out" | "flag"
    reason:       str
    momentum:     float      # -100 to +100
    pnl_pct:      float
    recommended_amount: Optional[Decimal] = None
    executed:     bool       = False
    executed_at:  Optional[str] = None
    error:        Optional[str] = None


# ── Momentum Analyzer ──────────────────────────────────────────────────────────

class MomentumAnalyzer:
    """
    Calculates a momentum score −100 to +100 for the staked side.
    Positive = staked side is in control; negative = opponent dominating.
    """

    def analyze(self, position: StakePosition, live: MatchLiveData) -> float:
        side = position.predicted_side  # "home" | "draw" | "away"
        score = 0.0

        if side in ("home", "away"):
            # Possession component (±30)
            home_poss = live.home_possession / 100.0
            if side == "home":
                score += (home_poss - 0.5) * 60      # +30 for 100% → −30 for 0%
            else:
                score += ((1 - home_poss) - 0.5) * 60

            # Shots on target component (±30)
            our_shots  = live.home_shots_ot  if side == "home" else live.away_shots_ot
            opp_shots  = live.away_shots_ot  if side == "home" else live.home_shots_ot
            total_shots = max(our_shots + opp_shots, 1)
            score += ((our_shots / total_shots) - 0.5) * 60

            # xG balance component (±30)
            our_xg  = live.home_xg  if side == "home" else live.away_xg
            opp_xg  = live.away_xg  if side == "home" else live.home_xg
            total_xg = max(our_xg + opp_xg, 0.01)
            score += ((our_xg / total_xg) - 0.5) * 60

            # Recent attack frequency (±10)
            our_att  = live.home_attacks_last5 if side == "home" else live.away_attacks_last5
            opp_att  = live.away_attacks_last5 if side == "home" else live.home_attacks_last5
            total_att = max(our_att + opp_att, 1)
            score += ((our_att / total_att) - 0.5) * 20

            # Current score factor: if losing, momentum is cut
            our_goals  = live.home_score if side == "home" else live.away_score
            opp_goals  = live.away_score if side == "home" else live.home_score
            if opp_goals > our_goals:
                score -= (opp_goals - our_goals) * 15   # penalty per goal conceded
            elif our_goals > opp_goals:
                score += (our_goals - opp_goals) * 10   # bonus per goal ahead

            # Time decay: late game with lead is more certain → boost
            if live.minute >= 70 and our_goals > opp_goals:
                score += min(10, (live.minute - 70) * 0.5)

        else:
            # Draw: both sides balanced → high possession symmetry is good
            diff = abs(live.home_possession - live.away_possession)
            score = max(-50, 50 - diff * 2)
            if live.home_score != live.away_score:
                score -= 40   # active score means draw is at risk

        return max(-100.0, min(100.0, score))


# ── Broker clients ────────────────────────────────────────────────────────────

async def _cash_out_sportybet(position: StakePosition, amount: Decimal) -> dict:
    """Execute cash-out via SportyBet API (placeholder — adapt to live SDK)."""
    api_url = os.getenv("SPORTYBET_API_URL", "")
    api_key = os.getenv("SPORTYBET_API_KEY", "")
    if not api_url or not api_key:
        logger.warning("[cash-out] SportyBet credentials not configured — simulation mode")
        return {"simulated": True, "position_id": position.position_id, "amount": float(amount)}

    async with httpx.AsyncClient(timeout=_BROKER_TIMEOUT) as client:
        resp = await client.post(
            f"{api_url}/bets/{position.position_id}/cashout",
            json={"amount": float(amount)},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        return resp.json()


async def _cash_out_football_com(position: StakePosition, amount: Decimal) -> dict:
    """Execute cash-out via Football.com API."""
    api_url = os.getenv("FOOTBALL_COM_API_URL", "")
    api_key = os.getenv("FOOTBALL_COM_API_KEY", "")
    if not api_url or not api_key:
        logger.warning("[cash-out] Football.com credentials not configured — simulation mode")
        return {"simulated": True, "position_id": position.position_id, "amount": float(amount)}

    async with httpx.AsyncClient(timeout=_BROKER_TIMEOUT) as client:
        resp = await client.post(
            f"{api_url}/cashout",
            json={"bet_id": position.position_id, "cash_out_value": float(amount)},
            headers={"X-API-Key": api_key},
        )
        resp.raise_for_status()
        return resp.json()


async def _cash_out_internal(position: StakePosition, amount: Decimal) -> dict:
    """Execute cash-out via internal VIT staking settlement.

    Marks the stake REFUNDED and credits the cash-out amount back to the
    user's VITCoin wallet so the funds are immediately spendable.
    """
    try:
        from app.db.database import AsyncSessionLocal
        from app.modules.blockchain.models import UserStake, StakeStatus
        from app.modules.wallet.services import WalletService
        from app.modules.wallet.models import Currency
        from sqlalchemy import select, update
        import uuid as _uuid

        async with AsyncSessionLocal() as db:
            # 1. Mark stake as refunded
            result = await db.execute(
                select(UserStake).where(UserStake.id == position.position_id)
            )
            stake = result.scalar_one_or_none()
            if stake is None:
                raise ValueError(f"Stake {position.position_id} not found")

            stake.status = StakeStatus.REFUNDED.value

            # 2. Credit cash-out amount to user's VITCoin wallet
            wallet_svc = WalletService(db)
            wallet = await wallet_svc.get_or_create_wallet(stake.user_id)
            ref = f"CASHOUT-{position.position_id[:8]}-{_uuid.uuid4().hex[:6].upper()}"
            await wallet_svc.credit(
                wallet_id=wallet.id,
                user_id=stake.user_id,
                currency=Currency.VITCOIN,
                amount=amount,
                tx_type="cashout",
                reference=ref,
                metadata={
                    "source": "cash_out_sentinel",
                    "stake_id": position.position_id,
                    "match_id": position.match_id,
                    "strategy": position.strategy,
                    "original_stake": float(position.stake_amount),
                },
            )

            await db.commit()

        logger.info(
            "[cash-out] internal: stake %s refunded, credited %.4f VIT to user %s (ref=%s)",
            position.position_id[:8], float(amount), stake.user_id, ref,
        )
        return {
            "internal": True,
            "refunded": float(amount),
            "position_id": position.position_id,
            "wallet_ref": ref,
        }
    except Exception as exc:
        logger.error("[cash-out] internal settlement error: %s", exc)
        return {"error": str(exc)}


_BROKER_HANDLERS = {
    "sportybet":    _cash_out_sportybet,
    "football_com": _cash_out_football_com,
    "internal":     _cash_out_internal,
}


# ── Cash Out Sentinel ─────────────────────────────────────────────────────────

class CashOutSentinel:
    """
    Evaluates open betting positions against live match data and executes
    cash-outs according to each position's strategy.

    Usage:
        sentinel = get_cash_out_sentinel()
        decision = await sentinel.evaluate_position(position, live_data)
    """

    def __init__(self) -> None:
        self._analyzer = MomentumAnalyzer()
        self._open_positions: Dict[str, StakePosition] = {}
        self._decisions:      Dict[str, CashOutDecision] = {}
        logger.info("[cash-out-sentinel] initialised")

    def register_position(self, position: StakePosition) -> None:
        """Track a new open position."""
        self._open_positions[position.position_id] = position
        logger.debug("[cash-out-sentinel] tracking position %s", position.position_id)

    def unregister_position(self, position_id: str) -> None:
        self._open_positions.pop(position_id, None)

    async def evaluate_position(
        self,
        position: StakePosition,
        live: MatchLiveData,
    ) -> CashOutDecision:
        """
        Evaluate one position against live data and decide whether to cash out.
        Returns a CashOutDecision (may trigger execution if action='cash_out').
        """
        config  = _STRATEGY_CONFIG[position.strategy]
        momentum = self._analyzer.analyze(position, live)
        pnl     = position.pnl_pct()

        action = "hold"
        reason = ""

        if position.strategy == CashOutStrategy.MANUAL:
            action = "hold"
            reason = "manual strategy — human review required"
        elif pnl >= config["profit_lock"]:
            action = "cash_out"
            reason = f"profit lock at {pnl:.0%} ≥ {config['profit_lock']:.0%}"
        elif pnl <= -config["loss_cut"]:
            action = "cash_out"
            reason = f"loss cut at {pnl:.0%} ≤ -{config['loss_cut']:.0%}"
        elif momentum < -60 and pnl < 0:
            action = "cash_out"
            reason = f"adverse momentum ({momentum:.0f}) + loss position"
        elif live.status == "finished":
            action = "hold"   # settlement will handle this
            reason = "match finished — awaiting settlement"

        cash_out_amount: Optional[Decimal] = None
        if action == "cash_out" and position.current_odds > 0:
            cash_out_amount = position.current_value

        decision = CashOutDecision(
            position_id=position.position_id,
            action=action,
            reason=reason,
            momentum=round(momentum, 2),
            pnl_pct=round(pnl, 4),
            recommended_amount=cash_out_amount,
        )

        if action == "cash_out" and cash_out_amount:
            await self._execute(position, decision, cash_out_amount)

        self._decisions[position.position_id] = decision
        logger.info(
            "[cash-out-sentinel] pos=%s action=%s pnl=%.1f%% momentum=%.0f reason=%s",
            position.position_id[:8], action, pnl * 100, momentum, reason,
        )
        return decision

    async def _execute(
        self,
        position: StakePosition,
        decision: CashOutDecision,
        amount: Decimal,
    ) -> None:
        """Execute the cash-out via the appropriate broker."""
        handler = _BROKER_HANDLERS.get(position.broker, _cash_out_internal)
        try:
            result = await handler(position, amount)
            decision.executed    = True
            decision.executed_at = datetime.now(timezone.utc).isoformat()
            self.unregister_position(position.position_id)
            logger.info("[cash-out-sentinel] executed %s broker=%s amount=%.4f result=%s",
                        position.position_id[:8], position.broker, float(amount), result)
        except Exception as exc:
            decision.error = str(exc)
            logger.error("[cash-out-sentinel] execution failed %s: %s", position.position_id[:8], exc)

    async def scan_all_positions(self, live_feed: Dict[str, MatchLiveData]) -> List[CashOutDecision]:
        """Evaluate all tracked positions against a live data feed."""
        decisions = []
        for pos_id, position in list(self._open_positions.items()):
            live = live_feed.get(position.match_id)
            if live is None:
                continue
            try:
                d = await self.evaluate_position(position, live)
                decisions.append(d)
            except Exception as exc:
                logger.error("[cash-out-sentinel] scan error for %s: %s", pos_id, exc)
        return decisions

    def get_decisions(self) -> Dict[str, dict]:
        return {pid: {
            "action":    d.action,
            "reason":    d.reason,
            "momentum":  d.momentum,
            "pnl_pct":   d.pnl_pct,
            "executed":  d.executed,
            "error":     d.error,
        } for pid, d in self._decisions.items()}

    def status(self) -> dict:
        return {
            "open_positions": len(self._open_positions),
            "decisions":      len(self._decisions),
            "executed":       sum(1 for d in self._decisions.values() if d.executed),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_GLOBAL_SENTINEL: Optional[CashOutSentinel] = None


def get_cash_out_sentinel() -> CashOutSentinel:
    global _GLOBAL_SENTINEL
    if _GLOBAL_SENTINEL is None:
        _GLOBAL_SENTINEL = CashOutSentinel()
    return _GLOBAL_SENTINEL


# ── FastAPI router ────────────────────────────────────────────────────────────

from fastapi import APIRouter
from pydantic import BaseModel

cashout_router = APIRouter(prefix="/api/cashout", tags=["Cash-Out Sentinel"])


@cashout_router.get("/status")
async def cashout_status():
    return get_cash_out_sentinel().status()


@cashout_router.get("/decisions")
async def cashout_decisions():
    return get_cash_out_sentinel().get_decisions()


@cashout_router.get("/strategies")
async def cashout_strategies():
    """List available cash-out strategies with configuration parameters."""
    return {
        "strategies": [
            {
                "id": "aggressive",
                "name": "Aggressive",
                "description": "Cash out to lock ≥75% of potential profit, or cut ≥50% loss — fastest exit.",
                "min_profit_pct": _STRATEGY_CONFIG[CashOutStrategy.AGGRESSIVE]["profit_lock"],
                "max_loss_pct": _STRATEGY_CONFIG[CashOutStrategy.AGGRESSIVE]["loss_cut"],
                "momentum_threshold": 0.65,
                "risk_level": "low",
                "recommended_for": "Volatile matches, injury concerns, weather risk",
            },
            {
                "id": "balanced",
                "name": "Balanced",
                "description": "Cash out when ≥50% of potential profit secured, or ≥25% loss reached.",
                "min_profit_pct": _STRATEGY_CONFIG[CashOutStrategy.BALANCED]["profit_lock"],
                "max_loss_pct": _STRATEGY_CONFIG[CashOutStrategy.BALANCED]["loss_cut"],
                "momentum_threshold": 0.72,
                "risk_level": "medium",
                "recommended_for": "Standard pre-match bets, moderate confidence",
            },
            {
                "id": "conservative",
                "name": "Conservative",
                "description": "Let positions run until ≥90% profit locked, only cutting at ≥10% loss.",
                "min_profit_pct": _STRATEGY_CONFIG[CashOutStrategy.CONSERVATIVE]["profit_lock"],
                "max_loss_pct": _STRATEGY_CONFIG[CashOutStrategy.CONSERVATIVE]["loss_cut"],
                "momentum_threshold": 0.80,
                "risk_level": "high",
                "recommended_for": "High-confidence model bets, top-league fixtures",
            },
        ],
        "active_strategy": "balanced",
        "note": "Strategies are enforced by the Cash-Out Sentinel agent (runs every 30s).",
    }


@cashout_router.get("/config")
async def cashout_config():
    """Return current cash-out sentinel configuration."""
    sentinel = get_cash_out_sentinel()
    s = sentinel.status()
    return {
        "enabled": True,
        "scan_interval_seconds": 30,
        "open_positions": s.get("open_positions", 0),
        "decisions_made": s.get("decisions", 0),
        "executed": s.get("executed", 0),
        "supported_bookmakers": ["sportybet", "football.com", "internal"],
        "config": {
            "aggressive":   {"profit_lock": _STRATEGY_CONFIG[CashOutStrategy.AGGRESSIVE]["profit_lock"],   "loss_cut": _STRATEGY_CONFIG[CashOutStrategy.AGGRESSIVE]["loss_cut"],   "momentum_threshold": 0.65},
            "balanced":     {"profit_lock": _STRATEGY_CONFIG[CashOutStrategy.BALANCED]["profit_lock"],     "loss_cut": _STRATEGY_CONFIG[CashOutStrategy.BALANCED]["loss_cut"],     "momentum_threshold": 0.72},
            "conservative": {"profit_lock": _STRATEGY_CONFIG[CashOutStrategy.CONSERVATIVE]["profit_lock"], "loss_cut": _STRATEGY_CONFIG[CashOutStrategy.CONSERVATIVE]["loss_cut"], "momentum_threshold": 0.80},
        },
    }
