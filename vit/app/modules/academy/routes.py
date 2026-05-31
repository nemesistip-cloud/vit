"""Academic Repository API routes.
v5.1.0 — Course notes, past questions, and school-specific resources.
"""
from __future__ import annotations

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from app.modules.academy.models import Course, AcademicResource
from app.schemas.schemas import CourseCreate, CourseResponse, ResourceCreate, ResourceResponse
from app.modules.wallet.services import WalletService
from app.modules.notifications.service import NotificationService
from app.modules.tasks.service import TaskService
from app.modules.merit.service import record_merit_event

router = APIRouter(prefix="/api/academy", tags=["Academic Repository"])
logger = logging.getLogger(__name__)

@router.get("/courses", response_model=List[CourseResponse])
async def list_courses(
    university: Optional[str] = None,
    department: Optional[str] = None,
    level: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List courses, optionally filtered by user's university/dept if not provided."""
    uni = university or current_user.university
    dept = department or current_user.department

    q = select(Course)
    if uni:
        q = q.where(Course.university == uni)
    if dept:
        q = q.where(Course.department == dept)
    if level:
        q = q.where(Course.level == level)

    res = await db.execute(q)
    courses = res.scalars().all()
    return courses

@router.post("/courses", response_model=CourseResponse)
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new course entry."""
    existing = await db.execute(
        select(Course).where(Course.course_code == data.course_code, Course.university == data.university)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Course already exists in this university")

    course = Course(**data.model_dump(), created_by=current_user.id)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course

@router.get("/resources", response_model=List[ResourceResponse])
async def list_resources(
    course_id: int,
    resource_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List resources for a specific course."""
    q = select(AcademicResource).where(AcademicResource.course_id == course_id)
    if resource_type:
        q = q.where(AcademicResource.resource_type == resource_type)

    res = await db.execute(q)
    return res.scalars().all()

@router.post("/resources", response_model=ResourceResponse)
async def upload_resource(
    data: ResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new uploaded resource."""
    resource = AcademicResource(
        **data.model_dump(),
        uploaded_by=current_user.id
    )
    db.add(resource)

    current_user.total_xp += 10

    try:
        task_service = TaskService(db)
        await task_service.dispatch_trigger(current_user.id, "academic_resource_uploaded")
    except Exception as e:
        logger.warning(f"Failed to dispatch task trigger: {e}")

    try:
        wallet_service = WalletService(db)
        await wallet_service.credit(current_user.id, 2.0, "academic_contribution")

        from app.modules.merit.models import MeritEventType
        await record_merit_event(db, current_user.id, MeritEventType.ACADEMIC_RESOURCE_UPLOADED)
    except Exception as e:
        logger.warning(f"Failed to credit VIT for upload: {e}")

    try:
        notif_service = NotificationService(db)
        await notif_service.create(
            user_id=current_user.id,
            title="Resource Uploaded",
            content=f"Your resource '{resource.title}' has been uploaded and queued for verification. +2 VIT awarded.",
            type="info"
        )
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")

    await db.commit()
    await db.refresh(resource)
    return resource

@router.get("/search")
async def search_resources(
    query: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search courses and resources by text."""
    course_q = select(Course).where(
        (Course.course_code.ilike(f"%{query}%")) | (Course.course_title.ilike(f"%{query}%"))
    ).where(Course.university == current_user.university)

    res_courses = await db.execute(course_q)
    return {
        "courses": res_courses.scalars().all(),
    }

@router.post("/resources/{resource_id}/verify")
async def verify_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Verify an academic resource and pay out additional rewards."""
    res = await db.execute(select(AcademicResource).where(AcademicResource.id == resource_id))
    resource = res.scalar_one_or_none()
    if not resource:
        raise HTTPException(404, "Resource not found")

    if resource.is_verified:
        return {"status": "already_verified"}

    resource.is_verified = True

    reward_map = {"note": 5.0, "slide": 5.0, "past_question": 10.0, "textbook": 15.0}
    xp_map = {"note": 25, "slide": 25, "past_question": 50, "textbook": 75}

    reward = reward_map.get(resource.resource_type, 2.0)
    xp = xp_map.get(resource.resource_type, 10)

    if not resource.vit_reward_paid:
        try:
            wallet_service = WalletService(db)
            await wallet_service.credit(resource.uploaded_by, reward, "academic_verification")
            resource.vit_reward_paid = True

            from app.modules.merit.models import MeritEventType
            await record_merit_event(db, resource.uploaded_by, MeritEventType.ACADEMIC_RESOURCE_VERIFIED)

            user_res = await db.execute(select(User).where(User.id == resource.uploaded_by))
            uploader = user_res.scalar_one_or_none()
            if uploader:
                uploader.total_xp += xp

                try:
                    task_service = TaskService(db)
                    await task_service.dispatch_trigger(resource.uploaded_by, "academic_resource_verified")
                except Exception as te:
                    logger.warning(f"Failed to dispatch task trigger: {te}")

            notif_service = NotificationService(db)
            await notif_service.create(
                user_id=resource.uploaded_by,
                title="Resource Verified!",
                content=f"Your resource '{resource.title}' has been verified! +{reward} VIT and {xp} XP awarded.",
                type="success"
            )
        except Exception as e:
            logger.error(f"Failed to process verification rewards: {e}")

    await db.commit()
    return {"status": "verified", "reward": reward, "xp": xp}

@router.get("/tutor/ask")
async def ask_tutor(
    query: str,
    course_code: str,
    university: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ask the school-specific AI tutor a question with rate limiting."""
    is_premium = current_user.subscription_tier in ["pro", "elite"]

    from app.agents.academic_agent import AcademicAgent
    agent = AcademicAgent()

    uni = university or current_user.university or "Unknown University"

    response = await agent.get_tutor_response(query, uni, course_code)

    try:
        task_service = TaskService(db)
        await task_service.dispatch_trigger(current_user.id, "academic_session")
    except Exception as e:
        logger.warning(f"Failed to dispatch academic_session trigger: {e}")

    return {
        "query": query,
        "university": uni,
        "course_code": course_code,
        "response": response,
        "model": "VIT-Brain-v1-Academic",
        "is_premium": is_premium
    }
