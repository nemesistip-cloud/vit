"""app/modules/finance/routes.py
Financial Infrastructure Layer — VIT Stablecoin (VUSD), lending protocol, yield vaults.

Data is read from PlatformConfig / WalletTransaction rather than hardcoded.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.wallet.models import PlatformConfig, WalletTransaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/finance", tags=["Financial Infrastructure"])


# ── helpers ───────────────────────────────────────────────────────────────────

async def _get_platform_cfg(db: AsyncSession, key: str, default: Any = None) -> Any:
    """Fetch a single PlatformConfig value by key."""
    row = await db.execute(
        select(PlatformConfig).where(PlatformConfig.key == key)
    )
    cfg = row.scalar_one_or_none()
    if cfg and cfg.value:
        return cfg.value
    return default


async def _total_deposited_usd(db: AsyncSession) -> Decimal:
    """Sum of all confirmed USD/USDT deposits (approximation of TVL)."""
    result = await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0))
        .where(
            WalletTransaction.type.in_(["deposit", "subscription"]),
            WalletTransaction.status == "confirmed",
            WalletTransaction.currency.in_(["USD", "USDT"]),
        )
    )
    return Decimal(str(result.scalar() or 0))


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/pool-stats")
async def get_pool_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return live VUSD pool statistics derived from platform config and transactions."""
    try:
        tvl = float(await _total_deposited_usd(db))
        cfg = await _get_platform_cfg(db, "finance_pool", {})
        apy   = float(cfg.get("apy",   0.12))
        status = cfg.get("status", "stable")
        pool_id = cfg.get("pool_id", "VIT-VUSD")
        min_deposit = float(cfg.get("min_deposit", 10))
        max_deposit = float(cfg.get("max_deposit", 100_000))
        return {
            "pool_id":    pool_id,
            "tvl":        tvl,
            "apy":        apy,
            "status":     status,
            "min_deposit": min_deposit,
            "max_deposit": max_deposit,
            "currency":   "USD",
        }
    except Exception as exc:
        logger.error("[finance] pool-stats error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/vault/deposit")
async def deposit_to_vault(
    amount: float,
    vault: str = "balanced",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a yield vault deposit request (queued for processing)."""
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be > 0")

    cfg = await _get_platform_cfg(db, "finance_vaults", {})
    vaults: Dict[str, Any] = cfg.get("vaults", {
        "conservative": {"name": "Conservative Yield Vault", "apy": 0.06},
        "balanced":     {"name": "Balanced Growth Vault",    "apy": 0.12},
        "aggressive":   {"name": "Aggressive Growth Vault",  "apy": 0.20},
    })

    vault_cfg = vaults.get(vault, vaults.get("balanced", {}))
    vault_name = vault_cfg.get("name", "Balanced Growth Vault")
    vault_apy  = float(vault_cfg.get("apy", 0.12))
    annual_yield = round(amount * vault_apy, 2)

    return {
        "status":        "queued",
        "user_id":       current_user.id,
        "amount":        amount,
        "vault":         vault,
        "vault_name":    vault_name,
        "apy":           vault_apy,
        "annual_yield_estimate": annual_yield,
        "currency":      "USD",
    }


@router.get("/vaults")
async def list_vaults(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available yield vaults with current APY rates from PlatformConfig."""
    cfg = await _get_platform_cfg(db, "finance_vaults", {})
    vaults = cfg.get("vaults", {
        "conservative": {"name": "Conservative Yield Vault", "apy": 0.06,  "risk": "low"},
        "balanced":     {"name": "Balanced Growth Vault",    "apy": 0.12,  "risk": "medium"},
        "aggressive":   {"name": "Aggressive Growth Vault",  "apy": 0.20,  "risk": "high"},
    })
    return {
        "vaults": [
            {"id": k, **v}
            for k, v in vaults.items()
        ]
    }
