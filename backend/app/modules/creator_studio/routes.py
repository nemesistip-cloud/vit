import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.modules.creator_studio.models import ContentType, ContentStatus
from app.modules.creator_studio.schemas import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    BrandMemoryCreate,
    BrandMemoryResponse,
    IdeaGenerateRequest,
    IdeaResponse,
    ContentGenerateRequest,
    ContentItemCreate,
    ContentItemUpdate,
    ContentItemResponse,
    XAccountConnectRequest,
    XAccountStatusResponse,
    AnalyticsSummaryResponse,
)
from app.modules.creator_studio.service import CreatorStudioService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/creator", tags=["VIT Creator Studio"])


# ── Brand Management Endpoints ───────────────────────────────────────────────

@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED, summary="Create brand persona")
async def create_brand(
    data: BrandCreate,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    brand = await service.create_brand(me.id, data)
    return brand


@router.get("/brands", response_model=List[BrandResponse], summary="List user brands")
async def list_brands(
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    return await service.get_user_brands(me.id)


@router.get("/brands/{brand_id}", response_model=BrandResponse, summary="Get brand details")
async def get_brand(
    brand_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    brand = await service.get_brand(brand_id, me.id)
    if not brand:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand persona not found")
    return brand


@router.patch("/brands/{brand_id}", response_model=BrandResponse, summary="Update brand persona")
async def update_brand(
    brand_id: str,
    data: BrandUpdate,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    brand = await service.update_brand(brand_id, me.id, data)
    if not brand:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand persona not found")
    return brand


# ── Brand Memory Endpoints ───────────────────────────────────────────────────

@router.post("/brands/{brand_id}/memory", response_model=BrandMemoryResponse, status_code=status.HTTP_201_CREATED, summary="Add brand memory entry")
async def add_memory(
    brand_id: str,
    data: BrandMemoryCreate,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    memory = await service.add_memory(brand_id, me.id, data)
    if not memory:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand persona not found")
    return memory


@router.get("/brands/{brand_id}/memory", response_model=List[BrandMemoryResponse], summary="Get brand memory entries")
async def list_memories(
    brand_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    return await service.get_memories(brand_id, me.id)


@router.delete("/brands/{brand_id}/memory/{memory_id}", summary="Delete brand memory entry")
async def delete_memory(
    brand_id: str,
    memory_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    success = await service.delete_memory(memory_id, brand_id, me.id)
    if not success:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Memory entry not found")
    return {"ok": True}


# ── Ideas Engine Endpoints ───────────────────────────────────────────────────

@router.post("/ideas/generate", response_model=List[IdeaResponse], summary="Generate content ideas")
async def generate_ideas(
    data: IdeaGenerateRequest,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    ideas = await service.generate_ideas(data.brand_id, me.id, data.topic, data.count)
    return ideas


@router.get("/brands/{brand_id}/ideas", response_model=List[IdeaResponse], summary="Get brand ideas bank")
async def list_ideas(
    brand_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    return await service.get_ideas(brand_id, me.id)


# ── AI Content Studio Endpoints ───────────────────────────────────────────────

@router.post("/content/generate", response_model=ContentItemResponse, status_code=status.HTTP_201_CREATED, summary="Generate AI content draft")
async def generate_content(
    data: ContentGenerateRequest,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    try:
        content_item = await service.generate_content(
            brand_id=data.brand_id,
            user_id=me.id,
            content_type=data.content_type,
            idea_id=data.idea_id,
            topic=data.topic,
            instructions=data.instructions,
            include_hooks=data.include_hooks,
        )
        return content_item
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err))


@router.get("/brands/{brand_id}/content", response_model=List[ContentItemResponse], summary="List content items / pipeline")
async def list_content_items(
    brand_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    return await service.get_content_items(brand_id, me.id, status=status_filter, limit=limit)


@router.patch("/brands/{brand_id}/content/{item_id}", response_model=ContentItemResponse, summary="Update content item or schedule")
async def update_content_item(
    brand_id: str,
    item_id: str,
    data: ContentItemUpdate,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    updated = await service.update_content_item(item_id, brand_id, me.id, data)
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content item not found")
    return updated


# ── X Integration & Publishing Endpoints ─────────────────────────────────────

@router.post("/brands/{brand_id}/x-account", response_model=XAccountStatusResponse, summary="Connect X account")
async def connect_x_account(
    brand_id: str,
    data: XAccountConnectRequest,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    try:
        conn = await service.connect_x_account(
            brand_id=brand_id,
            user_id=me.id,
            x_user_id=data.x_user_id,
            x_handle=data.x_handle,
            access_token=data.access_token,
            refresh_token=data.refresh_token,
        )
        return XAccountStatusResponse(
            is_connected=conn.is_connected,
            x_handle=conn.x_handle,
            x_user_id=conn.x_user_id,
            connected_at=conn.created_at,
        )
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err))


@router.post("/brands/{brand_id}/content/{item_id}/publish", response_model=ContentItemResponse, summary="Publish content immediately to X")
async def publish_content_now(
    brand_id: str,
    item_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    try:
        published_item = await service.publish_content_now(item_id, brand_id, me.id)
        return published_item
    except ValueError as err:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err))


# ── Growth Intelligence & Analytics Endpoints ─────────────────────────────────

@router.get("/brands/{brand_id}/analytics", response_model=AnalyticsSummaryResponse, summary="Get creator growth analytics")
async def get_creator_analytics(
    brand_id: str,
    me: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CreatorStudioService(db)
    return await service.get_analytics_summary(brand_id, me.id)
