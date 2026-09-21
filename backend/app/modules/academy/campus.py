"""Campus Hub — aggregated overview endpoint — v5.6"""
from __future__ import annotations

import logging
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from app.modules.academy.models import (
    Course, AcademicResource, CampusCircle, CampusGig,
)

router = APIRouter(prefix="/api/campus", tags=["Campus Hub"])
logger = logging.getLogger(__name__)


@router.get("/overview")
async def campus_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregated campus statistics for the hub dashboard."""
    uni = getattr(current_user, "university", None)

    total_courses = (await db.execute(func.count(Course.id))).scalar() or 0
    total_resources = (await db.execute(func.count(AcademicResource.id))).scalar() or 0
    total_circles = (await db.execute(func.count(CampusCircle.id))).scalar() or 0
    open_gigs = (
        await db.execute(func.count(CampusGig.id).filter(CampusGig.status == "open"))
    ).scalar() or 0

    top_circles = (
        await db.execute(
            select(CampusCircle)
            .order_by(desc(CampusCircle.member_count))
            .limit(5)
        )
    ).scalars().all()

    recent_gigs = (
        await db.execute(
            select(CampusGig)
            .where(CampusGig.status == "open")
            .order_by(desc(CampusGig.created_at))
            .limit(5)
        )
    ).scalars().all()

    return {
        "university": uni,
        "stats": {
            "total_courses": total_courses,
            "total_resources": total_resources,
            "total_circles": total_circles,
            "open_gigs": open_gigs,
        },
        "top_circles": [
            {"id": c.id, "name": c.name, "member_count": c.member_count, "circle_type": c.circle_type}
            for c in top_circles
        ],
        "recent_gigs": [
            {
                "id": g.id, "title": g.title, "gig_type": g.gig_type,
                "budget_vit": g.budget_vit, "university": g.university,
            }
            for g in recent_gigs
        ],
    }


@router.get("/leaderboard")
async def campus_leaderboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top resource contributors by upload count."""
    rows = (
        await db.execute(
            select(
                AcademicResource.uploaded_by,
                func.count(AcademicResource.id).label("uploads"),
                func.sum(AcademicResource.downloads).label("total_downloads"),
            )
            .group_by(AcademicResource.uploaded_by)
            .order_by(desc("uploads"))
            .limit(20)
        )
    ).all()

    return {
        "leaderboard": [
            {"user_id": r.uploaded_by, "uploads": r.uploads, "total_downloads": r.total_downloads or 0}
            for r in rows
        ]
    }
