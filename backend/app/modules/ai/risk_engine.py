from decimal import Decimal
from typing import List, Dict, Any
import math
from exchange.order_book import OrderBook

class RiskEngine:
    """
    Risk Engine
    Estimates wallet exposure, market volatility, and liquidity thinness.
    """

    @staticmethod
    def estimate_wallet_exposure(
        wallet_balances: Dict[str, Decimal],
        current_prices_usd: Dict[str, Decimal]
    ) -> Dict[str, Any]:
        """
        Estimates total USD value exposure of a wallet.
        """
        total_value_usd = Decimal("0")
        exposures = {}

        for currency, amount in wallet_balances.items():
            price = current_prices_usd.get(currency, Decimal("0"))
            value = amount * price
            total_value_usd += value
            exposures[currency] = {
                "amount": float(amount),
                "value_usd": float(value)
            }

        return {
            "total_value_usd": float(total_value_usd),
            "exposures": exposures,
            "concentration_risk": "high" if len(exposures) < 3 and total_value_usd > 1000 else "low"
        }

    @staticmethod
    def calculate_market_volatility(price_history: List[Decimal]) -> float:
        """
        Calculates simple standard deviation of returns as volatility.
        """
        if len(price_history) < 2:
            return 0.0

        returns = []
        for i in range(1, len(price_history)):
            prev = price_history[i-1]
            curr = price_history[i]
            if prev > 0:
                returns.append(float((curr - prev) / prev))

        if not returns:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance)

        return volatility

    @staticmethod
    def score_liquidity_thinness(order_book: OrderBook) -> Dict[str, Any]:
        """
        Scores how "thin" the liquidity is.
        Thin liquidity means small orders cause large price movements.
        """
        best_bid = order_book.get_best_bid()
        best_ask = order_book.get_best_ask()

        if not best_bid or not best_ask:
            return {"score": 1.0, "status": "no_liquidity"}

        spread = (best_ask.price - best_bid.price) / best_bid.price

        # Calculate slippage for a "standard" order size, e.g. 1000 VITCOIN
        standard_size = Decimal("1000")

        def calculate_slippage(orders, size):
            accumulated_size = Decimal("0")
            weighted_price = Decimal("0")
            for o in orders:
                fill = min(o.remaining_quantity, size - accumulated_size)
                weighted_price += fill * o.price
                accumulated_size += fill
                if accumulated_size >= size:
                    break

            if accumulated_size < size:
                return None # Not enough liquidity

            avg_price = weighted_price / size
            return avg_price

        buy_slippage_price = calculate_slippage(order_book.asks, standard_size)
        sell_slippage_price = calculate_slippage(order_book.bids, standard_size)

        buy_slippage = 1.0
        if buy_slippage_price:
            buy_slippage = float((buy_slippage_price - best_ask.price) / best_ask.price)

        sell_slippage = 1.0
        if sell_slippage_price:
            sell_slippage = float((best_bid.price - sell_slippage_price) / best_bid.price)

        # Composite score 0 (thick) to 1 (thin)
        score = min(1.0, (float(spread) * 10) + (buy_slippage * 5) + (sell_slippage * 5))

        status = "thick"
        if score > 0.7:
            status = "very_thin"
        elif score > 0.3:
            status = "moderate"

        return {
            "score": score,
            "status": status,
            "spread_pct": float(spread) * 100,
            "buy_slippage_pct": buy_slippage * 100,
            "sell_slippage_pct": sell_slippage * 100
        }
