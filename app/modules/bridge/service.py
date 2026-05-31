# app/modules/bridge/service.py
"""Cross-Chain Bridge service — lock/mint, burn/release, audit log."""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bridge.models import BridgeAuditLog, BridgePool, BridgeTransaction

logger = logging.getLogger(__name__)

BRIDGE_FEE_PCT = Decimal("0.0100")   # 1 % default fee


# ── Pool helpers ──────────────────────────────────────────────────────────────

async def list_pools(db: AsyncSession, active_only: bool = True) -> list[BridgePool]:
    q = select(BridgePool)
    if active_only:
        q = q.where(BridgePool.is_active == True)
    result = await db.execute(q.order_by(BridgePool.id))
    return list(result.scalars().all())


async def get_pool(db: AsyncSession, pool_id: int) -> Optional[BridgePool]:
    result = await db.execute(select(BridgePool).where(BridgePool.id == pool_id))
    return result.scalar_one_or_none()


async def seed_default_pools(db: AsyncSession) -> None:
    """Ensure at least the default VIT ↔ USDT and VIT ↔ ETH pools exist."""
    existing = (await db.execute(select(func.count(BridgePool.id)))).scalar() or 0
    if existing > 0:
        return

    defaults = [
        BridgePool(
            asset_from="VIT",   asset_to="USDT",
            chain_from="VIT_NETWORK", chain_to="ETHEREUM",
            exchange_rate=Decimal("0.08500000"),
            fee_pct=Decimal("0.0100"),
            min_amount=Decimal("100.00000000"),
            max_amount=Decimal("50000.00000000"),
            pool_liquidity=Decimal("500000.00000000"),
            is_active=True,
        ),
        BridgePool(
            asset_from="VIT",   asset_to="ETH",
            chain_from="VIT_NETWORK", chain_to="ETHEREUM",
            exchange_rate=Decimal("0.00003500"),
            fee_pct=Decimal("0.0100"),
            min_amount=Decimal("500.00000000"),
            max_amount=Decimal("100000.00000000"),
            pool_liquidity=Decimal("250000.00000000"),
            is_active=True,
        ),
        BridgePool(
            asset_from="USDT",  asset_to="VIT",
            chain_from="ETHEREUM", chain_to="VIT_NETWORK",
            exchange_rate=Decimal("11.76470588"),
            fee_pct=Decimal("0.0100"),
            min_amount=Decimal("10.00000000"),
            max_amount=Decimal("5000.00000000"),
            pool_liquidity=Decimal("50000.00000000"),
            is_active=True,
        ),
    ]
    for p in defaults:
        db.add(p)
    await db.commit()
    logger.info("Bridge: seeded 3 default pools")


# ── Transaction helpers ────────────────────────────────────────────────────────

def _generate_tx_hash(user_id: int, pool_id: int, amount: Decimal) -> str:
    raw = f"vit-bridge:{user_id}:{pool_id}:{amount}:{uuid.uuid4().hex}"
    return "0x" + hashlib.sha256(raw.encode()).hexdigest()


async def initiate_bridge(
    db: AsyncSession,
    user_id: int,
    pool_id: int,
    amount_in: Decimal,
    destination_address: str,
    source_address: Optional[str] = None,
) -> BridgeTransaction:
    pool = await get_pool(db, pool_id)
    if not pool:
        raise ValueError("Bridge pool not found")
    if not pool.is_active:
        raise ValueError("This bridge pool is currently paused")
    if amount_in < pool.min_amount:
        raise ValueError(f"Minimum bridge amount is {pool.min_amount} {pool.asset_from}")
    if amount_in > pool.max_amount:
        raise ValueError(f"Maximum bridge amount is {pool.max_amount} {pool.asset_from}")

    fee       = (amount_in * pool.fee_pct).quantize(Decimal("0.00000001"))
    net_in    = amount_in - fee
    amount_out = (net_in * pool.exchange_rate).quantize(Decimal("0.00000001"))

    if pool.pool_liquidity < amount_out:
        raise ValueError("Insufficient pool liquidity. Try a smaller amount.")

    # Debit user's VIT wallet for outbound bridges
    if pool.chain_from == "VIT_NETWORK":
        from app.modules.wallet.services import WalletService
        from app.modules.wallet.models import Currency
        ws = WalletService(db)
        wallet = await ws.get_or_create_wallet(user_id)
        if wallet.vitcoin_balance < amount_in:
            raise ValueError(f"Insufficient VITCoin balance. Need {amount_in} VITCoin.")
        await ws.debit(
            wallet_id=wallet.id,
            user_id=user_id,
            currency=Currency.VITCOIN,
            amount=amount_in,
            tx_type="bridge_lock",
            reference=f"bridge_lock_{uuid.uuid4().hex[:8]}",
            metadata={"pool_id": pool_id, "destination": destination_address},
        )

    tx_hash = _generate_tx_hash(user_id, pool_id, amount_in)

    tx = BridgeTransaction(
        pool_id=pool_id,
        user_id=user_id,
        tx_hash=tx_hash,
        direction="outbound" if pool.chain_from == "VIT_NETWORK" else "inbound",
        amount_in=amount_in,
        amount_out=amount_out,
        fee=fee,
        exchange_rate=pool.exchange_rate,
        destination_address=destination_address,
        source_address=source_address,
        status="locked",
    )
    db.add(tx)

    # Reduce pool liquidity
    pool.pool_liquidity -= amount_out

    await db.flush()

    # Audit log
    audit = BridgeAuditLog(
        transaction_id=tx.id,
        event="initiated",
        actor="user",
        detail=f"Bridge {amount_in} {pool.asset_from} → {amount_out} {pool.asset_to} | fee={fee}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(tx)

    logger.info(f"Bridge initiated: tx={tx.tx_hash} user={user_id} amount_in={amount_in}")
    return tx


async def confirm_bridge(
    db: AsyncSession,
    tx_hash: str,
    relayer_tx_hash: str,
    actor: str = "relayer",
) -> BridgeTransaction:
    """Relayer confirms the cross-chain transfer completed."""
    result = await db.execute(
        select(BridgeTransaction).where(BridgeTransaction.tx_hash == tx_hash)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise ValueError("Transaction not found")
    if tx.status not in ("locked", "pending"):
        raise ValueError(f"Cannot confirm transaction in state '{tx.status}'")

    tx.status = "completed"
    tx.relayer_tx_hash = relayer_tx_hash
    tx.confirmed_at = datetime.now(timezone.utc)
    tx.completed_at = datetime.now(timezone.utc)

    # Credit VITCoin for inbound bridges
    pool = await get_pool(db, tx.pool_id)
    if pool and pool.chain_to == "VIT_NETWORK":
        from app.modules.wallet.services import WalletService
        from app.modules.wallet.models import Currency
        ws = WalletService(db)
        wallet = await ws.get_or_create_wallet(tx.user_id)
        await ws.credit(
            wallet_id=wallet.id,
            user_id=tx.user_id,
            currency=Currency.VITCOIN,
            amount=tx.amount_out,
            tx_type="bridge_mint",
            reference=f"bridge_mint_{uuid.uuid4().hex[:8]}",
            metadata={"bridge_tx_hash": tx_hash},
        )

    audit = BridgeAuditLog(
        transaction_id=tx.id,
        event="completed",
        actor=actor,
        detail=f"Relayer confirmed: relayer_tx={relayer_tx_hash}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(tx)
    return tx


async def my_transactions(
    db: AsyncSession,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[BridgeTransaction]:
    result = await db.execute(
        select(BridgeTransaction)
        .where(BridgeTransaction.user_id == user_id)
        .order_by(BridgeTransaction.created_at.desc())
        .limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def get_transaction(db: AsyncSession, tx_id: int) -> Optional[BridgeTransaction]:
    result = await db.execute(
        select(BridgeTransaction).where(BridgeTransaction.id == tx_id)
    )
    return result.scalar_one_or_none()


async def bridge_stats(db: AsyncSession) -> dict:
    total_txs   = (await db.execute(select(func.count(BridgeTransaction.id)))).scalar() or 0
    completed   = (await db.execute(
        select(func.count(BridgeTransaction.id)).where(BridgeTransaction.status == "completed")
    )).scalar() or 0
    total_vol   = (await db.execute(select(func.sum(BridgeTransaction.amount_in)))).scalar() or 0
    total_fees  = (await db.execute(select(func.sum(BridgeTransaction.fee)))).scalar() or 0
    pools_count = (await db.execute(select(func.count(BridgePool.id)).where(BridgePool.is_active == True))).scalar() or 0

    return {
        "total_transactions": total_txs,
        "completed_transactions": completed,
        "total_volume_vitcoin": float(total_vol),
        "total_fees_collected": float(total_fees),
        "active_pools": pools_count,
    }
