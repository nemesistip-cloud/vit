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
    # These serve as a fallback when the DB config is unavailable.
    # Update live values via the admin panel → PlatformConfig key "exchange_rates_usd".
    _DEFAULT_RATES_TO_USD: dict = {
        "NGN":     Decimal("0.000633"),   # 1 USD ≈ 1580 NGN
        "USD":     Decimal("1.0"),
        "USDT":    Decimal("1.0"),        # USDT pegged to USD
        "PI":      Decimal("0.314159"),   # 1 PI ≈ $0.314
        "VITCoin": Decimal("0.10"),       # initial price; updated by VITCoinPricingEngine
    }

    @staticmethod
    def _rate_lookup(rates: dict, currency_value: str):
        """Case-insensitive lookup against the rates dict."""
        if currency_value in rates:
            return rates[currency_value]
        cv = currency_value.lower()
        for k, v in rates.items():
            if k.lower() == cv:
                return v
        return None

    async def _get_rates_to_usd(self) -> dict:
        """
        Load live exchange rates from PlatformConfig.
        Falls back to class-level defaults when the DB entry is absent or malformed.
        Config key: "exchange_rates_usd"
        Expected value shape: {"NGN": 0.000633, "PI": 0.314159, "VITCOIN": 0.10}
        """
        try:
            from app.modules.wallet.models import PlatformConfig as _PC
            result = await self.db.execute(
                select(_PC).where(_PC.key == "exchange_rates_usd")
            )
            row = result.scalar_one_or_none()
            merged = dict(self._DEFAULT_RATES_TO_USD)
            if row and isinstance(row.value, dict):
                # Normalize keys: case-insensitive override of defaults so
                # admin-supplied keys like "vitcoin"/"VITCOIN" still match the
                # canonical enum value "VITCoin".
                lower_to_canon = {k.lower(): k for k in merged.keys()}
                for k, v in row.value.items():
                    try:
                        canon = lower_to_canon.get(k.lower(), k)
                        merged[canon] = Decimal(str(v))
                    except Exception:
                        pass
            # Always overlay the live VIT price from VITCoinPriceHistory so
            # conversions, the /exchange-rates endpoint, and analytics agree.
            try:
                from app.modules.wallet.models import VITCoinPriceHistory as _VPH
                live = await self.db.execute(
                    select(_VPH).order_by(_VPH.calculated_at.desc()).limit(1)
                )
                latest = live.scalar_one_or_none()
                if latest and latest.price_usd and Decimal(latest.price_usd) > Decimal("0"):
                    merged["VITCoin"] = Decimal(latest.price_usd)
            except Exception:
                pass
            return merged
        except Exception as _e:
            logger.warning(
                "EXCHANGE_RATE_FALLBACK could not load 'exchange_rates_usd' from "
                "PlatformConfig (%s) — using class-level defaults. Set this in "
                "admin → Currency to silence this warning.",
                _e,
            )
        else:
            logger.warning(
                "EXCHANGE_RATE_FALLBACK PlatformConfig 'exchange_rates_usd' is "
                "missing or malformed — using class-level defaults"
            )
        return dict(self._DEFAULT_RATES_TO_USD)

    async def get_exchange_rate(self, from_currency: "Currency", to_currency: "Currency") -> Decimal:
        """Return the exchange rate: how many to_currency units you get per 1 from_currency."""
        rates = await self._get_rates_to_usd()
        from_usd = self._rate_lookup(rates, from_currency.value)
        to_usd   = self._rate_lookup(rates, to_currency.value)

        if from_usd is None:
            raise ValueError(
                f"No exchange rate found for source currency '{from_currency.value}'. "
                "Cannot perform conversion."
            )
        if to_usd is None:
            raise ValueError(
                f"No exchange rate found for target currency '{to_currency.value}'. "
                "Cannot perform conversion."
            )
        if to_usd == Decimal("0"):
            raise ValueError(
                f"Exchange rate for '{to_currency.value}' is zero — conversion not possible."
            )
        return from_usd / to_usd

    @classmethod
    def _get_exchange_rate(cls, from_currency: "Currency", to_currency: "Currency") -> Decimal:
        """Synchronous fallback using class-level defaults (used in WithdrawalService)."""
        from_usd = cls._rate_lookup(cls._DEFAULT_RATES_TO_USD, from_currency.value)
        to_usd   = cls._rate_lookup(cls._DEFAULT_RATES_TO_USD, to_currency.value)

        if from_usd is None:
            raise ValueError(
                f"No exchange rate found for source currency '{from_currency.value}'. "
                "Cannot perform conversion."
            )
        if to_usd is None:
            raise ValueError(
                f"No exchange rate found for target currency '{to_currency.value}'. "
                "Cannot perform conversion."
            )
        if to_usd == Decimal("0"):
            raise ValueError(
                f"Exchange rate for '{to_currency.value}' is zero — conversion not possible."
            )
        return from_usd / to_usd

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_wallet(self, user_id: int) -> Wallet:
        result = await self.db.execute(select(Wallet).where(Wallet.user_id == user_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            wallet = Wallet(user_id=user_id)
            self.db.add(wallet)
            await self.db.flush()
            logger.info(f"Created wallet for user {user_id}")
        return wallet

    async def get_balance(self, wallet_id: str, currency: Currency) -> Decimal:
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id))
        wallet = result.scalar_one_or_none()
        if not wallet:
            return Decimal("0.00000000")
        balance_map = {
            Currency.NGN: wallet.ngn_balance,
            Currency.USD: wallet.usd_balance,
            Currency.USDT: wallet.usdt_balance,
            Currency.PI: wallet.pi_balance,
            Currency.VITCOIN: wallet.vitcoin_balance,
        }
        return balance_map.get(currency, Decimal("0.00000000"))

    async def credit(
        self,
        wallet_id: str,
        user_id: int,
        currency: Currency,
        amount: Decimal,
        tx_type: str,
        reference: Optional[str] = None,
        metadata: Optional[Dict] = None,
        fee_amount: Decimal = Decimal("0.00000000"),
        fee_currency: Optional[str] = None,
    ) -> WalletTransaction:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise ValueError(f"Wallet {wallet_id} not found")
        if wallet.is_frozen:
            raise ValueError("Wallet is frozen")
        balance_attr = f"{currency.value.lower()}_balance"
        setattr(wallet, balance_attr, getattr(wallet, balance_attr) + amount)
        tx = WalletTransaction(
            user_id=user_id, wallet_id=wallet_id,
            type=tx_type, currency=currency.value,
            amount=amount, direction="credit", status="confirmed",
            reference=reference, fee_amount=fee_amount,
            fee_currency=fee_currency,
            tx_metadata=metadata, processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(tx)
        await self.db.flush()
        logger.info(f"Credited {amount} {currency.value} to wallet {wallet_id}")
        return tx

    async def deposit_vitcoin(
        self,
        user_id: int,
        amount: Decimal,
        description: str,
        tx_type: str,
        reference: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> WalletTransaction:
        """Convenience wrapper to credit VITCoin to a user's wallet."""
        wallet = await self.get_or_create_wallet(user_id)
        payload = dict(metadata or {})
        payload.update({
            "description": description,
            "task_type": tx_type,
        })
        return await self.credit(
            wallet_id=wallet.id,
            user_id=user_id,
            currency=Currency.VITCOIN,
            amount=amount,
            tx_type=tx_type,
            reference=reference,
            metadata=payload,
        )

    async def debit(
        self,
        wallet_id: str,
        user_id: int,
        currency: Currency,
        amount: Decimal,
        tx_type: str,
        reference: Optional[str] = None,
        metadata: Optional[Dict] = None,
        fee_amount: Decimal = Decimal("0.00000000"),
        fee_currency: Optional[str] = None,
    ) -> WalletTransaction:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        result = await self.db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one_or_none()
        if not wallet:
            raise ValueError(f"Wallet {wallet_id} not found")
        if wallet.is_frozen:
            raise ValueError("Wallet is frozen")
        balance_attr = f"{currency.value.lower()}_balance"
        current = getattr(wallet, balance_attr)
        if current < amount:
            raise ValueError(f"Insufficient {currency.value} balance")
        setattr(wallet, balance_attr, current - amount)
        tx = WalletTransaction(
            user_id=user_id, wallet_id=wallet_id,
            type=tx_type, currency=currency.value,
            amount=amount, direction="debit", status="confirmed",
            reference=reference, fee_amount=fee_amount,
            fee_currency=fee_currency,
            tx_metadata=metadata, processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(tx)
        await self.db.flush()
        logger.info(f"Debited {amount} {currency.value} from wallet {wallet_id}")
        return tx

    async def convert_currency(
        self,
        wallet_id: str,
        user_id: int,
        from_currency: Currency,
        to_currency: Currency,
        amount: Decimal,
        conversion_fee_pct: Decimal,
    ) -> Tuple[WalletTransaction, WalletTransaction, Decimal]:
        if from_currency == to_currency:
            raise ValueError("Cannot convert same currency")
        debit_tx = await self.debit(
            wallet_id=wallet_id, user_id=user_id,
            currency=from_currency, amount=amount, tx_type="conversion",
        )
        rate = await self.get_exchange_rate(from_currency, to_currency)
        fee = amount * (conversion_fee_pct / Decimal("100"))
        converted_amount = (amount * rate) - (fee * rate)
        credit_tx = await self.credit(
            wallet_id=wallet_id, user_id=user_id,
            currency=to_currency, amount=converted_amount, tx_type="conversion",
            fee_amount=fee, fee_currency=from_currency.value,
            metadata={
                "from_currency": from_currency.value,
                "to_currency": to_currency.value,
                "original_amount": float(amount),
                "converted_amount": float(converted_amount),
                "rate": float(rate),
                "fee_pct": float(conversion_fee_pct),
            },
        )
        return debit_tx, credit_tx, converted_amount

    async def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        transaction_type: Optional[str] = None,
        currency: Optional[Currency] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Tuple[int, list]:
        query = select(WalletTransaction).where(WalletTransaction.user_id == user_id)
        if transaction_type:
            query = query.where(WalletTransaction.type == transaction_type)
        if currency:
            query = query.where(WalletTransaction.currency == currency.value)
        if status:
            query = query.where(WalletTransaction.status == status)
        if date_from:
            query = query.where(WalletTransaction.created_at >= date_from)
        if date_to:
            query = query.where(WalletTransaction.created_at <= date_to)
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()
        query = query.order_by(WalletTransaction.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return total, result.scalars().all()


class WithdrawalService:
    """Withdrawal request handling."""

    def __init__(self, db: AsyncSession, wallet_service: WalletService):
        self.db = db
        self.wallet_service = wallet_service

    async def create_withdrawal_request(
        self,
        user_id: int,
        wallet_id: str,
        currency: Currency,
        amount: Decimal,
        destination: str,
        destination_type: str,
        auto_approve_limit: Decimal,
        kyc_status: str = "none",
    ) -> WithdrawalRequest:
        # KYC enforcement: require verified KYC for withdrawals above $10 equivalent
        _KYC_THRESHOLD_USD = Decimal("10.00")
        # Use live rates from DB via the shared wallet service (falls back to defaults)
        _rates_to_usd = await self.wallet_service._get_rates_to_usd()
        amount_usd = amount * _rates_to_usd.get(currency.value, Decimal("1.0"))
        if amount_usd > _KYC_THRESHOLD_USD and kyc_status not in ("approved", "verified"):
            raise ValueError(
                "KYC verification required for withdrawals above $10. "
                "Please complete identity verification in your profile settings."
            )

        balance = await self.wallet_service.get_balance(wallet_id, currency)
        if balance < amount:
            raise ValueError(f"Insufficient {currency.value} balance")
        fee_amount = Decimal("0.00")
        net_amount = amount - fee_amount
        auto_approved = amount <= auto_approve_limit
        status = "auto_approved" if auto_approved else "pending"
        request = WithdrawalRequest(
            user_id=user_id, wallet_id=wallet_id,
            currency=currency.value, amount=amount,
            fee_amount=fee_amount, net_amount=net_amount,
            destination=destination, destination_type=destination_type,
            status=status, auto_approved=auto_approved,
        )
        self.db.add(request)
        await self.db.flush()

        # Always reserve/debit the funds immediately so balance is locked while pending
        await self.wallet_service.debit(
            wallet_id=wallet_id, user_id=user_id,
            currency=currency, amount=amount,
            tx_type="withdrawal" if auto_approved else "withdrawal_reserve",
            metadata={
                "withdrawal_request_id": str(request.id),
                "status": status,
            },
            fee_amount=fee_amount, fee_currency=currency.value,
        )

        if auto_approved:
            request.processed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            request.status = "processed"

        logger.info(f"Created withdrawal request {request.id} for user {user_id} (status={status})")
        return request


class SubscriptionService:
    """Subscription management."""

    def __init__(self, db: AsyncSession, wallet_service: WalletService):
        self.db = db
        self.wallet_service = wallet_service

    async def subscribe(
        self,
        user_id: int,
        wallet_id: str,
        plan_id: str,
        currency: Currency,
        price: Decimal,
    ) -> dict:
        transaction = await self.wallet_service.debit(
            wallet_id=wallet_id, user_id=user_id,
            currency=currency, amount=price, tx_type="subscription",
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # Fetch plan duration from DB, fall back to 30 days
        from app.modules.wallet.models import WalletSubscriptionPlan as _Plan
        from sqlalchemy import select as _select
        _plan_row = await self.db.execute(_select(_Plan).where(_Plan.id == plan_id))
        _plan = _plan_row.scalar_one_or_none()
        duration_days = int(_plan.duration_days) if _plan and getattr(_plan, "duration_days", None) else 30
        subscription = WalletUserSubscription(
            user_id=user_id, plan_id=plan_id,
            currency_paid=currency.value, amount_paid=price,
            started_at=now, expires_at=now + timedelta(days=duration_days),
            auto_renew=True, status="active",
            renewal_tx_id=transaction.id,
        )
        self.db.add(subscription)
        await self.db.flush()
        logger.info(f"User {user_id} subscribed to plan {plan_id}")
        return {
            "subscription_id": str(subscription.id),
            "transaction_id": str(transaction.id),
            "expires_at": subscription.expires_at,
        }
