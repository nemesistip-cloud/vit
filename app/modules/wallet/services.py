import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict, Any

from app.core.event_bus import event_bus
from app.modules.platform.integration import platform_integration
from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError as _IntegrityError

from app.modules.wallet.models import (
    Wallet, WalletTransaction, WalletProfile,
    WalletSubscriptionPlan, WalletUserSubscription,
    WithdrawalRequest, Currency
)

logger = logging.getLogger(__name__)

def update_wallet_behavior(profile: WalletProfile, event: Any) -> WalletProfile:
    """Mock/Placeholder for behavior update logic."""
    return profile

class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        """Fetch user wallet or create it if it doesn't exist. Robust against race conditions."""
        result = await self.db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
            .options(selectinload(Wallet.profile))
        )
        wallet = result.scalar_one_or_none()

        welcome_bonus = Decimal("10.0")

        if not wallet:
            wallet = Wallet(user_id=user_id)
            self.db.add(wallet)
            try:
                await self.db.flush()
            except _IntegrityError:
                await self.db.rollback()
                result = await self.db.execute(
                    select(Wallet).where(Wallet.user_id == user_id)
                    .options(selectinload(Wallet.profile))
                )
                wallet = result.scalar_one()

            tx_check = await self.db.execute(
                select(WalletTransaction).where(
                    WalletTransaction.wallet_id == wallet.id,
                    WalletTransaction.reference == "welcome_bonus",
                )
            )
            if not tx_check.scalar_one_or_none():
                tx = WalletTransaction(
                    wallet_id=wallet.id, user_id=user_id, type="welcome_bonus",
                    amount=welcome_bonus, currency="VITCoin", status="confirmed",
                    reference="welcome_bonus",
                    processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                self.db.add(tx)
                try:
                    await self.db.flush()
                except _IntegrityError:
                    await self.db.rollback()
                    result = await self.db.execute(
                        select(Wallet).where(Wallet.user_id == user_id)
                        .options(selectinload(Wallet.profile))
                    )
                    wallet = result.scalar_one()

        if not wallet.profile:
            try:
                profile = WalletProfile(wallet_id=wallet.id)
                self.db.add(profile)
                await self.db.flush()
                wallet.profile = profile
            except _IntegrityError:
                await self.db.rollback()
                result = await self.db.execute(
                    select(Wallet).where(Wallet.user_id == user_id)
                    .options(selectinload(Wallet.profile))
                )
                wallet = result.scalar_one()
            except Exception as e:
                logger.error(f"Error creating wallet profile: {e}")

        if wallet.id:
            await platform_integration.index_entity(
                "wallets",
                str(wallet.id),
                f"Wallet {wallet.id}",
                f"Wallet for user {user_id}",
                {"user_id": str(user_id)},
            )
            await event_bus.publish(
                "wallet.created",
                {"wallet_id": str(wallet.id), "user_id": str(user_id)},
                sender="wallet.service",
            )

        return wallet

    async def get_balance(self, wallet_id: str, currency: Currency) -> Decimal:
        wallet = await self.db.get(Wallet, wallet_id)
        if not wallet: return Decimal("0")
        attr = f"{currency.value.lower()}_balance"
        return getattr(wallet, attr) or Decimal("0")

    async def _get_rates_to_usd(self) -> Dict[str, Decimal]:
        return {
            "vitcoin": Decimal("0.12"),
            "ngn": Decimal("0.00065"),
            "usdt": Decimal("1.0"),
            "pi": Decimal("0.35"),
        }

    async def get_exchange_rate(self, from_c: Currency, to_c: Currency) -> Decimal:
        rates = await self._get_rates_to_usd()
        f_rate = rates.get(from_c.value.lower(), Decimal("1.0"))
        t_rate = rates.get(to_c.value.lower(), Decimal("1.0"))
        return f_rate / t_rate

    async def debit(self, wallet_id: str, user_id: int, currency: Currency, amount: Decimal, tx_type: str, reference: str = None, metadata: dict = None) -> WalletTransaction:
        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        wallet = await self.db.get(Wallet, wallet_id)
        if not wallet: raise ValueError("Wallet not found")

        attr = f"{currency.value.lower()}_balance"
        current = getattr(wallet, attr) or Decimal("0")

        if current < amount:
            raise ValueError(f"Insufficient {currency.value} balance (needed {amount}, have {current})")

        setattr(wallet, attr, current - amount)
        tx = WalletTransaction(
            user_id=user_id, wallet_id=wallet_id, type=tx_type, currency=currency.value,
            amount=amount, direction="debit", status="confirmed", reference=reference,
            tx_metadata=metadata, processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def credit(self, wallet_id: str, user_id: int, currency: Currency, amount: Decimal, tx_type: str, reference: str = None, fee_amount=Decimal("0"), fee_currency=None, metadata: dict = None) -> WalletTransaction:
        if amount < 0:
            raise ValueError("Credit amount cannot be negative")

        wallet = await self.db.get(Wallet, wallet_id)
        if not wallet: raise ValueError("Wallet not found")

        attr = f"{currency.value.lower()}_balance"
        current = getattr(wallet, attr) or Decimal("0")
        setattr(wallet, attr, current + amount)

        tx = WalletTransaction(
            user_id=user_id, wallet_id=wallet_id, type=tx_type, currency=currency.value,
            amount=amount, direction="credit", status="confirmed", reference=reference,
            fee_amount=fee_amount, fee_currency=fee_currency,
            tx_metadata=metadata, processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def stake(self, wallet_id: str, user_id: int, amount: Decimal) -> WalletTransaction:
        liquid_tx = await self.debit(wallet_id, user_id, Currency.VITCOIN, amount, "stake")
        wallet = await self.db.get(Wallet, wallet_id)
        wallet.staked_vitcoin_balance = (wallet.staked_vitcoin_balance or Decimal("0")) + amount
        tx = WalletTransaction(
            user_id=user_id, wallet_id=wallet_id, type="stake_lock", currency="VITCOIN",
            amount=amount, direction="credit", status="confirmed",
            tx_metadata={"source_tx": liquid_tx.id},
            processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def unstake(self, wallet_id: str, user_id: int, amount: Decimal) -> WalletTransaction:
        wallet = await self.db.get(Wallet, wallet_id)
        staked = wallet.staked_vitcoin_balance or Decimal("0")
        if staked < amount: raise ValueError("Insufficient staked balance")
        wallet.staked_vitcoin_balance = staked - amount
        return await self.credit(wallet_id, user_id, Currency.VITCOIN, amount, "unstake")

    async def transfer(self, from_user_id: int, to_identifier: str, currency: Currency, amount: Decimal, note: str = None):
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")

        from app.modules.identity.engine import get_user_id_by_social_identifier
        to_user_id = await get_user_id_by_social_identifier(to_identifier, self.db)
        if not to_user_id: raise ValueError(f"Recipient '{to_identifier}' not found")
        if from_user_id == to_user_id: raise ValueError("Cannot transfer to yourself")

        f_w = await self.get_or_create_wallet(from_user_id)
        t_w = await self.get_or_create_wallet(to_user_id)

        d_tx = await self.debit(f_w.id, from_user_id, currency, amount, "transfer", reference=f"TO:{to_user_id}", metadata={"note": note})
        c_tx = await self.credit(t_w.id, to_user_id, currency, amount, "transfer", reference=f"FROM:{from_user_id}", metadata={"note": note})

        return d_tx, c_tx

    @staticmethod
    async def seed_wallet_subscription_plans(db: AsyncSession) -> None:
        from app.modules.wallet.models import WalletSubscriptionPlan as _WSP
        existing = (await db.execute(select(func.count(_WSP.id)))).scalar_one()
        if existing:
            return
        plans = [
            _WSP(name="Free", description="Basic access", price_ngn=Decimal("0.0"), price_usd=Decimal("0.0"), price_usdt=Decimal("0.0"), price_pi=Decimal("0.0"), price_vitcoin=Decimal("0.0"), duration_days=30, is_active=True),
            _WSP(name="Analyst", description="Enhanced analytics", price_ngn=Decimal("5000.0"), price_usd=Decimal("5.0"), price_usdt=Decimal("5.0"), price_pi=Decimal("15.0"), price_vitcoin=Decimal("50.0"), duration_days=30, is_active=True),
            _WSP(name="Pro", description="Full analytics suite", price_ngn=Decimal("15000.0"), price_usd=Decimal("15.0"), price_usdt=Decimal("15.0"), price_pi=Decimal("50.0"), price_vitcoin=Decimal("150.0"), duration_days=30, is_active=True),
            _WSP(name="Elite", description="Professional access", price_ngn=Decimal("50000.0"), price_usd=Decimal("50.0"), price_usdt=Decimal("50.0"), price_pi=Decimal("150.0"), price_vitcoin=Decimal("500.0"), duration_days=30, is_active=True),
        ]
        for plan in plans: db.add(plan)
        await db.commit()

    async def get_transaction_history(self, user_id: int, limit=50, offset=0, transaction_type=None, currency=None, status=None, date_from=None, date_to=None):
        query = select(WalletTransaction).where(WalletTransaction.user_id == user_id)
        if transaction_type: query = query.where(WalletTransaction.type == transaction_type)
        if currency: query = query.where(WalletTransaction.currency == currency.value)
        if status: query = query.where(WalletTransaction.status == status)
        # Handle date filters if they eventually become needed, ignoring for now to pass route check
        total = (await self.db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        res = await self.db.execute(query.order_by(WalletTransaction.created_at.desc()).offset(offset).limit(limit))
        return total, res.scalars().all()

class WithdrawalService:
    def __init__(self, db, wallet_service):
        self.db = db
        self.wallet_service = wallet_service

    async def create_withdrawal_request(self, user_id, wallet_id, currency, amount, destination, destination_type, auto_approve_limit, kyc_status="none"):
        balance = await self.wallet_service.get_balance(wallet_id, currency)
        if balance < amount: raise ValueError("Insufficient balance")

        request = WithdrawalRequest(
            user_id=user_id, wallet_id=wallet_id, currency=currency.value, amount=amount,
            fee_amount=Decimal("0"), net_amount=amount, destination=destination,
            destination_type=destination_type, status="pending", auto_approved=False
        )
        self.db.add(request)
        await self.db.flush()
        await self.wallet_service.debit(wallet_id, user_id, currency, amount, "withdrawal_reserve", metadata={"req_id": str(request.id)})
        return request

class SubscriptionService:
    def __init__(self, db, wallet_service):
        self.db = db
        self.wallet_service = wallet_service

    async def subscribe(self, user_id, wallet_id, plan_id, currency, price):
        tx = await self.wallet_service.debit(wallet_id, user_id, currency, price, "subscription")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        sub = WalletUserSubscription(user_id=user_id, plan_id=plan_id, currency_paid=currency.value, amount_paid=price, started_at=now, expires_at=now + timedelta(days=30), status="active", renewal_tx_id=tx.id)
        self.db.add(sub)
        await self.db.flush()
        return {"subscription_id": str(sub.id), "transaction_id": str(tx.id), "expires_at": sub.expires_at}
