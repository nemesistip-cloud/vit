from typing import List, Dict, Any
from .svi import SyntheticValueIndex
from .market_intelligence import MarketIntelligenceEngine
from .risk_engine import RiskEngine

class AICopilot:
    """
    AI Copilot
    Aggregates data from SVI, Market Intelligence, and Risk Engine to provide insights.
    """

    def __init__(self, svi_report: Dict[str, Any], mi_report: Dict[str, Any], risk_report: Dict[str, Any]):
        self.svi_report = svi_report
        self.mi_report = mi_report
        self.risk_report = risk_report

    def generate_insights(self) -> List[str]:
        insights = []

        # SVI Insights
        if self.svi_report.get("status") == "inflationary_pressure":
            insights.append("Market entering inflationary regime; SVI indicates supply outstripping USD backing.")
        elif self.svi_report.get("status") == "highly_collateralized":
            insights.append("Structural health is strong; VITCOIN is highly collateralized by USD deposits.")

        # Market Intelligence Insights
        whales = self.mi_report.get("whales", [])
        if len(whales) > 3:
            insights.append(f"High whale activity detected: {len(whales)} large orders currently in the book.")

        walls = self.mi_report.get("walls", {})
        if walls.get("asks"):
            insights.append("Resistance detected: Significant liquidity walls on the sell side.")
        if walls.get("bids"):
            insights.append("Support detected: Significant liquidity walls on the buy side.")

        # Risk Insights
        risk_score = self.risk_report.get("liquidity", {}).get("score", 0.0)
        if risk_score > 0.7:
            insights.append("Market entering low liquidity regime; expect higher slippage.")

        volatility = self.risk_report.get("volatility", 0.0)
        if volatility > 0.05:
            insights.append("Risk of volatility spike increasing; large price swings observed.")

        # If no specific insights, provide a general one
        if not insights:
            insights.append("Market conditions are currently stable.")

        return insights

    @classmethod
    async def get_market_copilot_report(cls, db, order_book, price_history, wallet_balances, current_prices):
        """
        Helper to generate a full copilot report.
        """
        svi_report = await SyntheticValueIndex.get_market_health_report(db)

        mi_engine = MarketIntelligenceEngine()
        mi_report = {
            "whales": mi_engine.detect_whale_activity(order_book.bids + order_book.asks),
            "walls": mi_engine.detect_liquidity_walls(order_book)
        }

        risk_engine = RiskEngine()
        risk_report = {
            "volatility": risk_engine.calculate_market_volatility(price_history),
            "liquidity": risk_engine.score_liquidity_thinness(order_book)
        }

        if wallet_balances:
            risk_report["wallet_exposure"] = risk_engine.estimate_wallet_exposure(wallet_balances, current_prices)

        copilot = cls(svi_report, mi_report, risk_report)
        return {
            "svi": svi_report,
            "market_intelligence": mi_report,
            "risk": risk_report,
            "insights": copilot.generate_insights()
        }
