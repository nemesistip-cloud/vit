from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.db.models import User
from app.modules.blockchain.models import MatchSettlement
from app.modules.wallet.models import Wallet, WalletTransaction
from app.api.dependencies.admin import require_admin
from app.services.vit_chain_client import VitChainClient, VitChainClientError
from app.core.errors import AppError

router = APIRouter(prefix="/admin/finance", tags=["Admin Finance"])

@router.get("/blockchain/vitals")
async def get_blockchain_vitals(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    chain = VitChainClient()
    try:
        status, metrics = await chain.status(), await chain.metrics()
    except VitChainClientError as exc:
        raise AppError("VIT Chain telemetry is unavailable", status_code=503, code="chain_unavailable") from exc

    return {
        "source": "vit-chain",
        "status": "available",
        "block_height": status["block_height"],
        "tps": metrics["tps"],
        "total_transactions": metrics["total_transactions"],
        "active_validators": metrics["active_validators"],
        "connected_peers": status.get("connected_peers"),
        "mempool_size": None,
        "gas_price_gwei": None,
        "network_load": None,
    }

@router.get("/treasury/summary")
async def get_treasury_summary(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    chain = VitChainClient()
    try:
        supply = await chain.supply()
    except VitChainClientError as exc:
        raise AppError("VIT Chain supply data is unavailable", status_code=503, code="chain_unavailable") from exc

    stablecoin_reserves = await db.execute(
        select(
            func.coalesce(func.sum(Wallet.usd_balance), 0),
            func.coalesce(func.sum(Wallet.usdt_balance), 0),
        )
    )
    usd_reserves, usdt_reserves = (float(value or 0) for value in stablecoin_reserves.one())

    since_30_days = datetime.now(timezone.utc) - timedelta(days=30)
    revenue_rows = (await db.execute(
        select(WalletTransaction.currency, func.sum(WalletTransaction.amount))
        .where(
            WalletTransaction.type.in_(["fee", "platform_fee", "subscription"]),
            WalletTransaction.status == "confirmed",
            WalletTransaction.created_at >= since_30_days,
        )
        .group_by(WalletTransaction.currency)
    )).all()
    revenue_by_currency = {str(currency): float(amount or 0) for currency, amount in revenue_rows}

    since_24_hours = datetime.now(timezone.utc) - timedelta(hours=24)
    burn_24h = await db.execute(
        select(func.coalesce(func.sum(MatchSettlement.burn_amount), 0)).where(
            MatchSettlement.settled_at >= since_24_hours
        )
    )
    total_supply = float(supply.get("total_supply") or 0)
    staked_supply = float(supply.get("staked_supply") or 0)
    revenue_usd_equivalent = revenue_by_currency.get("USD", 0) + revenue_by_currency.get("USDT", 0)

    return {
        "source": "vit-chain-and-wallet-ledger",
        "total_reserves_usd": usd_reserves + usdt_reserves,
        "reserve_breakdown": {"USD": usd_reserves, "USDT": usdt_reserves},
        "circulating_supply": float(supply["circulating_supply"]) if supply.get("circulating_supply") is not None else None,
        "burned_tokens": float(supply["burned_supply"]) if supply.get("burned_supply") is not None else None,
        "monthly_revenue": revenue_usd_equivalent,
        "monthly_revenue_by_currency": revenue_by_currency,
        "staked_ratio": f"{(staked_supply / total_supply * 100):.2f}%" if total_supply > 0 else None,
        "burn_rate_24h": float(burn_24h.scalar_one() or 0),
    }
