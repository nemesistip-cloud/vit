import asyncio
import csv
import hashlib
import io
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_env, APP_VERSION, AUTH_ENABLED, API_KEY
from app.db.database import AsyncSessionLocal, get_db
from app.db.models import User, AuditLog, Match, Prediction, SubscriptionPlan
from app.core.dependencies import get_orchestrator, get_telegram_alerts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

_KEY_REGISTRY = [
    {"name": "FOOTBALL_DATA_API_KEY", "label": "Football-Data.org", "required": True, "group": "Sports Data"},
    {"name": "ISPORTS_API_KEY", "label": "iSports API", "required": False, "group": "Sports Data"},
    {"name": "ODDS_API_KEY", "label": "The Odds API", "required": True, "group": "Sports Data"},
    {"name": "STRIPE_SECRET_KEY", "label": "Stripe", "required": False, "group": "Payments"},
    {"name": "JWT_SECRET_KEY", "label": "JWT Secret Key", "required": True, "group": "Security"},
    {"name": "GCS_BUCKET_NAME", "label": "GCS Bucket", "required": True, "group": "Infrastructure"},
]

@router.get("/api-keys")
async def list_api_keys():
    keys = []
    for entry in _KEY_REGISTRY:
        keys.append({**entry, "configured": bool(os.getenv(entry["name"])), "masked": "••••" if os.getenv(entry["name"]) else ""})
    return {"keys": keys}

@router.get("/config-status")
async def get_config_status():
    services = []
    for entry in _KEY_REGISTRY:
        services.append({"key": entry["name"], "label": entry["label"], "set": bool(os.getenv(entry["name"])), "status": "ok" if os.getenv(entry["name"]) else "warning"})
    return {"services": services, "summary": {"healthy": True}}

@router.get("/health")
async def admin_health():
    return {"status": "ok"}

@router.get("/models/status")
async def get_models_status():
    orch = get_orchestrator()
    if not orch: return {"ready": 0, "total": 0, "models": []}
    return orch.get_model_status()

@router.post("/models/reload")
async def reload_models():
    orch = get_orchestrator()
    if orch: orch.load_all_models()
    return {"status": "reloaded"}
