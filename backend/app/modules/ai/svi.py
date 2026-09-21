from decimal import Decimal
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.wallet.models import Wallet, WalletTransaction

class SyntheticValueIndex:
    """
    Synthetic Value Index (SVI)
    Formula: total_vitcoin_in_circulation / total_usd_deposited
    Used as a structural market health indicator, NOT price.
    """

    @staticmethod
    def calculate_svi(total_vitcoin_circulating: Decimal, total_usd_deposited: Decimal) -> Decimal:
        if total_usd_deposited <= 0:
            return Decimal("0")
        return total_vitcoin_circulating / total_usd_deposited

    @classmethod
    async def get_current_svi(cls, db: AsyncSession) -> Decimal:
        # Calculate total vitcoin in circulation (liquid + staked)
        vitcoin_query = select(
            func.sum(Wallet.vitcoin_balance + Wallet.staked_vitcoin_balance)
        )
        total_vitcoin = (await db.execute(vitcoin_query)).scalar() or Decimal("0")

        # Calculate total USD deposited
        # We look for transactions of type 'deposit' where currency is 'USD' or 'USDT' (assuming 1:1 for simplicity or we might need rates)
        # For this requirement, we'll sum 'deposit' transactions in USD/USDT
        usd_deposit_query = select(func.sum(WalletTransaction.amount)).where(
            WalletTransaction.type == "deposit",
            WalletTransaction.status == "confirmed",
            WalletTransaction.currency.in_(["USD", "USDT"])
        )
        total_usd = (await db.execute(usd_deposit_query)).scalar() or Decimal("0")

        return cls.calculate_svi(total_vitcoin, total_usd)

    @classmethod
    async def get_market_health_report(cls, db: AsyncSession) -> dict:
        svi = await cls.get_current_svi(db)

        # Heuristic for health
        # If SVI is high, it might mean lots of VITCOIN backed by less USD (inflationary risk)
        # If SVI is low, it might mean strong backing.
        # This is a "synthetic" value so the range depends on initial distribution.

        health_status = "stable"
        if svi > Decimal("1000"):
            health_status = "inflationary_pressure"
        elif svi < Decimal("1"):
            health_status = "highly_collateralized"

        return {
            "svi": float(svi),
            "status": health_status,
            "timestamp": func.now()
        }
