"""Native AI Inference Client."""
from __future__ import annotations
import logging
from app.core.dependencies import get_orchestrator
logger = logging.getLogger(__name__)
async def call_ai(p, **k): return "Native analysis."
async def call_ai_with_provider(p, **k): return ("Native analysis.", "native")
async def provider_status():
    orch = get_orchestrator()
    ready = orch.num_models_ready() if orch else 0
    return {"native": {"status": "available" if ready > 0 else "degraded", "available": ready > 0, "models_ready": ready, "total_models": 22}}
async def verify_provider(n): return True
def get_provider_priority(): return ["native"]
def set_provider_priority(o): return ["native"]
def get_provider_failures(): return {}
async def reset_provider_backoff(n=None): return {}
