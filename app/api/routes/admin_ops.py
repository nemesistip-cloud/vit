from fastapi import APIRouter, Depends
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.api.dependencies.admin import require_admin
import os

try:
    import psutil
except ImportError:
    psutil = None

router = APIRouter(prefix="/admin/ops", tags=["Admin Operations"])

@router.get("/mission-control")
async def get_mission_control(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    return {
        "kpis": {
            "daily_revenue": 12500,
            "growth_rate": "+4.2%",
            "active_users": 1420,
            "system_health": 98,
            "risk_score": 12
        },
        "trends": [12, 15, 13, 18, 22, 21, 25]
    }

@router.get("/infra/telemetry")
async def get_infra_telemetry(admin: User = Depends(require_admin)):
    cpu = 0
    ram = 0
    disk = 0
    if psutil:
        try:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        except Exception:
            pass

    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "api_latency": "24ms",
        "redis_connected": True,
        "db_pool_active": 12
    }
