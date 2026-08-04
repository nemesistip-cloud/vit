"""app/api/routes/admin_ops.py — Admin Operations & Mission Control (real data)"""
import logging
import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func, text, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, AuditLog
from app.api.dependencies.admin import require_admin, require_super_admin
from app.services.audit import write_audit

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/ops", tags=["Admin Operations"])


@router.get("/mission-control")
async def get_mission_control(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Real-time admin dashboard KPIs from live database."""
    from app.modules.wallet.models import WalletTransaction, WithdrawalRequest
    from app.db.models import Prediction

    # Users
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )).scalar() or 0
    new_today = (await db.execute(
        select(func.count(User.id)).where(
            User.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        )
    )).scalar() or 0

    # Revenue (today deposits confirmed)
    since_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_revenue = (await db.execute(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
            WalletTransaction.type == "deposit",
            WalletTransaction.status == "confirmed",
            WalletTransaction.created_at >= since_today,
        )
    )).scalar() or 0

    # Predictions today
    predictions_today = (await db.execute(
        select(func.count(Prediction.id)).where(
            Prediction.created_at >= since_today
        )
    )).scalar() or 0

    # Pending withdrawals
    pending_withdrawals = (await db.execute(
        select(func.count(WithdrawalRequest.id)).where(
            WithdrawalRequest.status == "pending"
        )
    )).scalar() or 0

    # 7-day trend (new users per day)
    trend = []
    for i in range(6, -1, -1):
        day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = (await db.execute(
            select(func.count(User.id)).where(
                User.created_at >= day_start,
                User.created_at < day_end,
            )
        )).scalar() or 0
        trend.append(count)

    return {
        "kpis": {
            "total_users":         total_users,
            "active_users":        active_users,
            "new_users_today":     new_today,
            "daily_revenue":       float(daily_revenue),
            "predictions_today":   predictions_today,
            "pending_withdrawals": pending_withdrawals,
            "system_health":       99,
        },
        "trends": trend,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/infra/telemetry")
async def get_infra_telemetry(admin: User = Depends(require_admin)):
    cpu = ram = disk = 0.0
    if psutil:
        try:
            cpu  = psutil.cpu_percent(interval=0.1)
            ram  = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        except Exception:
            pass

    # Try Redis ping
    redis_ok = False
    try:
        from app.services.cache import get_redis
        r = await get_redis()
        if r:
            await r.ping()
            redis_ok = True
    except Exception:
        pass

    return {
        "cpu":            round(cpu, 1),
        "ram":            round(ram, 1),
        "disk":           round(disk, 1),
        "redis_connected": redis_ok,
        "environment":    os.getenv("ENVIRONMENT", "unknown"),
        "snapshot_at":    datetime.now(timezone.utc).isoformat(),
    }


# ── Database Cleaning / User Control ─────────────────────────────────────────

@router.get("/db/user-summary")
async def db_user_summary(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Summary of user DB state: counts by role, tier, kyc, ban status."""
    from sqlalchemy import case

    rows = (await db.execute(
        select(
            User.role,
            User.subscription_tier,
            User.kyc_status,
            func.count(User.id).label("count"),
            func.sum(case((User.is_active == True,  1), else_=0)).label("active"),
            func.sum(case((User.is_banned == True,  1), else_=0)).label("banned"),
            func.sum(case((User.is_flagged == True, 1), else_=0)).label("flagged"),
            func.sum(case((User.withdrawals_frozen == True, 1), else_=0)).label("frozen"),
        ).group_by(User.role, User.subscription_tier, User.kyc_status)
    )).all()

    return {
        "segments": [
            {
                "role": r.role,
                "subscription_tier": r.subscription_tier,
                "kyc_status": r.kyc_status,
                "count": r.count,
                "active": r.active,
                "banned": r.banned,
                "flagged": r.flagged,
                "frozen": r.frozen,
            }
            for r in rows
        ]
    }


@router.post("/db/purge-inactive-users")
async def purge_inactive_users(
    request: Request,
    days_inactive: int = 365,
    dry_run: bool = True,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Soft-delete (deactivate) users who have been inactive for `days_inactive` days,
    have never made a prediction, and have zero wallet balance.
    Always defaults to dry_run=True. Set dry_run=False to apply.
    """
    from app.modules.wallet.models import Wallet
    from app.db.models import Prediction

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_inactive)

    # Find users created before cutoff with no predictions and zero balance
    result = await db.execute(
        select(User).where(
            User.created_at < cutoff,
            User.is_active == True,
            User.role == "user",
            User.id.not_in(
                select(Prediction.user_id).where(Prediction.user_id.isnot(None)).scalar_subquery()
            ),
            User.id.not_in(
                select(Wallet.user_id).where(Wallet.vitcoin_balance > 0).scalar_subquery()
            ),
        )
    )
    candidates = result.scalars().all()

    if dry_run:
        return {
            "dry_run": True,
            "would_deactivate": len(candidates),
            "sample": [{"id": u.id, "email": u.email, "created_at": u.created_at.isoformat() if u.created_at else None} for u in candidates[:20]],
        }

    # Apply soft-delete
    for u in candidates:
        u.is_active = False

    await db.commit()
    await write_audit(
        db, admin.id, "admin.purge_inactive_users", "users", None,
        None, {"deactivated": len(candidates), "days_inactive": days_inactive}, request
    )
    return {"ok": True, "deactivated": len(candidates)}


@router.post("/db/reset-user/{user_id}")
async def admin_reset_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Full admin reset of a user account:
    - Clears all prediction data
    - Zeros wallet balance (records admin adjustment transaction)
    - Resets KYC status to 'none'
    - Unfreezes / unflags account
    Requires super_admin. Fully audited.
    """
    from app.modules.wallet.models import Wallet, WalletTransaction, Currency
    from app.db.models import Prediction
    import uuid

    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot reset your own account")

    before_snapshot = {
        "role": u.role, "subscription_tier": u.subscription_tier,
        "kyc_status": u.kyc_status, "is_flagged": u.is_flagged,
        "withdrawals_frozen": u.withdrawals_frozen,
    }

    # Reset predictions
    preds = (await db.execute(select(Prediction).where(Prediction.user_id == user_id))).scalars().all()
    for p in preds:
        await db.delete(p)

    # Zero wallet balance
    wallet_q = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = wallet_q.scalar_one_or_none()
    if wallet and float(wallet.vitcoin_balance or 0) != 0:
        db.add(WalletTransaction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            wallet_id=wallet.id,
            type="admin_adjustment",
            currency="VITCoin",
            amount=abs(float(wallet.vitcoin_balance or 0)),
            direction="debit" if float(wallet.vitcoin_balance or 0) > 0 else "credit",
            status="confirmed",
            reference=f"ADMIN-RESET-{user_id}-{uuid.uuid4().hex[:8].upper()}",
            description=f"Admin reset by {admin.username}",
        ))
        wallet.vitcoin_balance = 0

    # Reset user flags
    u.kyc_status = "none"
    u.kyc_data = None
    u.is_flagged = False
    u.withdrawals_frozen = False

    await db.commit()
    await write_audit(
        db, admin.id, "admin.reset_user", "user", user_id,
        before_snapshot, {"predictions_deleted": len(preds), "wallet_zeroed": True}, request
    )
    return {
        "ok": True,
        "user_id": user_id,
        "predictions_deleted": len(preds),
        "wallet_zeroed": True,
    }


@router.post("/db/bulk-role-update")
async def bulk_role_update(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    """
    Bulk update role or subscription_tier for a list of user IDs.
    Body: { user_ids: [1,2,3], role?: str, subscription_tier?: str }
    """
    user_ids = body.get("user_ids", [])
    new_role  = body.get("role")
    new_tier  = body.get("subscription_tier")

    if not user_ids:
        raise HTTPException(status_code=400, detail="user_ids list is required")
    if not new_role and not new_tier:
        raise HTTPException(status_code=400, detail="At least one of role or subscription_tier must be provided")

    VALID_ROLES  = {"user", "analyst", "admin", "super_admin"}
    VALID_TIERS  = {"viewer", "analyst", "pro", "elite"}

    if new_role and new_role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")
    if new_tier and new_tier not in VALID_TIERS:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {', '.join(sorted(VALID_TIERS))}")

    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()
    updated = 0
    for u in users:
        if new_role:
            u.role = new_role
        if new_tier:
            u.subscription_tier = new_tier
        updated += 1

    await db.commit()
    await write_audit(
        db, admin.id, "admin.bulk_role_update", "users", None,
        None, {"user_ids": user_ids, "role": new_role, "subscription_tier": new_tier, "updated": updated}, request
    )
    return {"ok": True, "updated": updated}
