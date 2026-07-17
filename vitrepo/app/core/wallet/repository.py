from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from app.core.persistence.repository import BaseRepository, RepositoryRegistry
from .models import CoreAccount, CoreWallet, CoreAsset, CoreBalance, CoreAddress, CoreWalletAudit

class AccountRepository(BaseRepository[CoreAccount]):
    model = CoreAccount
    async def get_by_owner(self, owner_id: str) -> List[CoreAccount]:
        stmt = select(self.model).where(self.model.owner_id == owner_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()

class WalletRepository(BaseRepository[CoreWallet]):
    model = CoreWallet
    async def get_by_account(self, account_id: str) -> List[CoreWallet]:
        stmt = select(self.model).where(self.model.account_id == account_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()

class AssetRepository(BaseRepository[CoreAsset]):
    model = CoreAsset
    async def get_by_symbol(self, symbol: str) -> Optional[CoreAsset]:
        stmt = select(self.model).where(self.model.symbol == symbol)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

class BalanceRepository(BaseRepository[CoreBalance]):
    model = CoreBalance
    async def get_wallet_balance(self, wallet_id: str, asset_symbol: str) -> Optional[CoreBalance]:
        stmt = select(self.model).where(and_(self.model.wallet_id == wallet_id, self.model.asset_symbol == asset_symbol))
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
    async def get_all_wallet_balances(self, wallet_id: str) -> List[CoreBalance]:
        stmt = select(self.model).where(self.model.wallet_id == wallet_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()

class AddressRepository(BaseRepository[CoreAddress]):
    model = CoreAddress
    async def get_by_address(self, network: str, address: str) -> Optional[CoreAddress]:
        stmt = select(self.model).where(and_(self.model.network == network, self.model.address == address))
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()
    async def get_wallet_addresses(self, wallet_id: str) -> List[CoreAddress]:
        stmt = select(self.model).where(self.model.wallet_id == wallet_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()

class WalletAuditRepository(BaseRepository[CoreWalletAudit]):
    model = CoreWalletAudit
    async def get_wallet_history(self, wallet_id: str, limit: int = 50) -> List[CoreWalletAudit]:
        stmt = select(self.model).where(self.model.wallet_id == wallet_id).order_by(self.model.timestamp.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()

RepositoryRegistry.register("core_account", AccountRepository)
RepositoryRegistry.register("core_wallet", WalletRepository)
RepositoryRegistry.register("core_asset", AssetRepository)
RepositoryRegistry.register("core_balance", BalanceRepository)
RepositoryRegistry.register("core_address", AddressRepository)
RepositoryRegistry.register("core_wallet_audit", WalletAuditRepository)
