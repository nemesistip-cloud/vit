import logging
from .models import Trade
from decimal import Decimal
from typing import Dict

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self):
        self.trade_history = []
        # Simple internal balance tracking to satisfy "update balances"
        # without external wallet dependency as per constraints.
        # wallet_id -> {currency -> amount}
        self.balances: Dict[str, Dict[str, Decimal]] = {}

    def execute_trade(self, trade: Trade):
        """
        Executes a trade by updating internal balances and recording the trade.
        """
        total_value = trade.price * trade.quantity

        # Update balances (Mock implementation)
        # Buyer: -Quote, +Base
        self._update_balance(trade.buyer_wallet_id, "QUOTE", -total_value)
        self._update_balance(trade.buyer_wallet_id, "BASE", trade.quantity)

        # Seller: +Quote, -Base
        self._update_balance(trade.seller_wallet_id, "QUOTE", total_value)
        self._update_balance(trade.seller_wallet_id, "BASE", -trade.quantity)

        logger.info(f"TRADE EXECUTED: {trade.quantity} units @ {trade.price} | "
                    f"Buyer {trade.buyer_wallet_id} paid {total_value} QUOTE")

        self.trade_history.append(trade)
        self._emit_trade_event(trade)

    def _update_balance(self, wallet_id: str, currency: str, amount: Decimal):
        if wallet_id not in self.balances:
            self.balances[wallet_id] = {"QUOTE": Decimal("0"), "BASE": Decimal("0")}
        self.balances[wallet_id][currency] += amount

    def _emit_trade_event(self, trade: Trade):
        # Placeholder for event emission
        logger.info(f"EMITTING TRADE EVENT: {trade.id}")

    def get_balance(self, wallet_id: str, currency: str) -> Decimal:
        return self.balances.get(wallet_id, {}).get(currency, Decimal("0"))
