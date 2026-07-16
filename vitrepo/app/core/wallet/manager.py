import logging
import asyncio
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.event_bus import event_bus
from .models import CoreAccount, CoreWallet, CoreAddress, CoreAsset, WalletStatus, AccountType
from .repository import AccountRepository, WalletRepository, AddressRepository, AssetRepository
from .engine import BalanceEngine
from .cache import WalletCache

logger = logging.getLogger(__name__)

class WalletManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.account_repo = AccountRepository(session)
        self.wallet_repo = WalletRepository(session)
        self.address_repo = AddressRepository(session)
        self.asset_repo = AssetRepository(session)
        self.engine = BalanceEngine(session)
    async def create_account(self, owner_id: str, account_type: AccountType = AccountType.INDIVIDUAL, name: Optional[str] = None) -> CoreAccount:
        account = await self.account_repo.create(owner_id=owner_id, account_type=account_type, name=name)
        logger.info(f"Created account {account.id} for owner {owner_id}")
        return account
    async def create_wallet(self, account_id: str, name: str = "Primary Wallet") -> CoreWallet:
        wallet = await self.wallet_repo.create(account_id=account_id, name=name)
        try:
            await self.generate_address(wallet.id, "vit")
        except Exception as e:
            logger.warning(f"Failed to generate initial VIT address for wallet {wallet.id}: {e}")
        await event_bus.publish("WalletCreated", {"wallet_id": wallet.id, "account_id": account_id, "name": name}, sender="wallet_manager")
        return wallet
    async def generate_address(self, wallet_id: str, network: str) -> CoreAddress:
        existing = await self.address_repo.get_wallet_addresses(wallet_id)
        for addr in existing:
            if addr.network == network: return addr
        address_str = f"vit_{wallet_id[:16]}"
        address = await self.address_repo.create(wallet_id=wallet_id, network=network, address=address_str)
        await event_bus.publish("AddressGenerated", {"wallet_id": wallet_id, "network": network, "address": address_str}, sender="wallet_manager")
        return address
    async def register_asset(self, symbol: str, name: str, precision: int = 18, asset_type: str = "native") -> CoreAsset:
        existing = await self.asset_repo.get_by_symbol(symbol)
        if existing: return existing
        asset = await self.asset_repo.create(symbol=symbol, name=name, precision=precision, asset_type=asset_type)
        await event_bus.publish("AssetRegistered", {"symbol": symbol, "name": name, "type": asset_type}, sender="wallet_manager")
        return asset
    async def get_wallet_summary(self, wallet_id: str) -> Dict[str, Any]:
        cached_meta = await WalletCache.get_wallet_metadata(wallet_id)
        cached_balances = await WalletCache.get_balances(wallet_id)
        if cached_meta and cached_balances is not None:
            return {**cached_meta, "balances": cached_balances}
        wallet = await self.wallet_repo.get_by_id(wallet_id)
        if not wallet: raise ValueError(f"Wallet {wallet_id} not found.")
        balances = await self.engine.balance_repo.get_all_wallet_balances(wallet_id)
        addresses = await self.address_repo.get_wallet_addresses(wallet_id)
        summary = {"id": wallet.id, "account_id": wallet.account_id, "name": wallet.name, "status": wallet.status, "balances": {b.asset_symbol: str(b.confirmed_balance) for b in balances}, "addresses": {a.network: a.address for a in addresses}}
        await WalletCache.set_wallet_metadata(wallet_id, {"id": wallet.id, "account_id": wallet.account_id, "name": wallet.name, "status": wallet.status, "addresses": summary["addresses"]})
        await WalletCache.set_balances(wallet_id, {b.asset_symbol: b.confirmed_balance for b in balances})
        return summary
