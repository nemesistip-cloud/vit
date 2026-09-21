import logging
from typing import Dict, Any, Optional
from app.core.kernel import Subsystem
from app.core.registry.models import ModuleMetadata, HealthStatus
from app.db.database import AsyncSessionLocal
from .sdk import WalletSDK
from .manager import WalletManager

logger = logging.getLogger(__name__)

class WalletSubsystem(Subsystem):
    name = "wallet"
    dependencies = ["config", "observability", "persistence", "database", "redis", "blockchain"]
    def __init__(self, kernel):
        super().__init__(kernel)
        self._sdk = None
        self._metadata = ModuleMetadata(module_id=self.name, name="Wallet Platform", owner="core", domain="finance", version="1.0.0", capabilities=["WalletLifecycle", "AccountRegistry", "BalanceEngine", "AssetRegistry", "WalletSDK"], dependencies=self.dependencies)
    async def _on_initialize(self, config: Dict[str, Any]):
        self._sdk = WalletSDK(self)
    async def _on_start(self):
        async with AsyncSessionLocal() as session:
            try:
                manager = WalletManager(session)
                await manager.register_asset("VIT", "VIT Native Token", precision=18, asset_type="native")
                await manager.register_asset("USDT", "Tether USD", precision=6, asset_type="fungible")
                await manager.register_asset("NGN", "Nigerian Naira", precision=2, asset_type="fiat")
                await session.commit()
            except Exception as e:
                logger.error(f"[wallet] Failed to start Wallet Subsystem: {e}")
                await session.rollback()
                self.error_count += 1
                raise e
    def get_sdk(self) -> WalletSDK:
        return self._sdk
    async def health_check(self) -> bool:
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            return True
        except Exception: return False
    async def get_diagnostics(self) -> Dict[str, Any]:
        diags = await super().get_diagnostics()
        async with AsyncSessionLocal() as session:
            from sqlalchemy import func, select
            from .models import CoreWallet, CoreAccount
            total_wallets = await session.scalar(select(func.count(CoreWallet.id)))
            total_accounts = await session.scalar(select(func.count(CoreAccount.id)))
        diags.update({"total_wallets": total_wallets, "total_accounts": total_accounts, "version": self._metadata.version, "capabilities": self._metadata.capabilities})
        return diags
