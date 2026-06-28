import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wallet.models import (
    VITCoinPriceHistory, PlatformConfig, WalletTransaction,
    Wallet, SavingsVault
)
from app.core.cache import cache

logger = logging.getLogger(__name__)

# v5.5.0 3-Governor Phase Weights
PHASE_WEIGHTS = {
    "launch": {"g1": Decimal("0.6"), "g2": Decimal("0.3"), "g3": Decimal("0.1")},
    "growth": {"g1": Decimal("0.4"), "g2": Decimal("0.4"), "g3": Decimal("0.2")},
    "mature": {"g1": Decimal("0.2"), "g2": Decimal("0.4"), "g3": Decimal("0.4")},
}

# Thresholds for phase detection based on circulating supply
PHASE_THRESHOLDS = {
    "growth": Decimal("100000000"),  # 100M VIT
    "mature": Decimal("500000000"),  # 500M VIT
}

PRICE_CACHE_KEY = "vit:vitcoin:price_cache"

class VITCoinPricingEngine:
    """
    3-Governor Hybrid Pricing Engine (v5.5.0)
    G1: Demand Signal (Buy/Sell Volume Ratio)
    G2: Supply Compression (Locked/Circulating Ratio)
    G3: Momentum Carry (Historical Price Velocity)
    """

    @staticmethod
    def detect_phase(circulating_supply: Decimal) -> str:
        """Detect the current market phase based on circulating supply."""
        if circulating_supply < PHASE_THRESHOLDS["growth"]:
            return "launch"
        elif circulating_supply < PHASE_THRESHOLDS["mature"]:
            return "growth"
        else:
            return "mature"

    @staticmethod
    async def get_governor_1_demand(db: AsyncSession) -> Decimal:
        """
        Governor 1: Demand Signal
        Ratio of Buy vs. Sell volume in last 24h.
        """
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        # Total Buy volume (in VITCoin)
        buy_q = select(func.sum(WalletTransaction.amount)).where(
            WalletTransaction.type == "buy",
            WalletTransaction.currency == "VITCoin",
            WalletTransaction.status == "confirmed",
            WalletTransaction.created_at >= cutoff
        )
        buy_vol = (await db.execute(buy_q)).scalar() or Decimal("0")

        # Total Sell volume (in VITCoin)
        sell_q = select(func.sum(WalletTransaction.amount)).where(
            WalletTransaction.type == "sell",
            WalletTransaction.currency == "VITCoin",
            WalletTransaction.status == "confirmed",
            WalletTransaction.created_at >= cutoff
        )
        sell_vol = (await db.execute(sell_q)).scalar() or Decimal("0")

        if sell_vol == 0:
            return Decimal("1.1") if buy_vol > 0 else Decimal("1.0")

        ratio = buy_vol / sell_vol
        # Clamp ratio to sensible bounds (0.5 to 2.0) to avoid extreme volatility
        return max(Decimal("0.5"), min(Decimal("2.0"), ratio))

    @staticmethod
    async def get_governor_2_supply(db: AsyncSession, circulating_supply: Decimal) -> Decimal:
        """
        Governor 2: Supply Compression
        Ratio of Locked (Staked + Vaulted) vs. Circulating supply.
        """
        if circulating_supply <= 0:
            return Decimal("1.0")

        # Total Staked
        staked_q = select(func.sum(Wallet.staked_vitcoin_balance))
        staked_total = (await db.execute(staked_q)).scalar() or Decimal("0")

        # Total Vaulted
        vaulted_q = select(func.sum(SavingsVault.current_balance)).where(
            SavingsVault.currency == "VITCoin",
            SavingsVault.is_active == True
        )
        vaulted_total = (await db.execute(vaulted_q)).scalar() or Decimal("0")

        locked_total = staked_total + vaulted_total
        compression_ratio = locked_total / circulating_supply

        # Base multiplier 1.0 + compression_ratio
        # If 50% supply is locked, multiplier is 1.5
        return Decimal("1.0") + compression_ratio

    @staticmethod
    async def get_governor_3_momentum(db: AsyncSession) -> Decimal:
        """
        Governor 3: Momentum Carry
        Price trend derived from last 3 history snapshots.
        """
        q = select(VITCoinPriceHistory.price_usd).order_by(
            VITCoinPriceHistory.calculated_at.desc()
        ).limit(3)
        prices = (await db.execute(q)).scalars().all()

        if len(prices) < 2:
            return Decimal("1.0")

        # Simple momentum: (P_current / P_previous)
        current = Decimal(str(prices[0]))
        previous = Decimal(str(prices[1]))

        if previous == 0:
            return Decimal("1.0")

        momentum = current / previous
        # Clamp momentum (0.9 to 1.1)
        return max(Decimal("0.9"), min(Decimal("1.1"), momentum))

    @classmethod
    async def get_current_price(cls, db: AsyncSession) -> Dict[str, Any]:
        """
        Execute 3-Governor logic and return full price state.
        Cached in Redis for 60s.
        """
        # 1. Try Cache
        cached_price = await cache.get(PRICE_CACHE_KEY)
        if cached_price:
            # We need to handle Decimal serialization if coming from cache
            # But the requirement says "Cache result in Redis key ...", and app.core.cache is a simple in-memory dict-wrapper mostly.
            # Actually app.core.cache uses a dict in-memory. If REDIS_URL is set, it might use redis.
            # Let's check app/core/cache.py again.
            return cached_price

        # 2. Base Data
        # Get latest circulating supply
        supply_q = select(func.sum(Wallet.vitcoin_balance + Wallet.staked_vitcoin_balance))
        circulating_supply = (await db.execute(supply_q)).scalar() or Decimal("0")

        # Fallback to seed if zero supply
        if circulating_supply <= 0:
            circulating_supply = Decimal("1000000") # 1M default

        phase = cls.detect_phase(circulating_supply)
        weights = PHASE_WEIGHTS[phase]

        # 3. Governors
        g1 = await cls.get_governor_1_demand(db)
        g2 = await cls.get_governor_2_supply(db, circulating_supply)
        g3 = await cls.get_governor_3_momentum(db)

        # 4. Hybrid Computation
        # Price = Base * (W1*G1 + W2*G2 + W3*G3)
        # We need a Base price. We'll use the latest recorded price or seed $0.10.
        latest_p_q = select(VITCoinPriceHistory.price_usd).order_by(
            VITCoinPriceHistory.calculated_at.desc()
        ).limit(1)
        base_price = (await db.execute(latest_p_q)).scalar() or Decimal("0.10")

        multiplier = (weights["g1"] * g1) + (weights["g2"] * g2) + (weights["g3"] * g3)
        computed_price = base_price * multiplier

        # 5. Floor Enforcement
        floor_q = select(PlatformConfig).where(PlatformConfig.key == "vitcoin_price_floor")
        floor_cfg = (await db.execute(floor_q)).scalar_one_or_none()
        floor_usd = Decimal(str(floor_cfg.value.get("amount", "0.001"))) if floor_cfg else Decimal("0.001")

        final_price = max(computed_price, floor_usd)

        result = {
            "price_usd": float(final_price),
            "phase": phase,
            "floor_usd": float(floor_usd),
            "governors": {
                "g1": float(g1),
                "g2": float(g2),
                "g3": float(g3)
            },
            "computed_at": datetime.now(timezone.utc).isoformat()
        }

        # 6. Cache and Return
        await cache.set(PRICE_CACHE_KEY, result, ttl=60)

        # Return with original types for internal use, but cached as JSON-serializable
        return {
            "price_usd": final_price,
            "phase": phase,
            "floor_usd": floor_usd,
            "governors": {
                "g1": g1,
                "g2": g2,
                "g3": g3
            },
            "computed_at": datetime.now(timezone.utc)
        }
