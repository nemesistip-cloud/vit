"""app/modules/physical_infra/routes.py
Physical Infrastructure Layer — Phase 13/37
DePIN IoT nodes, broadcast sync, and stadium integration.
"""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/api/physical", tags=["Physical Infrastructure"])

@router.post("/sensor-data")
async def submit_sensor_data(packet: dict):
    return {"status": "received", "reward": 0.5, "token": "VIT"}

@router.get("/broadcast-delay")
async def get_broadcast_delay(source: str):
    return {"source": source, "delay_ms": 4200}
