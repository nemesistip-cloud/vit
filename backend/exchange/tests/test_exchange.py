import pytest
from decimal import Decimal
from exchange.models import Order, OrderSide
from exchange.order_book import OrderBook
from exchange.matching_engine import MatchingEngine
from exchange.executor import TradeExecutor

def test_basic_match():
    book = OrderBook()
    executor = TradeExecutor()
    engine = MatchingEngine(book, executor)

    # Add a sell order (Maker)
    sell_order = Order(wallet_id="seller1", side=OrderSide.SELL, price=Decimal("100"), quantity=Decimal("10"))
    engine.process_order(sell_order)

    assert len(book.asks) == 1
    assert engine.get_market_price() is None

    # Add a buy order (Taker) that matches
    buy_order = Order(wallet_id="buyer1", side=OrderSide.BUY, price=Decimal("100"), quantity=Decimal("5"))
    trades = engine.process_order(buy_order)

    assert len(trades) == 1
    assert trades[0].quantity == Decimal("5")
    assert trades[0].price == Decimal("100")
    assert sell_order.remaining_quantity == Decimal("5")
    assert buy_order.remaining_quantity == Decimal("0")
    assert len(book.asks) == 1
    assert len(book.bids) == 0
    assert engine.get_market_price() == Decimal("100")

def test_partial_match_multiple_orders():
    book = OrderBook()
    executor = TradeExecutor()
    engine = MatchingEngine(book, executor)

    # Multiple sell orders at different prices
    engine.process_order(Order(wallet_id="s1", side=OrderSide.SELL, price=Decimal("100"), quantity=Decimal("10")))
    engine.process_order(Order(wallet_id="s2", side=OrderSide.SELL, price=Decimal("110"), quantity=Decimal("10")))

    # Buy order that clears first and partially clears second
    buy_order = Order(wallet_id="b1", side=OrderSide.BUY, price=Decimal("115"), quantity=Decimal("15"))
    trades = engine.process_order(buy_order)

    assert len(trades) == 2
    assert trades[0].price == Decimal("100")
    assert trades[0].quantity == Decimal("10")
    assert trades[1].price == Decimal("110")
    assert trades[1].quantity == Decimal("5")
    assert engine.get_market_price() == Decimal("110")
    assert len(book.asks) == 1
    assert book.asks[0].remaining_quantity == Decimal("5")

def test_no_match():
    book = OrderBook()
    executor = TradeExecutor()
    engine = MatchingEngine(book, executor)

    engine.process_order(Order(wallet_id="s1", side=OrderSide.SELL, price=Decimal("100"), quantity=Decimal("10")))
    buy_order = Order(wallet_id="b1", side=OrderSide.BUY, price=Decimal("90"), quantity=Decimal("10"))
    trades = engine.process_order(buy_order)

    assert len(trades) == 0
    assert len(book.asks) == 1
    assert len(book.bids) == 1
    assert engine.get_market_price() is None

def test_sort_order():
    book = OrderBook()

    book.add_order(Order(wallet_id="b1", side=OrderSide.BUY, price=Decimal("100"), quantity=Decimal("1")))
    book.add_order(Order(wallet_id="b2", side=OrderSide.BUY, price=Decimal("110"), quantity=Decimal("1")))
    book.add_order(Order(wallet_id="b3", side=OrderSide.BUY, price=Decimal("105"), quantity=Decimal("1")))

    assert book.bids[0].price == Decimal("110")
    assert book.bids[1].price == Decimal("105")
    assert book.bids[2].price == Decimal("100")

    book.add_order(Order(wallet_id="s1", side=OrderSide.SELL, price=Decimal("200"), quantity=Decimal("1")))
    book.add_order(Order(wallet_id="s2", side=OrderSide.SELL, price=Decimal("190"), quantity=Decimal("1")))
    book.add_order(Order(wallet_id="s3", side=OrderSide.SELL, price=Decimal("195"), quantity=Decimal("1")))

    assert book.asks[0].price == Decimal("190")
    assert book.asks[1].price == Decimal("195")
    assert book.asks[2].price == Decimal("200")


def test_balance_updates():
    book = OrderBook()
    executor = TradeExecutor()
    engine = MatchingEngine(book, executor)

    # Initialize balances for clarity (optional in this mock)
    executor._update_balance("seller1", "BASE", Decimal("100"))
    executor._update_balance("buyer1", "QUOTE", Decimal("1000"))

    # Maker: Sell 10 @ 100
    engine.process_order(Order(wallet_id="seller1", side=OrderSide.SELL, price=Decimal("100"), quantity=Decimal("10")))

    # Taker: Buy 5 @ 100
    engine.process_order(Order(wallet_id="buyer1", side=OrderSide.BUY, price=Decimal("100"), quantity=Decimal("5")))

    # Check balances
    # Buyer should have -500 QUOTE, +5 BASE
    assert executor.get_balance("buyer1", "QUOTE") == Decimal("500")
    assert executor.get_balance("buyer1", "BASE") == Decimal("5")

    # Seller should have +500 QUOTE, -5 BASE (from initial 100)
    assert executor.get_balance("seller1", "QUOTE") == Decimal("500")
    assert executor.get_balance("seller1", "BASE") == Decimal("95")
