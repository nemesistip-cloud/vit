import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quant.models import StrategyVault, UserVaultPosition
from app.modules.wallet.services import WalletService
from app.modules.wallet.models import Currency

logger = logging.getLogger(__name__)

class QuantService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_service = WalletService(db)

    async def get_active_vaults(self) -> List[StrategyVault]:
        stmt = select(StrategyVault).where(StrategyVault.status == "active").order_by(StrategyVault.historical_roi.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def stake_in_vault(self, user_id: int, vault_id: int, amount: Decimal) -> UserVaultPosition:
        vault = await self.db.get(StrategyVault, vault_id)
        if not vault:
            raise ValueError("Vault not found")
        if vault.status != "active":
            raise ValueError("Vault is not active")
        if vault.total_staked + amount > vault.max_cap:
            raise ValueError("Vault capacity reached")

        # Debit user wallet
        wallet = await self.wallet_service.get_or_create_wallet(user_id)
        await self.wallet_service.debit(
            wallet.id, user_id, Currency.VITCOIN, amount, "stake_vault",
            reference=f"Stake in {vault.name}"
        )

        # Update position
        stmt = select(UserVaultPosition).where(
            UserVaultPosition.user_id == user_id,
            UserVaultPosition.vault_id == vault_id
        )
        pos = (await self.db.execute(stmt)).scalar_one_or_none()

        if pos:
            pos.staked_balance += amount
        else:
            pos = UserVaultPosition(
                user_id=user_id,
                vault_id=vault_id,
                staked_balance=amount,
                entry_roi=vault.historical_roi
            )
            self.db.add(pos)

        vault.total_staked += amount
        await self.db.commit()
        await self.db.refresh(pos)
        return pos

    async def harvest_yield(self, user_id: int, vault_id: int) -> Decimal:
        stmt = select(UserVaultPosition).where(
            UserVaultPosition.user_id == user_id,
            UserVaultPosition.vault_id == vault_id
        )
        pos = (await self.db.execute(stmt)).scalar_one_or_none()
        if not pos or pos.yield_earned <= 0:
            return Decimal("0")

        yield_to_claim = pos.yield_earned
        pos.yield_earned = Decimal("0")

        # Credit user wallet
        wallet = await self.wallet_service.get_or_create_wallet(user_id)
        await self.wallet_service.credit(
            wallet.id, user_id, Currency.VITCOIN, yield_to_claim, "harvest_yield",
            reference=f"Harvest from vault {vault_id}"
        )

        await self.db.commit()
        return yield_to_claim

    async def sync_vault_performance(self, vault_id: int, new_roi: float, win_rate: float):
        """Update vault metrics based on latest settled matches."""
        vault = await self.db.get(StrategyVault, vault_id)
        if not vault: return

        old_roi = float(vault.historical_roi)
        vault.historical_roi = Decimal(str(new_roi))
        vault.win_rate = Decimal(str(win_rate))
        vault.last_rebalanced_at = datetime.now(timezone.utc)

        # If ROI increased, distribute partial yield to stakers
        # This is a simplified model for the MVP
        if new_roi > old_roi:
            improvement = Decimal(str(new_roi - old_roi))
            # Distribute 50% of the ROI improvement as instant yield to current stakers
            yield_per_unit = improvement * Decimal("0.5")

            stmt = update(UserVaultPosition).where(
                UserVaultPosition.vault_id == vault_id
            ).values(
                yield_earned=UserVaultPosition.yield_earned + (UserVaultPosition.staked_balance * yield_per_unit)
            )
            await self.db.execute(stmt)

        await self.db.commit()

    async def bootstrap_default_vaults(self):
        """Create initial vaults based on standard strategies."""
        defaults = [
            {"name": "Home Steamroller", "slug": "home-steamroller", "filter": {"bet_side": "home", "confidence_gte": 0.65}, "roi": 8.5},
            {"name": "Draw Underrated", "slug": "draw-underrated", "filter": {"bet_side": "draw", "odds_range": [3.5, 10.0]}, "roi": 12.2},
            {"name": "Underdog Away Edge", "slug": "away-underdog", "filter": {"bet_side": "away", "odds_range": [3.0, 5.0]}, "roi": 5.4},
        ]

        for d in defaults:
            stmt = select(StrategyVault).where(StrategyVault.slug == d["slug"])
            existing = (await self.db.execute(stmt)).scalar_one_or_none()
            if not existing:
                v = StrategyVault(
                    name=d["name"],
                    slug=d["slug"],
                    strategy_filter=d["filter"],
                    historical_roi=Decimal(str(d["roi"])),
                    win_rate=Decimal("0.45"),
                    max_cap=Decimal("500000")
                )
                self.db.add(v)

        await self.db.commit()
