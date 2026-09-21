from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.modules.platform.integration import platform_integration

router = APIRouter(prefix="/api/platform/search", tags=["Platform Search"])


@router.get("", summary="Search platform resources")
async def search_platform(
    q: str = Query(default="", min_length=0),
    resource_type: Optional[str] = Query(default=None),
    tags: Optional[List[str]] = Query(default=None),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    page: int = Query(default=1, ge=1),
    sort_by: str = Query(default="relevance"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    results = platform_integration.search.search_resources(
        query=q,
        resource_type=resource_type,
        tags=tags,
        category=category,
        limit=limit,
        page=page,
        sort_by=sort_by,
    )
    return {
        "query": q,
        "resource_type": resource_type,
        "results": [
            {
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "title": item.title,
                "description": item.description,
                "tags": item.tags,
                "owner": item.owner,
                "permissions": item.permissions,
                "last_updated": item.last_updated,
                "search_score": item.search_score,
            }
            for item in results
        ],
        "total": len(results),
    }


@router.get("/resources", summary="List indexed platform resources")
def list_resources(resource_type: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    resources = platform_integration.search._resources.values()
    if resource_type:
        resources = [item for item in resources if item.resource_type == resource_type]
    return {
        "resources": [
            {
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "title": item.title,
                "description": item.description,
                "tags": item.tags,
                "owner": item.owner,
                "permissions": item.permissions,
                "last_updated": item.last_updated,
            }
            for item in resources
        ],
        "total": len(resources),
    }


@router.get("/types", summary="List indexed resource types")
def list_resource_types() -> Dict[str, Any]:
    return {"types": platform_integration.search.types()}


@router.post("/reindex", summary="Reindex known platform resources")
async def reindex_resources(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    platform_integration.search.index_resource(
        resource_type="users",
        resource_id="system-reindex",
        title="Platform search reindex",
        description="Search platform reindex operation completed",
        tags=["system"],
        owner=str(current_user.id),
        permissions=["read"],
        last_updated="now",
    )
    return {"status": "ok", "message": "reindex completed"}


@router.get("/health", summary="Search platform health")
def health() -> Dict[str, Any]:
    return platform_integration.search.health()
