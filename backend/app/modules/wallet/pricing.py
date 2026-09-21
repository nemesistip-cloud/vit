# app/modules/wallet/pricing.py
"""VITCoin pricing engine and exchange rate utilities."""

import logging
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wallet.models import PlatformConfig, VITCoinPriceHistory, WalletTransaction, Currency

logger = logging.getLogger(__name__)


class VITCoinPricingEngine:
    """VITCoin price calculation and management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_current_price(self) -> Dict[str, Decimal]:
        """Get current VITCoin price in all supported currencies."""

        # Get latest price from history
        result = await self.db.execute(
            select(VITCoinPriceHistory)
            .order_by(VITCoinPriceHistory.calculated_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()

        if not latest:
            logger.warning(
                "VIT_PRICE_FALLBACK no rows in VITCoinPriceHistory — returning "
                "seed price ($0.10). Run the pricing scheduler or seed the "
                "table to recover. This is a degraded state."
            )
            price_usd = Decimal("0.10")
        else:
            price_usd = latest.price_usd

        # Get exchange rates from platform config 'exchange_rates_usd'
        rates_result = await self.db.execute(
            select(PlatformConfig).where(PlatformConfig.key == "exchange_rates_usd")
        )
        rates_config = rates_result.scalar_one_or_none()

        if rates_config and isinstance(rates_config.value, dict):
            # We have 1 Currency = X USD. We need 1 USD = X Currency.
            ngn_rate = Decimal(str(rates_config.value.get("NGN", 0.000633)))
            usd_ngn = Decimal("1") / ngn_rate if ngn_rate > 0 else Decimal("1580")

            pi_rate = Decimal(str(rates_config.value.get("PI", 0.314159)))
            usd_pi = Decimal("1") / pi_rate if pi_rate > 0 else Decimal("3.18")

            usd_usdt = Decimal("1.0")
        else:
            logger.warning(
                "VIT_PRICE_FALLBACK PlatformConfig key 'exchange_rates_usd' missing — "
                "using hardcoded defaults."
            )
            usd_ngn = Decimal("1580")
            usd_pi = Decimal("3.18")
            usd_usdt = Decimal("1.0")

        return {
            "usd": price_usd,
            "ngn": price_usd * usd_ngn,
            "usdt": price_usd * usd_usdt,
            "pi": price_usd * usd_pi,
        }

    async def calculate_conversion_amount(
        self,
        from_currency: Currency,
        to_currency: Currency,
        amount: Decimal,
    ) -> Dict[str, Decimal]:
        """Calculate converted amount with fees."""

        # Get current prices
        prices = await self.get_current_price()

        # Get conversion fee
        fee_result = await self.db.execute(
            select(PlatformConfig).where(PlatformConfig.key == "conversion_fee_pct")
        )
        fee_config = fee_result.scalar_one_or_none()
        fee_pct = Decimal(str(fee_config.value.get("value", 0.5))) if fee_config else Decimal("0.5")

        # Convert to USD first (base currency)
        if from_currency == Currency.USD:
            usd_amount = amount
        elif from_currency == Currency.NGN:
            usd_amount = amount * prices["usd"] / prices["ngn"]
        elif from_currency == Currency.USDT:
            usd_amount = amount * prices["usd"] / prices["usdt"]
        elif from_currency == Currency.PI:
            usd_amount = amount * prices["usd"] / prices["pi"]
        elif from_currency == Currency.VITCOIN:
            usd_amount = amount * prices["usd"]
        else:
            usd_amount = amount

        # Apply fee
        fee = usd_amount * (fee_pct / Decimal("100"))
        usd_amount_after_fee = usd_amount - fee

        # Convert to target currency
        if to_currency == Currency.USD:
            converted_amount = usd_amount_after_fee
        elif to_currency == Currency.NGN:
            converted_amount = usd_amount_after_fee * prices["ngn"] / prices["usd"]
        elif to_currency == Currency.USDT:
            converted_amount = usd_amount_after_fee * prices["usdt"] / prices["usd"]
        elif to_currency == Currency.PI:
            converted_amount = usd_amount_after_fee * prices["pi"] / prices["usd"]
        elif to_currency == Currency.VITCOIN:
            converted_amount = usd_amount_after_fee / prices["usd"]
        else:
            converted_amount = usd_amount_after_fee

        return {
            "from_amount": amount,
            "to_amount": converted_amount,
            "fee": fee,
            "fee_pct": fee_pct,
            "rate": (usd_amount / amount) if amount > 0 else Decimal("0"),
        }

    async def get_circulating_supply(self) -> Decimal:
        """Get current VITCoin circulating supply."""
        from sqlalchemy import case

        result = await self.db.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (WalletTransaction.direction == 'credit', WalletTransaction.amount),
                            else_=Decimal('0'),
                        )
                    ),
                    Decimal('0'),
                ).label("total_credited"),
                func.coalesce(
                    func.sum(
                        case(
                            (WalletTransaction.direction == 'debit', WalletTransaction.amount),
                            else_=Decimal('0'),
                        )
                    ),
                    Decimal('0'),
                ).label("total_debited"),
            ).where(
                WalletTransaction.currency == "VITCoin",
                WalletTransaction.status == "confirmed",
            )
        )
        row = result.one_or_none()
        if row:
            credited = row.total_credited or Decimal("0")
            debited  = row.total_debited  or Decimal("0")
            supply   = credited - debited
            if supply > Decimal("0"):
                return supply

        cfg_result = await self.db.execute(
            select(PlatformConfig).where(PlatformConfig.key == "vitcoin_supply")
        )
        cfg = cfg_result.scalar_one_or_none()
        if cfg and isinstance(cfg.value, dict):
            try:
                return Decimal(str(cfg.value.get("initial", 10_000_000)))
            except Exception:
                pass
        return Decimal("10000000")

    async def get_rolling_revenue(self, days: int = 30) -> Decimal:
        """Get rolling revenue from fees for the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.execute(
            select(func.sum(WalletTransaction.amount))
            .where(
                WalletTransaction.type == "fee",
                WalletTransaction.created_at >= cutoff,
                WalletTransaction.status == "confirmed",
            )
        )
        return result.scalar() or Decimal("0")
