from decimal import Decimal
from typing import List, Optional
from .models import Order, OrderSide
import bisect

class OrderBook:
    def __init__(self):
        # bids sorted descending by price
        self.bids: List[Order] = []
        # asks sorted ascending by price
        self.asks: List[Order] = []

    def add_order(self, order: Order):
        if order.side == OrderSide.BUY:
            # For bids, we want descending price.
            # bisect works on ascending, so we can use a custom key or just sort.
            # Since performance is usually key, let's keep it sorted.
            self.bids.append(order)
            self.bids.sort(key=lambda x: (-x.price, x.timestamp))
        else:
            self.asks.append(order)
            self.asks.sort(key=lambda x: (x.price, x.timestamp))

    def remove_order(self, order: Order):
        if order.side == OrderSide.BUY:
            self.bids = [o for o in self.bids if o.id != order.id]
        else:
            self.asks = [o for o in self.asks if o.id != order.id]

    def get_best_bid(self) -> Optional[Order]:
        return self.bids[0] if self.bids else None

    def get_best_ask(self) -> Optional[Order]:
        return self.asks[0] if self.asks else None

    def clean_empty_orders(self):
        self.bids = [o for o in self.bids if o.remaining_quantity > 0]
        self.asks = [o for o in self.asks if o.remaining_quantity > 0]
