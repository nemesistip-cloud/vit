"""VITPredict application catalog, health, and compatibility-owned API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.routes.matches import router as matches_router
from app.api.routes.odds_compare import router as odds_router
from app.api.routes.predict import router as predictions_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.analytics import get_user_leaderboard
from app.modules.vitpredict.manifest import vitpredict_manifest
from app.modules.developer.models import DeveloperApp

router = APIRouter(tags=["Applications"])
vitpredict_api = APIRouter(prefix="/api/apps/vitpredict", tags=["VITPredict"])


@router.get("/api/apps", summary="List discoverable VIT applications")
async def list_applications(db: AsyncSession = Depends(get_db)) -> list[dict]:
    manifest = vitpredict_manifest().to_dict()
    applications = [
        {
            "id": manifest["app_id"],
            "slug": "vitpredict",
            "name": "VITPredict",
            "description": "Football prediction intelligence, match analysis, and model evaluation.",
            "category": "prediction-intelligence",
            "availability": "available",
            "integration_status": "preview",
            "version": manifest["version"],
            "launch_path": "/apps/vitpredict",
            "api_base_path": "/api/apps/vitpredict",
            "manifest": manifest,
        }
    ]
    result = await db.scalars(
        select(DeveloperApp).where(DeveloperApp.status == "published").order_by(DeveloperApp.name.asc())
    )
    applications.extend(
        {
            "id": app.app_id,
            "slug": app.app_id.removeprefix("app:"),
            "name": app.name,
            "description": app.description or "",
            "category": (app.category or "general").lower().replace(" ", "-"),
            "availability": "available",
            "integration_status": "published",
            "version": "1.0.0",
            "launch_path": "/applications",
            "launch_url": app.prod_url,
        }
        for app in result.all()
    )
    return applications


@vitpredict_api.get("/manifest", summary="Get the VITPredict application manifest")
async def get_vitpredict_manifest() -> dict:
    return vitpredict_manifest().to_dict()


@vitpredict_api.get("/health", summary="Check VITPredict's shared database dependency")
async def get_vitpredict_health(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"app_id": "app:vitpredict", "status": "degraded", "dependency": "database"},
        ) from exc

    return {
        "app_id": "app:vitpredict",
        "status": "available",
        "checks": {"gateway": "available", "database": "available"},
        "checked_dependencies": ["gateway", "database"],
    }


vitpredict_api.include_router(matches_router)
vitpredict_api.include_router(predictions_router)
vitpredict_api.include_router(odds_router)
vitpredict_api.include_router(dashboard_router, prefix="/dashboard")
router.include_router(vitpredict_api)


@vitpredict_api.get("/analytics/leaderboard/users", summary="VITPredict user prediction leaderboard")
async def vitpredict_user_leaderboard(
    sort_by: str = "xp",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await get_user_leaderboard(sort_by=sort_by, limit=limit, db=db)