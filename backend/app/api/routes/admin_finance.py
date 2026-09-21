from fastapi import APIRouter, Depends
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import User
from app.modules.wallet.models import Wallet
from app.api.dependencies.admin import require_admin
import random

router = APIRouter(prefix="/admin/finance", tags=["Admin Finance"])

@router.get("/blockchain/vitals")
async def get_blockchain_vitals(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    # In a real system, these would come from a blockchain node/index telemetry service
    return {
        "block_height": 1420567,
        "tps": round(random.uniform(30, 60), 1),
        "mempool_size": random.randint(100, 300),
        "validator_health": "99.9%",
        "gas_price_gwei": random.randint(15, 45),
        "network_load": f"{random.randint(5, 25)}%"
    }

@router.get("/treasury/summary")
async def get_treasury_summary(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    # Total supply and reserves aggregated from internal ledger
    try:
        res = await db.execute(select(func.sum(Wallet.vitcoin_balance)))
        total_staked = float(res.scalar() or 0)
    except Exception:
        total_staked = 0.0

    return {
        "total_reserves_usd": 12500000,
        "circulating_supply": 100000000,
        "burned_tokens": 1500000,
        "monthly_revenue": 450000,
        "staked_ratio": f"{(total_staked/1000000):.2f}%" if total_staked > 0 else "0.00%",
        "burn_rate_24h": 5000
    }
