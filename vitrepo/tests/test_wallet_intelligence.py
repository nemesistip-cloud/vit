import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

# Define a mock WalletProfile that doesn'\''t depend on SQLAlchemy for behavior tests
class MockWalletProfile:
    def __init__(self, wallet_id, created_at=None, total_trades=0, total_trade_volume=Decimal("0"), avg_holding_duration_seconds=0.0):
        self.wallet_id = wallet_id
        self.created_at = created_at or datetime.now(timezone.utc)
        self.total_trades = total_trades
        self.total_trade_volume = total_trade_volume
        self.avg_trade_size = Decimal("0")
        self.avg_holding_duration_seconds = avg_holding_duration_seconds
        self.holding_duration_count = 0
        self.volatility_exposure = 0.0
        self.risk_score = 0.0
        self.activity_score = 0.0
        self.trading_style = "neutral"
        self.last_trade_at = None
        self.updated_at = None

from app.modules.wallet.intelligence import TradeEvent, BehaviorEngine, RiskScorer

def test_risk_scorer():
    # Test low risk
    score_low = RiskScorer.calculate_score(exposure=100.0, frequency_per_day=1.0, avg_volatility=0.01)
    assert 0 <= score_low <= 1.0

    # Test high risk
    score_high = RiskScorer.calculate_score(exposure=20000.0, frequency_per_day=60.0, avg_volatility=0.2)
    assert score_high > score_low
    assert score_high == 1.0 # Should be capped at 1.0

def test_behavior_engine_updates():
    engine = BehaviorEngine()
    profile = MockWalletProfile(
        wallet_id="test_wallet",
        created_at=datetime.now(timezone.utc) - timedelta(days=2)
    )

    # Event 1: Buy (no duration)
    event1 = TradeEvent(
        wallet_id="test_wallet",
        amount=Decimal("1000"),
        timestamp=datetime.now(timezone.utc),
        is_buy=True,
        volatility=0.02,
        holding_duration_seconds=None
    )

    engine.update_wallet_behavior(profile, event1)

    assert profile.total_trades == 1
    assert profile.holding_duration_count == 0
    assert profile.total_trade_volume == Decimal("1000")
    assert profile.avg_trade_size == Decimal("1000")
    assert profile.volatility_exposure == 0.02
    assert profile.trading_style == "neutral"

    # Event 2: Sell with holding duration
    event2 = TradeEvent(
        wallet_id="test_wallet",
        amount=Decimal("500"),
        timestamp=datetime.now(timezone.utc) + timedelta(minutes=10),
        is_buy=False,
        volatility=0.04,
        holding_duration_seconds=600.0 # 10 minutes
    )

    engine.update_wallet_behavior(profile, event2)

    assert profile.total_trades == 2
    assert profile.holding_duration_count == 1
    assert profile.total_trade_volume == Decimal("1500")
    assert profile.avg_trade_size == Decimal("750")
    assert profile.volatility_exposure == pytest.approx(0.03)
    assert profile.avg_holding_duration_seconds == 600.0

    # Event 3: Another sell with duration
    event3 = TradeEvent(
        wallet_id="test_wallet",
        amount=Decimal("500"),
        timestamp=datetime.now(timezone.utc) + timedelta(minutes=20),
        is_buy=False,
        volatility=0.06,
        holding_duration_seconds=1200.0 # 20 minutes
    )
    engine.update_wallet_behavior(profile, event3)
    assert profile.holding_duration_count == 2
    assert profile.avg_holding_duration_seconds == 900.0 # (600 + 1200) / 2

def test_trading_style_classification():
    engine = BehaviorEngine()

    # Scalper test
    profile_scalper = MockWalletProfile(
        wallet_id="scalper",
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
        total_trades=25,
        avg_holding_duration_seconds=500.0
    )
    style = engine._classify_trading_style(profile_scalper, trades_per_day=25.0)
    assert style == "scalper"

    # Holder test
    profile_holder = MockWalletProfile(
        wallet_id="holder",
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
        total_trades=5,
        avg_holding_duration_seconds=100000.0
    )
    style = engine._classify_trading_style(profile_holder, trades_per_day=0.5)
    assert style == "holder"

def test_activity_score():
    engine = BehaviorEngine()
    profile = MockWalletProfile(
        wallet_id="test",
        created_at=datetime.now(timezone.utc) - timedelta(days=5)
    )

    event = TradeEvent(
        wallet_id="test",
        amount=Decimal("100"),
        timestamp=datetime.now(timezone.utc),
        is_buy=True,
        volatility=0.01
    )

    # After 5 days, 1 trade => 0.2 trades/day. Activity score = 0.2 / 10.0 = 0.02
    engine.update_wallet_behavior(profile, event)
    assert profile.activity_score == pytest.approx(0.02)
