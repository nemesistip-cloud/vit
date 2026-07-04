import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from app.core.event_bus import event_bus
from .models import CoreBalance, CoreWalletAudit, CoreAsset
from .repository import BalanceRepository, WalletAuditRepository
from .cache import WalletCache

logger = logging.getLogger(__name__)

class BalanceEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.balance_repo = BalanceRepository(session)
        self.audit_repo = WalletAuditRepository(session)
    async def update_balance(self, wallet_id: str, asset_symbol: str, amount: Decimal, balance_type: str = "confirmed", actor_id: Optional[str] = None, reference_id: Optional[str] = None, metadata: Optional[Dict] = None) -> Decimal:
        stmt = select(CoreBalance).where(and_(CoreBalance.wallet_id == wallet_id, CoreBalance.asset_symbol == asset_symbol)).with_for_update()
        res = await self.session.execute(stmt)
        balance_obj = res.scalar_one_or_none()
        if not balance_obj:
            stmt_asset = select(CoreAsset).where(CoreAsset.symbol == asset_symbol)
            asset_res = await self.session.execute(stmt_asset)
            if not asset_res.scalar_one_or_none():
                raise ValueError(f"Asset {asset_symbol} not registered.")
            balance_obj = CoreBalance(wallet_id=wallet_id, asset_symbol=asset_symbol, confirmed_balance=Decimal("0"), pending_balance=Decimal("0"), reserved_balance=Decimal("0"))
            self.session.add(balance_obj)
            await self.session.flush()
        prev_confirmed = balance_obj.confirmed_balance
        prev_pending = balance_obj.pending_balance
        prev_reserved = balance_obj.reserved_balance
        if balance_type == "confirmed":
            balance_obj.confirmed_balance += amount
        elif balance_type == "pending":
            balance_obj.pending_balance += amount
        elif balance_type == "reserved":
            if amount > 0:
                spendable = balance_obj.confirmed_balance - balance_obj.reserved_balance
                if amount > spendable:
                    raise ValueError(f"Insufficient spendable balance for {asset_symbol} to reserve {amount}")
            balance_obj.reserved_balance += amount
        else:
            raise ValueError(f"Invalid balance type: {balance_type}")
        if balance_obj.confirmed_balance < 0 or balance_obj.pending_balance < 0 or balance_obj.reserved_balance < 0:
            if not metadata or not metadata.get("allow_negative"):
                raise ValueError(f"Insufficient {balance_type} balance for {asset_symbol} in wallet {wallet_id}")
        audit = CoreWalletAudit(wallet_id=wallet_id, action="BalanceUpdate", actor_id=actor_id, prev_state={"confirmed": str(prev_confirmed), "pending": str(prev_pending), "reserved": str(prev_reserved)}, new_state={"confirmed": str(balance_obj.confirmed_balance), "pending": str(balance_obj.pending_balance), "reserved": str(balance_obj.reserved_balance)}, reference_id=reference_id, metadata_json=metadata)
        self.session.add(audit)
        await WalletCache.invalidate_balances(wallet_id)
        await event_bus.publish("BalanceChanged", {"wallet_id": wallet_id, "asset": asset_symbol, "type": balance_type, "delta": str(amount), "new_total": str(getattr(balance_obj, f"{balance_type}_balance")), "reference_id": reference_id}, sender="balance_engine")
        return getattr(balance_obj, f"{balance_type}_balance")
    async def get_spendable_balance(self, wallet_id: str, asset_symbol: str) -> Decimal:
        stmt = select(CoreBalance).where(and_(CoreBalance.wallet_id == wallet_id, CoreBalance.asset_symbol == asset_symbol))
        res = await self.session.execute(stmt)
        balance = res.scalar_one_or_none()
        if not balance: return Decimal("0")
        return max(Decimal("0"), balance.confirmed_balance - balance.reserved_balance)
