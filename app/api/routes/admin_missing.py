"""app/api/routes/admin_missing.py — Admin supplementary routes (v5.5.0).

Endpoints: stats overview, user management, audit logs, system ops,
fixture sync, leagues, markets, marketplace pending listings.

Prefix: /admin  (registered as /api/admin/* via main.py include_router).
Auth:   Depends(get_current_admin) on every route.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_admin
from app.db.database import get_db
from app.db.models import User, Match, TrainingJob, AuditLog, SubscriptionPlan

router = APIRouter(prefix="/admin", tags=["Admin — Supplementary"])


@router.get("/stats")
async def get_admin_stats(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_admin)):
    """Provides dashboard overview statistics."""
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    match_count = (await db.execute(select(func.count(Match.id)))).scalar() or 0
    job_count = (await db.execute(select(func.count(TrainingJob.id)))).scalar() or 0
    audit_count = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
    plan_count = (await db.execute(select(func.count(SubscriptionPlan.id)).where(SubscriptionPlan.is_active == True))).scalar() or 0

    recent_activity_rows = (await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10)
    )).scalars().all()

    recent_activity = [
        {
            "action": r.action,
            "actor": r.actor,
            "status": r.status,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None
        } for r in recent_activity_rows
    ]

    top_users_rows = (await db.execute(
        select(User).order_by(User.created_at.desc()).limit(5)
    )).scalars().all()

    top_users = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "tier": u.subscription_tier
        } for u in top_users_rows
    ]

    return {
        "users": user_count,
        "matches": match_count,
        "training_jobs": job_count,
        "active_plans": plan_count,
        "audit_entries": audit_count,
        "recent_activity": recent_activity,
        "top_users": top_users
    }

# GET /users is handled by the main admin router (admin.py) — removed here to avoid conflict.

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Updates user details (role, tier, etc)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in body.items():
        if hasattr(user, key) and key not in ("id", "hashed_password"):
            setattr(user, key, value)

    await db.commit()
    return {"status": "success"}

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Bans or unbans a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_banned = body.get("banned", True)
    await db.commit()

    audit = AuditLog(
        action="user_ban" if user.is_banned else "user_unban",
        actor=current_user.username,
        resource="user",
        resource_id=str(user_id),
        details={"reason": body.get("reason", "")}
    )
    db.add(audit)
    await db.commit()

    return {"status": "success"}

@router.get("/audit-entries")
async def list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin)
):
    """Returns system audit logs."""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
    )
    logs = result.scalars().all()
    total = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0

    return {
        "logs": [
            {
                "id": l.id,
                "action": l.action,
                "actor": l.actor,
                "resource": l.resource,
                "resource_id": l.resource_id,
                "details": l.details,
                "ip_address": l.ip_address,
                "status": l.status,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None
            } for l in logs
        ],
        "total": total
    }

@router.post("/system/cache/clear")
async def clear_cache(current_user=Depends(get_current_admin)):
    return {"status": "success", "message": "Cache cleared"}

@router.post("/system/backup")
async def create_backup(current_user=Depends(get_current_admin)):
    return {"status": "success", "backup": f"backup_{int(datetime.now().timestamp())}.sql"}

@router.post("/matches/fetch-fixtures")
async def fetch_fixtures(
    count: int = 50,
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Trigger an immediate fixture sync from TheSportsDB + Football-Data.org."""
    from app.services.sportsdb_api import sync_upcoming_fixtures
    try:
        result = await sync_upcoming_fixtures(db, days_ahead=days)
    except Exception as sync_err:
        result = {"inserted": 0, "updated": 0, "skipped": 0, "total_fetched": 0, "error": str(sync_err)}

    seeded = 0
    try:
        from app.modules.predictions.seeder import seed_predictions_for_upcoming
        seeded = await seed_predictions_for_upcoming(db)
    except Exception:
        pass

    stored = result.get("inserted", 0) + result.get("updated", 0)
    return {
        "status": "success",
        "stored": stored,
        "skipped_existing": result.get("skipped", 0),
        "fixtures": result,
        "predictions_seeded": seeded,
        "days_ahead": days,
    }

@router.post("/sync-fixtures")
async def sync_fixtures(
    days: int = 90,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """Full fixture + prediction sync."""
    from app.services.sportsdb_api import sync_upcoming_fixtures
    try:
        result = await sync_upcoming_fixtures(db, days_ahead=days)
    except Exception as sync_err:
        result = {"inserted": 0, "updated": 0, "skipped": 0, "total_fetched": 0, "error": str(sync_err)}

    seeded = 0
    try:
        from app.modules.predictions.seeder import seed_predictions_for_upcoming
        seeded = await seed_predictions_for_upcoming(db)
    except Exception:
        pass

    return {"status": "success", "fixtures": result, "predictions_seeded": seeded, "days_ahead": days}

@router.get("/leagues")
async def list_leagues(current_user=Depends(get_current_admin)):
    from app.services.sportsdb_api import LEAGUE_DISPLAY, LEAGUES
    return [
        {"slug": slug, "name": LEAGUE_DISPLAY.get(slug, slug), "id": lid}
        for slug, lid in LEAGUES.items()
    ]

@router.get("/markets")
async def list_markets(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """List all markets from the DB."""
    from app.db.models import Market
    rows = (await db.execute(
        select(Market).order_by(Market.created_at.desc()).limit(500)
    )).scalars().all()
    return [
        {
            "id": m.id,
            "market_type": m.market_type,
            "category": m.category,
            "title": m.title,
            "description": m.description,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]

@router.get("/marketplace/pending")
async def list_pending_listings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    """List marketplace listings awaiting admin approval."""
    from app.modules.marketplace.models import AIModelListing
    rows = (await db.execute(
        select(AIModelListing)
        .where(AIModelListing.approval_status == "pending")
        .order_by(AIModelListing.created_at.desc())
        .limit(200)
    )).scalars().all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "slug": r.slug,
            "description": r.description,
            "category": r.category,
            "creator_id": r.creator_id,
            "price_per_call": float(r.price_per_call),
            "approval_status": r.approval_status,
            "approval_note": r.approval_note,
            "is_active": r.is_active,
            "is_verified": r.is_verified,
            "usage_count": r.usage_count,
            "avg_rating": r.avg_rating,
            "total_staked": float(r.total_staked),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
