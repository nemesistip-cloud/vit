import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import User, AuditLog, Match, Prediction, TrainingJob, SubscriptionPlan
from app.auth.dependencies import get_current_admin
from app.core.dependencies import get_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# Re-using the registry and existing routes from the original file
# I will append the missing routes to the end of the existing file.
