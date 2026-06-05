import pytest
from decimal import Decimal
from datetime import datetime
from exchange.models import Order, OrderSide
from exchange.order_book import OrderBook
from app.modules.ai.svi import SyntheticValueIndex
from app.modules.ai.market_intelligence import MarketIntelligenceEngine
from app.modules.ai.risk_engine import RiskEngine
from app.modules.ai.copilot import AICopilot

def test_svi_calculation():
    svi = SyntheticValueIndex.calculate_svi(Decimal("1000"), Decimal("500"))
    assert svi == Decimal("2")

    svi_zero = SyntheticValueIndex.calculate_svi(Decimal("1000"), Decimal("0"))
    assert svi_zero == Decimal("0")

def test_whale_detection():
    engine = MarketIntelligenceEngine()
    orders = [
        Order(wallet_id="w1", side=OrderSide.BUY, price=Decimal("10"), quantity=Decimal("100")),
        Order(wallet_id="w2", side=OrderSide.SELL, price=Decimal("11"), quantity=Decimal("15000")),
    ]
    whales = engine.detect_whale_activity(orders, threshold=Decimal("10000"))
    assert len(whales) == 1
    assert whales[0]["wallet_id"] == "w2"

def test_liquidity_walls():
    engine = MarketIntelligenceEngine()
    ob = OrderBook()
    # Add some base liquidity
    ob.add_order(Order(wallet_id="w1", side=OrderSide.BUY, price=Decimal("100"), quantity=Decimal("10")))
    ob.add_order(Order(wallet_id="w2", side=OrderSide.SELL, price=Decimal("101"), quantity=Decimal("10")))

    # Add a wall at 95 (within 10% of 100)
    for i in range(10):
         ob.add_order(Order(wallet_id=f"small_{i}", side=OrderSide.BUY, price=Decimal("99")-Decimal(str(i)), quantity=Decimal("1")))

    ob.add_order(Order(wallet_id="w3", side=OrderSide.BUY, price=Decimal("95"), quantity=Decimal("200")))

    walls = engine.detect_liquidity_walls(ob, depth_percent=0.1)
    assert len(walls["bids"]) >= 1
    assert any(w["price"] == 95.0 for w in walls["bids"])

def test_volatility_calculation():
    engine = RiskEngine()
    prices = [Decimal("100"), Decimal("110"), Decimal("100"), Decimal("90"), Decimal("100")]
    vol = engine.calculate_market_volatility(prices)
    assert vol > 0

def test_liquidity_thinness():
    engine = RiskEngine()
    ob = OrderBook()
    # Very thin liquidity
    ob.add_order(Order(wallet_id="w1", side=OrderSide.BUY, price=Decimal("100"), quantity=Decimal("1")))
    ob.add_order(Order(wallet_id="w2", side=OrderSide.SELL, price=Decimal("110"), quantity=Decimal("1")))

    score = engine.score_liquidity_thinness(ob)
    assert score["score"] > 0.5
    assert score["status"] in ["moderate", "very_thin"]

def test_copilot_insights():
    svi_report = {"status": "inflationary_pressure", "svi": 2000.0}
    mi_report = {"whales": [{"id": "1"}], "walls": {"asks": [{"price": 100.0}]}}
    risk_report = {"liquidity": {"score": 0.8}, "volatility": 0.06}

    copilot = AICopilot(svi_report, mi_report, risk_report)
    insights = copilot.generate_insights()

    assert any("inflationary" in i for i in insights)
    assert any("Resistance" in i for i in insights)
    assert any("low liquidity" in i for i in insights)
    assert any("volatility" in i for i in insights)
