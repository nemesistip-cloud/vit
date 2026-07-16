"""Campus Circles (Communities) API routes — v5.6"""
from __future__ import annotations

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.auth.dependencies import get_current_user
from app.modules.academy.models import CampusCircle, CampusPost, CampusComment

router = APIRouter(prefix="/api/campus/circles", tags=["Campus Circles"])
logger = logging.getLogger(__name__)


class CircleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    circle_type: str = "general"
    university: str
    faculty: Optional[str] = None
    department: Optional[str] = None


class PostCreate(BaseModel):
    content: str
    media_urls: Optional[List[str]] = None


class CommentCreate(BaseModel):
    content: str


@router.get("")
async def list_circles(
    university: Optional[str] = Query(None),
    circle_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uni = university or getattr(current_user, "university", None)
    q = select(CampusCircle)
    if uni:
        q = q.where(CampusCircle.university == uni)
    if circle_type:
        q = q.where(CampusCircle.circle_type == circle_type)
    q = q.order_by(desc(CampusCircle.member_count))
    result = await db.execute(q)
    circles = result.scalars().all()
    return [
        {
            "id": c.id, "name": c.name, "description": c.description,
            "circle_type": c.circle_type, "university": c.university,
            "faculty": c.faculty, "department": c.department,
            "member_count": c.member_count,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in circles
    ]


@router.post("")
async def create_circle(
    data: CircleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(
        select(CampusCircle).where(
            CampusCircle.name == data.name,
            CampusCircle.university == data.university
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "A circle with that name already exists at this university")

    circle = CampusCircle(**data.model_dump())
    db.add(circle)
    await db.commit()
    await db.refresh(circle)
    return {"id": circle.id, "name": circle.name, "message": "Circle created"}


@router.get("/{circle_id}/posts")
async def list_posts(
    circle_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    circle = await db.get(CampusCircle, circle_id)
    if not circle:
        raise HTTPException(404, "Circle not found")

    result = await db.execute(
        select(CampusPost)
        .where(CampusPost.circle_id == circle_id)
        .order_by(desc(CampusPost.is_pinned), desc(CampusPost.created_at))
        .limit(50)
    )
    posts = result.scalars().all()
    return [
        {
            "id": p.id, "content": p.content, "media_urls": p.media_urls,
            "upvotes": p.upvotes, "is_pinned": p.is_pinned,
            "author_id": p.author_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in posts
    ]


@router.post("/{circle_id}/posts")
async def create_post(
    circle_id: int,
    data: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    circle = await db.get(CampusCircle, circle_id)
    if not circle:
        raise HTTPException(404, "Circle not found")

    post = CampusPost(
        circle_id=circle_id,
        author_id=current_user.id,
        content=data.content,
        media_urls=data.media_urls or [],
    )
    db.add(post)
    circle.member_count = (circle.member_count or 0) + 1
    await db.commit()
    await db.refresh(post)
    return {"id": post.id, "message": "Post created"}


@router.post("/{circle_id}/posts/{post_id}/upvote")
async def upvote_post(
    circle_id: int,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = await db.get(CampusPost, post_id)
    if not post or post.circle_id != circle_id:
        raise HTTPException(404, "Post not found")
    post.upvotes = (post.upvotes or 0) + 1
    await db.commit()
    return {"upvotes": post.upvotes}


@router.get("/{circle_id}/posts/{post_id}/comments")
async def list_comments(
    circle_id: int,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CampusComment)
        .where(CampusComment.post_id == post_id)
        .order_by(CampusComment.created_at)
    )
    comments = result.scalars().all()
    return [
        {
            "id": c.id, "content": c.content, "author_id": c.author_id,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]


@router.post("/{circle_id}/posts/{post_id}/comments")
async def add_comment(
    circle_id: int,
    post_id: int,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = await db.get(CampusPost, post_id)
    if not post or post.circle_id != circle_id:
        raise HTTPException(404, "Post not found")

    comment = CampusComment(
        post_id=post_id,
        author_id=current_user.id,
        content=data.content,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {"id": comment.id, "message": "Comment added"}
