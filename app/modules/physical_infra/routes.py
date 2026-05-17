"""app/modules/physical_infra/routes.py
Physical Infrastructure Layer — DePIN IoT nodes, broadcast sync, stadium integration.

Reward amounts and broadcast-delay baselines are read from PlatformConfig where
available; constants serve as documented defaults only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.modules.wallet.models import PlatformConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/physical", tags=["Physical Infrastructure"])

_DEFAULT_SENSOR_REWARD_VIT = 0.5   # VIT per valid sensor packet (editable via admin)
_DEFAULT_BROADCAST_DELAY_MS = 4200  # baseline broadcast-to-market delay in ms


async def _cfg(db: AsyncSession, key: str, default):
    row = await db.execute(select(PlatformConfig).where(PlatformConfig.key == key))
    cfg = row.scalar_one_or_none()
    if cfg and cfg.value:
        return cfg.value
    return default


@router.post("/sensor-data")
async def submit_sensor_data(packet: dict, db: AsyncSession = Depends(get_db)):
    """
    Accept an IoT sensor packet from a registered DePIN node.

    The reward amount is read from PlatformConfig key ``depin_sensor_reward``.
    If no config exists the platform default (_DEFAULT_SENSOR_REWARD_VIT) is used.
    """
    cfg_val = await _cfg(db, "depin_sensor_reward", {})
    reward = float(cfg_val.get("vit_per_packet", _DEFAULT_SENSOR_REWARD_VIT))
    node_id = packet.get("node_id", "unknown")
    return {
        "status":    "received",
        "node_id":   node_id,
        "reward":    reward,
        "token":     "VIT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/broadcast-delay")
async def get_broadcast_delay(source: str, db: AsyncSession = Depends(get_db)):
    """
    Return the current measured broadcast-to-market delay for a named source.

    Delay values are stored in PlatformConfig key ``broadcast_delays``
    (dict of source→ms). Falls back to the platform default when not configured.
    """
    delays_cfg = await _cfg(db, "broadcast_delays", {})
    # Normalise key lookup (case-insensitive)
    src_key = source.lower()
    matched = next(
        (v for k, v in delays_cfg.items() if k.lower() == src_key), None
    )
    delay_ms = int(matched) if matched is not None else _DEFAULT_BROADCAST_DELAY_MS
    return {
        "source":   source,
        "delay_ms": delay_ms,
        "unit":     "milliseconds",
        "note":     "Configure per-source delays via Admin → PlatformConfig key 'broadcast_delays'",
    }
