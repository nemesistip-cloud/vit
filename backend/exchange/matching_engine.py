from typing import List, Tuple
from .models import Order, OrderSide, Trade
from .order_book import OrderBook
from .executor import TradeExecutor

class MatchingEngine:
    def __init__(self, order_book: OrderBook, executor: TradeExecutor):
        self.order_book = order_book
        self.executor = executor
        self.last_trade_price = None

    def process_order(self, order: Order) -> List[Trade]:
        trades = []
        if order.side == OrderSide.BUY:
            trades = self._match_buy_order(order)
        else:
            trades = self._match_sell_order(order)

        if order.remaining_quantity > 0:
            self.order_book.add_order(order)

        return trades

    def _match_buy_order(self, buy_order: Order) -> List[Trade]:
        trades = []
        while buy_order.remaining_quantity > 0:
            best_ask = self.order_book.get_best_ask()
            if not best_ask or buy_order.price < best_ask.price:
                break

            # Match found
            match_quantity = min(buy_order.remaining_quantity, best_ask.remaining_quantity)
            trade_price = best_ask.price # Execute at maker price

            trade = Trade(
                buyer_wallet_id=buy_order.wallet_id,
                seller_wallet_id=best_ask.wallet_id,
                price=trade_price,
                quantity=match_quantity,
                buy_order_id=buy_order.id,
                sell_order_id=best_ask.id
            )

            self.executor.execute_trade(trade)
            trades.append(trade)
            self.last_trade_price = trade_price

            buy_order.remaining_quantity -= match_quantity
            best_ask.remaining_quantity -= match_quantity

            if best_ask.remaining_quantity == 0:
                self.order_book.remove_order(best_ask)

        return trades

    def _match_sell_order(self, sell_order: Order) -> List[Trade]:
        trades = []
        while sell_order.remaining_quantity > 0:
            best_bid = self.order_book.get_best_bid()
            if not best_bid or sell_order.price > best_bid.price:
                break

            # Match found
            match_quantity = min(sell_order.remaining_quantity, best_bid.remaining_quantity)
            trade_price = best_bid.price # Execute at maker price

            trade = Trade(
                buyer_wallet_id=best_bid.wallet_id,
                seller_wallet_id=sell_order.wallet_id,
                price=trade_price,
                quantity=match_quantity,
                buy_order_id=best_bid.id,
                sell_order_id=sell_order.id
            )

            self.executor.execute_trade(trade)
            trades.append(trade)
            self.last_trade_price = trade_price

            sell_order.remaining_quantity -= match_quantity
            best_bid.remaining_quantity -= match_quantity

            if best_bid.remaining_quantity == 0:
                self.order_book.remove_order(best_bid)

        return trades

    def get_market_price(self):
        return self.last_trade_price
