"""Background tasks for wallet operations — VITCoin price, subscription renewals."""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wallet.models import (
    PlatformConfig,
    VITCoinPriceHistory,
    WalletTransaction,
    WalletUserSubscription,
    Wallet,
)

logger = logging.getLogger(__name__)


class WalletScheduler:
    """Scheduled background tasks for the wallet module."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_vitcoin_price(self) -> Optional[Decimal]:
        """Calculate and persist the current VITCoin price (revenue-backed formula)."""
        config_result = await self.db.execute(
            select(PlatformConfig).where(PlatformConfig.key == "vitcoin_price_formula")
        )
        config = config_result.scalar_one_or_none()
        if not config:
            logger.warning("VITCoin price formula config missing — skipping update")
            return None

        window_days = config.value.get("window_days", 30)
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

        fee_result = await self.db.execute(
            select(func.sum(WalletTransaction.amount)).where(
                WalletTransaction.type == "fee",
                WalletTransaction.created_at >= cutoff,
                WalletTransaction.status == "confirmed",
            )
        )
        rolling_revenue = fee_result.scalar() or Decimal("0")

        supply_result = await self.db.execute(
            select(func.sum(Wallet.vitcoin_balance))
        )
        circulating_supply = supply_result.scalar() or Decimal("0")

        raw_price = (rolling_revenue / circulating_supply) if circulating_supply > 0 else Decimal("0")

        floor_result = await self.db.execute(
            select(PlatformConfig).where(PlatformConfig.key == "vitcoin_price_floor")
        )
        floor_config = floor_result.scalar_one_or_none()
        price_floor = (
            Decimal(str(floor_config.value.get("amount", "0.001")))
            if floor_config
            else Decimal("0.001")
        )

        final_price = max(raw_price, price_floor)

        record = VITCoinPriceHistory(
            price_usd=final_price,
            circulating_supply=circulating_supply,
            rolling_revenue_usd=rolling_revenue,
        )
        self.db.add(record)
        await self.db.commit()

        logger.info(f"VITCoin price updated: ${final_price:.8f} USD "
                    f"(revenue ${rolling_revenue:.2f}, supply {circulating_supply:.0f})")
        return final_price

    async def process_subscription_renewals(self) -> int:
        """Auto-renew subscriptions expiring within 24 hours."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=1)

        result = await self.db.execute(
            select(WalletUserSubscription).where(
                WalletUserSubscription.status == "active",
                WalletUserSubscription.auto_renew == True,
                WalletUserSubscription.expires_at <= cutoff,
                WalletUserSubscription.expires_at > now,
            )
        )
        subscriptions = result.scalars().all()

        renewed = 0
        for sub in subscriptions:
            try:
                wallet_result = await self.db.execute(
                    select(Wallet).where(Wallet.user_id == sub.user_id)
                )
                wallet = wallet_result.scalar_one_or_none()
                if not wallet:
                    logger.warning(f"No wallet for user {sub.user_id}, skipping renewal {sub.id}")
                    continue

                balance_attr = f"{sub.currency_paid.lower()}_balance"
                balance = getattr(wallet, balance_attr, Decimal("0"))

                if balance >= sub.amount_paid:
                    setattr(wallet, balance_attr, balance - sub.amount_paid)
                    sub.expires_at = sub.expires_at + timedelta(days=30)
                    sub.status = "active"
                    renewed += 1
                    logger.info(f"Auto-renewed subscription {sub.id} for user {sub.user_id}")
                else:
                    sub.status = "expired"
                    logger.warning(f"Insufficient balance — expired subscription {sub.id}")
            except Exception as exc:
                logger.error(f"Renewal error for subscription {sub.id}: {exc}")

        await self.db.commit()
        return renewed
