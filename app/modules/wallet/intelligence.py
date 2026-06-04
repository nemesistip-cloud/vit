from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import logging

from app.modules.wallet.models import WalletProfile

logger = logging.getLogger(__name__)

@dataclass
class TradeEvent:
    wallet_id: str
    amount: Decimal
    timestamp: datetime
    is_buy: bool
    volatility: float
    holding_duration_seconds: Optional[float] = None

class RiskScorer:
    """Calculates normalized risk scores (0-1) based on wallet behavior."""

    @staticmethod
    def calculate_score(exposure: float, frequency_per_day: float, avg_volatility: float) -> float:
        # Normalize frequency (assuming > 50 trades/day is high frequency)
        norm_freq = min(frequency_per_day / 50.0, 1.0)

        # Normalize exposure (relative to a hypothetical cap, e.g., 10000 VIT)
        # In a real system, this might be relative to total balance
        norm_exposure = min(exposure / 10000.0, 1.0)

        # Normalize volatility (assuming 0.1 (10%) is high)
        norm_vol = min(avg_volatility / 0.1, 1.0)

        # Weighted combination
        score = (norm_freq * 0.3) + (norm_exposure * 0.4) + (norm_vol * 0.3)
        return float(round(score, 4))

class BehaviorEngine:
    """Updates WalletProfile based on trade events."""

    def update_wallet_behavior(self, profile: WalletProfile, event: TradeEvent) -> None:
        now = datetime.now(timezone.utc)

        # Update total trades and volume
        profile.total_trades += 1
        profile.total_trade_volume += event.amount

        # Update average trade size
        profile.avg_trade_size = profile.total_trade_volume / Decimal(profile.total_trades)

        # Update holding duration if provided
        if event.holding_duration_seconds is not None:
            profile.holding_duration_count += 1
            if profile.avg_holding_duration_seconds == 0:
                profile.avg_holding_duration_seconds = event.holding_duration_seconds
            else:
                # Running average based on events with duration
                profile.avg_holding_duration_seconds = (
                    (profile.avg_holding_duration_seconds * (profile.holding_duration_count - 1)) +
                    event.holding_duration_seconds
                ) / profile.holding_duration_count

        # Update volatility exposure (running average)
        profile.volatility_exposure = (
            (profile.volatility_exposure * (profile.total_trades - 1)) +
            event.volatility
        ) / profile.total_trades

        # Calculate activity score (trades per day since profile creation)
        days_active = max((now - profile.created_at.replace(tzinfo=timezone.utc)).days, 1)
        trades_per_day = profile.total_trades / days_active
        profile.activity_score = min(trades_per_day / 10.0, 1.0) # Normalized 0-1

        # Update risk score
        profile.risk_score = RiskScorer.calculate_score(
            exposure=float(profile.avg_trade_size),
            frequency_per_day=trades_per_day,
            avg_volatility=profile.volatility_exposure
        )

        # Classify trading style
        profile.trading_style = self._classify_trading_style(profile, trades_per_day)

        profile.last_trade_at = event.timestamp
        profile.updated_at = now

    def _classify_trading_style(self, profile: WalletProfile, trades_per_day: float) -> str:
        # Scalper: high frequency, low holding duration
        if trades_per_day > 20 and profile.avg_holding_duration_seconds < 3600:
            return "scalper"

        # Holder: low frequency, high holding duration
        if trades_per_day < 2 and profile.avg_holding_duration_seconds > 86400:
            return "holder"

        return "neutral"

def update_wallet_behavior(profile: WalletProfile, event: TradeEvent) -> WalletProfile:
    engine = BehaviorEngine()
    engine.update_wallet_behavior(profile, event)
    return profile
