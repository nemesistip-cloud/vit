# app/modules/wallet/direct_sale.py
"""Direct VITCoin purchase logic — using 3-Governor pricing engine."""

import hashlib
import logging
import uuid as _uuid_mod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.api.deps import get_current_user
from app.core.errors import AppError
from app.modules.wallet.models import (
    Wallet, WalletTransaction, Currency, PlatformConfig
)
from app.modules.wallet.services import WalletService
from app.modules.wallet.pricing_engine import VITCoinPricingEngine
from app.core.cache import cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wallet/vitcoin", tags=["Direct Sale"])

class VITCoinBuyRequest(BaseModel):
    amount_usd: float = Field(..., gt=0)

@router.post("/buy")
async def buy_vitcoin_direct(
    request: VITCoinBuyRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Buy VITCoin directly from the platform using USD balance.
    Uses Session 6.1 Pricing Engine and time-bucketed idempotency.
    """
    user_id = current_user.id
    amount_usd = Decimal(str(request.amount_usd))

    # 1. Specialized Idempotency Key
    minute_bucket = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    raw_key = f"{user_id}:{amount_usd}:{minute_bucket}"
    idempotency_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    cache_key = f"direct_sale:idempotency:{idempotency_hash}"
    cached_result = await cache.get(cache_key)
    if cached_result:
        return cached_result

    # 2. Get Current 3-Governor Price
    price_state = await VITCoinPricingEngine.get_current_price(db)
    price_usd = Decimal(str(price_state["price_usd"]))

    if price_usd <= 0:
        raise AppError("Invalid VITCoin price detected", status_code=500, code="pricing_error")

    # 3. Calculate Fee
    fee_q = select(PlatformConfig).where(PlatformConfig.key == "conversion_fee_pct")
    fee_cfg = (await db.execute(fee_q)).scalar_one_or_none()
    fee_pct = Decimal(str(fee_cfg.value.get("value", "1.5"))) if fee_cfg else Decimal("1.5")

    fee_usd = amount_usd * (fee_pct / Decimal("100"))
    net_usd = amount_usd - fee_usd
    vitcoin_to_receive = net_usd / price_usd

    # 4. Atomic Mutation
    async with db.begin():
        service = WalletService(db)
        wallet = await service.get_or_create_wallet(user_id)

        if wallet.usd_balance < amount_usd:
            raise AppError("Insufficient USD balance", status_code=402, code="insufficient_balance")

        wallet.usd_balance -= amount_usd
        wallet.vitcoin_balance += vitcoin_to_receive

        ref_base = f"DS-{user_id}-{_uuid_mod.uuid4().hex[:8].upper()}"

        # Debit Transaction
        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=user_id,
            wallet_id=wallet.id,
            type="buy",
            currency="USD",
            amount=amount_usd,
            direction="debit",
            status="confirmed",
            reference=f"{ref_base}-DEBIT",
            description=f"Direct purchase of VITCoin",
            fee_amount=fee_usd,
            fee_currency="USD",
            tx_metadata={"rate": str(price_usd), "idempotency_hash": idempotency_hash}
        ))

        # Credit Transaction
        db.add(WalletTransaction(
            id=str(_uuid_mod.uuid4()),
            user_id=user_id,
            wallet_id=wallet.id,
            type="buy",
            currency="VITCoin",
            amount=vitcoin_to_receive,
            direction="credit",
            status="confirmed",
            reference=f"{ref_base}-CREDIT",
            description=f"VITCoin received from direct purchase",
            tx_metadata={"rate": str(price_usd)}
        ))

    result = {
        "status": "success",
        "usd_spent": float(amount_usd),
        "vitcoin_received": float(vitcoin_to_receive),
        "rate": float(price_usd),
        "fee_usd": float(fee_usd),
        "reference": ref_base
    }

    await cache.set(cache_key, result, ttl=60)
    return result
