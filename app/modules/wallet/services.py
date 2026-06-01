# app/modules/wallet/services.py
"""Wallet business logic and transaction handling."""

import logging
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.modules.wallet.models import (
    Wallet, WalletTransaction, WalletSubscriptionPlan, WalletUserSubscription,
    Currency, WithdrawalRequest,
)

logger = logging.getLogger(__name__)


class WalletService:
    """Core wallet operations."""

    # Default exchange rates relative to USD (1 unit of currency = X USD).
    _DEFAULT_RATES_TO_USD: dict = {
        "NGN":     Decimal("0.000633"),
        "USD":     Decimal("1.0"),
        "USDT":    Decimal("1.0"),
        "PI":      Decimal("0.314159"),
        "VITCoin": Decimal("0.10"),
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _rate_lookup(rates: dict, currency_value: str):
        if currency_value in rates:
            return rates[currency_value]
        cv = currency_value.lower()
        for k, v in rates.items():
            if k.lower() == cv:
                return v
        return None

    async def _get_rates_to_usd(self) -> dict:
        try:
            from app.modules.wallet.models import PlatformConfig as _PC
            result = await self.db.execute(select(_PC).where(_PC.key == "exchange_rates_usd"))
            row = result.scalar_one_or_none()
            merged = dict(self._DEFAULT_RATES_TO_USD)
            if row and isinstance(row.value, dict):
                lower_to_canon = {k.lower(): k for k in merged.keys()}
                for k, v in row.value.items():
                    try:
                        canon = lower_to_canon.get(k.lower(), k)
                        merged[canon] = Decimal(str(v))
                    except Exception:
                        pass
            try:
                from app.modules.wallet.models import VITCoinPriceHistory as _VPH
                live = await self.db.execute(select(_VPH).order_by(_VPH.calculated_at.desc()).limit(1))
                latest = live.scalar_one_or_none()
                if latest and latest.price_usd and Decimal(latest.price_usd) > Decimal("0"):
                    merged["VITCoin"] = Decimal(latest.price_usd)
            except Exception:
                pass
            return merged
        except Exception as _e:
            logger.warning("EXCHANGE_RATE_FALLBACK failure: %s", _e)
            return dict(self._DEFAULT_RATES_TO_USD)

    async def get_exchange_rate(self, from_currency: "Currency", to_currency: "Currency") -> Decimal:
        rates = await self._get_rates_to_usd()
        from_usd = self._rate_lookup(rates, from_currency.value)
        to_usd   = self._rate_lookup(rates, to_currency.value)
        if from_usd is None or to_usd is None:
            raise ValueError(f"Rate not found for {from_currency.value} or {to_currency.value}")
        return from_usd / to_usd

    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            wallet = Wallet(user_id=user_id)
            self.db.add(wallet)
            await self.db.flush()
        return wallet

    async def get_balance(self, wallet_id: str, currency: Currency) -> Decimal:
        wallet = await self.db.get(Wallet, wallet_id)
        if not wallet: return Decimal("0")
        attr = f"{currency.value.lower()}_balance"
        return getattr(wallet, attr, Decimal("0"))

    async def credit(self, wallet_id, user_id, currency, amount, tx_type, reference=None, metadata=None, fee_amount=Decimal("0"), fee_currency=None) -> WalletTransaction:
        """Internal helper for balance credits."""
        if amount <= 0: raise ValueError("Amount must be positive")
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one_or_none()
        if not wallet: raise ValueError("Wallet not found")
        if wallet.is_frozen: raise ValueError("Wallet frozen")
        attr = f"{currency.value.lower()}_balance"
        setattr(wallet, attr, getattr(wallet, attr) + amount)
        tx = WalletTransaction(
            user_id=user_id, wallet_id=wallet_id, type=tx_type, currency=currency.value,
            amount=amount, direction="credit", status="confirmed", reference=reference,
            fee_amount=fee_amount, fee_currency=fee_currency, tx_metadata=metadata,
            processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def debit(self, wallet_id, user_id, currency, amount, tx_type, reference=None, metadata=None, fee_amount=Decimal("0"), fee_currency=None) -> WalletTransaction:
        """Internal helper for balance debits."""
        if amount <= 0: raise ValueError("Amount must be positive")
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one_or_none()
        if not wallet: raise ValueError("Wallet not found")
        if wallet.is_frozen: raise ValueError("Wallet frozen")
        attr = f"{currency.value.lower()}_balance"
        curr_bal = getattr(wallet, attr)
        if curr_bal < amount: raise ValueError(f"Insufficient {currency.value} balance")
        setattr(wallet, attr, curr_bal - amount)
        tx = WalletTransaction(
            user_id=user_id, wallet_id=wallet_id, type=tx_type, currency=currency.value,
            amount=amount, direction="debit", status="confirmed", reference=reference,
            fee_amount=fee_amount, fee_currency=fee_currency, tx_metadata=metadata,
            processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(tx)
        await self.db.flush()
        return tx

    # ── Core Transaction Engine (v2.0) ────────────────────────────────────────

    async def deposit(self, wallet_id, user_id, currency, amount, reference=None) -> WalletTransaction:
        return await self.credit(wallet_id, user_id, currency, amount, "deposit", reference=reference)

    async def withdraw(self, wallet_id, user_id, currency, amount, reference=None) -> WalletTransaction:
        return await self.debit(wallet_id, user_id, currency, amount, "withdrawal", reference=reference)

    async def stake(self, wallet_id: str, user_id: int, amount: Decimal) -> WalletTransaction:
        liquid_tx = await self.debit(wallet_id, user_id, Currency.VITCOIN, amount, "stake")
        wallet = await self.db.get(Wallet, wallet_id)
        wallet.staked_vitcoin_balance += amount
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
        if wallet.staked_vitcoin_balance < amount: raise ValueError("Insufficient staked balance")
        wallet.staked_vitcoin_balance -= amount
        return await self.credit(wallet_id, user_id, Currency.VITCOIN, amount, "unstake")

    async def reward_credit(self, wallet_id, user_id, currency, amount, reason) -> WalletTransaction:
        return await self.credit(wallet_id, user_id, currency, amount, "reward", metadata={"reason": reason})

    async def fee_charge(self, wallet_id, user_id, currency, amount, service) -> WalletTransaction:
        return await self.debit(wallet_id, user_id, currency, amount, "fee", metadata={"service": service})

    async def convert_currency(self, wallet_id, user_id, from_currency, to_currency, amount, conversion_fee_pct):
        if from_currency == to_currency: raise ValueError("Cannot convert same currency")
        debit_tx = await self.debit(wallet_id, user_id, from_currency, amount, "conversion")
        rate = await self.get_exchange_rate(from_currency, to_currency)
        fee = amount * (conversion_fee_pct / Decimal("100"))
        converted_amount = (amount * rate) - (fee * rate)
        credit_tx = await self.credit(
            wallet_id, user_id, to_currency, converted_amount, "conversion",
            fee_amount=fee, fee_currency=from_currency.value,
            metadata={"from": from_currency.value, "to": to_currency.value, "rate": float(rate)}
        )
        return debit_tx, credit_tx, converted_amount

    async def transfer(self, from_user_id, to_identifier, currency, amount, note=None):
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
        """Seed default wallet subscription plans if they don't exist yet."""
        from app.modules.wallet.models import WalletSubscriptionPlan as _WSP
        existing = (await db.execute(select(func.count(_WSP.id)))).scalar_one()
        if existing:
            return
        plans = [
            _WSP(
                name="Free",
                description="Basic access — no cost",
                features=["5 predictions/day", "TheSportsDB data", "Basic analytics"],
                price_ngn=Decimal("0.00"), price_usd=Decimal("0.00"),
                price_usdt=Decimal("0.00"), price_pi=Decimal("0.00"),
                price_vitcoin=Decimal("0.00"), duration_days=30, is_active=True,
            ),
            _WSP(
                name="Analyst",
                description="Enhanced intelligence for serious bettors",
                features=["20 predictions/day", "Multi-source odds", "CLV tracking", "AI insights"],
                price_ngn=Decimal("5000.00"), price_usd=Decimal("5.00"),
                price_usdt=Decimal("5.00"), price_pi=Decimal("15.00"),
                price_vitcoin=Decimal("50.00"), duration_days=30, is_active=True,
            ),
            _WSP(
                name="Pro",
                description="Full intelligence suite with live data",
                features=["Unlimited predictions", "Live odds", "22 AI agents", "API access", "Priority support"],
                price_ngn=Decimal("15000.00"), price_usd=Decimal("15.00"),
                price_usdt=Decimal("15.00"), price_pi=Decimal("50.00"),
                price_vitcoin=Decimal("150.00"), duration_days=30, is_active=True,
            ),
            _WSP(
                name="Elite",
                description="Institutional-grade access with full blockchain features",
                features=["Unlimited predictions", "On-chain verification", "DID identity", "Oracle access", "White-glove support"],
                price_ngn=Decimal("50000.00"), price_usd=Decimal("50.00"),
                price_usdt=Decimal("50.00"), price_pi=Decimal("150.00"),
                price_vitcoin=Decimal("500.00"), duration_days=30, is_active=True,
            ),
        ]
        for plan in plans:
            db.add(plan)
        await db.commit()
        logger.info("[wallet] Seeded %d wallet subscription plans", len(plans))

    async def get_transaction_history(self, user_id, limit=50, offset=0, transaction_type=None, currency=None, status=None, date_from=None, date_to=None):
        query = select(WalletTransaction).where(WalletTransaction.user_id == user_id)
        if transaction_type: query = query.where(WalletTransaction.type == transaction_type)
        if currency: query = query.where(WalletTransaction.currency == currency.value)
        if status: query = query.where(WalletTransaction.status == status)
        total = (await self.db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        res = await self.db.execute(query.order_by(WalletTransaction.created_at.desc()).offset(offset).limit(limit))
        return total, res.scalars().all()


class WithdrawalService:
    def __init__(self, db, wallet_service):
        self.db = db
        self.wallet_service = wallet_service

    async def create_withdrawal_request(self, user_id, wallet_id, currency, amount, destination, destination_type, auto_approve_limit, kyc_status="none") -> WithdrawalRequest:
        from app.modules.identity.passport import PassportService
        passport = await PassportService.get_passport(self.db, user_id)
        trust_factor = max(0.5, min(passport.trust_score / 50.0, 2.0))
        adj_limit = auto_approve_limit * Decimal(str(round(trust_factor, 2)))

        _KYC_THRESHOLD_USD = Decimal("10.00")
        rates = await self.wallet_service._get_rates_to_usd()
        amount_usd = amount * rates.get(currency.value, Decimal("1.0"))
        if amount_usd > _KYC_THRESHOLD_USD and kyc_status not in ("approved", "verified"):
            raise ValueError("KYC required for >$10 withdrawals")

        balance = await self.wallet_service.get_balance(wallet_id, currency)
        if balance < amount: raise ValueError("Insufficient balance")
        auto_approved = amount <= adj_limit
        status = "auto_approved" if auto_approved else "pending"
        request = WithdrawalRequest(
            user_id=user_id, wallet_id=wallet_id, currency=currency.value, amount=amount,
            fee_amount=Decimal("0"), net_amount=amount, destination=destination,
            destination_type=destination_type, status=status, auto_approved=auto_approved,
        )
        self.db.add(request)
        await self.db.flush()
        await self.wallet_service.debit(wallet_id, user_id, currency, amount, "withdrawal" if auto_approved else "withdrawal_reserve", metadata={"req_id": str(request.id)})
        if auto_approved:
            request.processed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            request.status = "processed"
        return request


class SubscriptionService:
    def __init__(self, db, wallet_service):
        self.db = db
        self.wallet_service = wallet_service

    async def subscribe(self, user_id, wallet_id, plan_id, currency, price):
        tx = await self.wallet_service.debit(wallet_id, user_id, currency, price, "subscription")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        from app.modules.wallet.models import WalletSubscriptionPlan as _P
        p = (await self.db.execute(select(_P).where(_P.id == plan_id))).scalar_one_or_none()
        days = p.duration_days if p else 30
        sub = WalletUserSubscription(user_id=user_id, plan_id=plan_id, currency_paid=currency.value, amount_paid=price, started_at=now, expires_at=now + timedelta(days=days), status="active", renewal_tx_id=tx.id)
        self.db.add(sub)
        await self.db.flush()
        return {"subscription_id": str(sub.id), "transaction_id": str(tx.id), "expires_at": sub.expires_at}
