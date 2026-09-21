import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any
from app.db.database import AsyncSessionLocal
from .manager import WalletManager
from .models import AccountType

logger = logging.getLogger(__name__)

class WalletSDK:
    def __init__(self, subsystem):
        self.subsystem = subsystem
    async def create_wallet(self, owner_id: str, name: str = "Primary Wallet", account_type: str = "individual") -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            manager = WalletManager(session)
            accounts = await manager.account_repo.get_by_owner(owner_id)
            if accounts: account = accounts[0]
            else: account = await manager.create_account(owner_id, account_type=AccountType(account_type))
            wallet = await manager.create_wallet(account.id, name=name)
            await session.commit()
            return await manager.get_wallet_summary(wallet.id)
    async def get_balance(self, wallet_id: str, asset: str = "VIT") -> Decimal:
        async with AsyncSessionLocal() as session:
            manager = WalletManager(session)
            return await manager.engine.get_spendable_balance(wallet_id, asset)
    async def get_all_balances(self, wallet_id: str) -> Dict[str, Decimal]:
        async with AsyncSessionLocal() as session:
            manager = WalletManager(session)
            balances = await manager.engine.balance_repo.get_all_wallet_balances(wallet_id)
            return {b.asset_symbol: b.confirmed_balance for b in balances}
    async def update_balance(self, wallet_id: str, asset: str, amount: Decimal, type: str = "confirmed", actor: str = "system", ref: Optional[str] = None) -> Decimal:
        async with AsyncSessionLocal() as session:
            manager = WalletManager(session)
            new_balance = await manager.engine.update_balance(wallet_id=wallet_id, asset_symbol=asset, amount=amount, balance_type=type, actor_id=actor, reference_id=ref)
            await session.commit()
            return new_balance
    async def validate_address(self, network: str, address: str) -> bool:
        async with AsyncSessionLocal() as session:
            manager = WalletManager(session)
            addr = await manager.address_repo.get_by_address(network, address)
            return addr is not None
    async def list_wallets(self, owner_id: str) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            manager = WalletManager(session)
            accounts = await manager.account_repo.get_by_owner(owner_id)
            all_wallets = []
            for acc in accounts:
                wallets = await manager.wallet_repo.get_by_account(acc.id)
                for w in wallets:
                    all_wallets.append(await manager.get_wallet_summary(w.id))
            return all_wallets
    async def get_transaction_history(self, wallet_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            manager = WalletManager(session)
            history = await manager.engine.audit_repo.get_wallet_history(wallet_id, limit=limit)
            return [{"action": h.action, "actor": h.actor_id, "prev": h.prev_state, "new": h.new_state, "ref": h.reference_id, "ts": h.timestamp.isoformat()} for h in history]
