from decimal import Decimal
from typing import List, Dict, Any
from exchange.models import Order, OrderSide
from exchange.order_book import OrderBook

class MarketIntelligenceEngine:
    """
    Market Intelligence Engine
    Detects whale activity, liquidity walls, and spoofing patterns.
    """

    @staticmethod
    def detect_whale_activity(orders: List[Order], threshold: Decimal = Decimal("10000")) -> List[Dict[str, Any]]:
        """
        Detects orders with quantity above a certain threshold.
        """
        whales = []
        for order in orders:
            if order.quantity >= threshold:
                whales.append({
                    "order_id": order.id,
                    "wallet_id": order.wallet_id,
                    "quantity": float(order.quantity),
                    "side": order.side.value,
                    "timestamp": order.timestamp
                })
        return whales

    @staticmethod
    def detect_liquidity_walls(order_book: OrderBook, depth_percent: float = 0.05) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detects large concentrations of orders at specific price levels within a certain depth.
        """
        walls = {"bids": [], "asks": []}

        best_bid = order_book.get_best_bid()
        best_ask = order_book.get_best_ask()

        if not best_bid or not best_ask:
            return walls

        bid_threshold_price = best_bid.price * Decimal(str(1 - depth_percent))
        ask_threshold_price = best_ask.price * Decimal(str(1 + depth_percent))

        # Aggregate bids
        bid_levels = {}
        for order in order_book.bids:
            if order.price >= bid_threshold_price:
                bid_levels[order.price] = bid_levels.get(order.price, Decimal("0")) + order.remaining_quantity

        # Aggregate asks
        ask_levels = {}
        for order in order_book.asks:
            if order.price <= ask_threshold_price:
                ask_levels[order.price] = ask_levels.get(order.price, Decimal("0")) + order.remaining_quantity

        # Heuristic: A wall is where volume at a level is > 3x the average volume in the range
        def find_walls(levels):
            if not levels: return []
            avg_vol = sum(levels.values()) / Decimal(len(levels))
            detected = []
            for price, vol in levels.items():
                if vol > avg_vol * Decimal("3"):
                    detected.append({"price": float(price), "volume": float(vol)})
            return detected

        walls["bids"] = find_walls(bid_levels)
        walls["asks"] = find_walls(ask_levels)

        return walls

    @staticmethod
    def detect_spoofing_patterns(order_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Basic heuristic spoofing detection.
        Spoofing pattern: Large order placed and cancelled shortly after without being filled,
        often followed by another large order on the opposite side.

        order_history is expected to be a list of events:
        {'type': 'place'|'cancel', 'order_id': str, 'wallet_id': str, 'side': 'buy'|'sell', 'quantity': float, 'timestamp': datetime}
        """
        spoofing_alerts = []
        # Group by order_id
        orders = {}
        for event in order_history:
            oid = event['order_id']
            if oid not in orders:
                orders[oid] = []
            orders[oid].append(event)

        for oid, events in orders.items():
            # Check if it was placed and cancelled
            types = [e['type'] for e in events]
            if 'place' in types and 'cancel' in types:
                place_event = next(e for e in events if e['type'] == 'place')
                cancel_event = next(e for e in events if e['type'] == 'cancel')

                duration = (cancel_event['timestamp'] - place_event['timestamp']).total_seconds()

                # Heuristic: Cancelled within 5 seconds and large quantity
                if duration < 5 and place_event['quantity'] > 5000:
                    spoofing_alerts.append({
                        "order_id": oid,
                        "wallet_id": place_event['wallet_id'],
                        "reason": "Large order cancelled quickly",
                        "duration": duration,
                        "quantity": place_event['quantity']
                    })

        return spoofing_alerts
