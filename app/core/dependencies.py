"""Dependency injection container for VIT application"""

import os
from functools import lru_cache
from typing import Optional

from fastapi import HTTPException

from app.pipelines.data_loader import DataLoader
from app.services.alerts import TelegramAlert
from services.ml_service.models.model_orchestrator import ModelOrchestrator


def _is_production() -> bool:
    """True when running in a Replit deployment (published app)."""
    return bool(os.getenv("REPLIT_DEPLOYMENT")) or os.getenv("ENVIRONMENT", "").lower() == "production"


def _has_trained_models() -> bool:
    """True when ≥4 trained PKL files are present in models/."""
    import glob
    return len(glob.glob("models/*.pkl")) >= 4


@lru_cache(maxsize=1)
def get_orchestrator() -> Optional[ModelOrchestrator]:
    """Lazy-load ModelOrchestrator singleton.

    Models are loaded whenever trained PKL files exist on disk (both dev and
    production).  This gives full VIT scoring in the development environment
    without any manual flag.  Set SKIP_MODEL_LOAD=1 to explicitly defer.
    """
    skip = os.getenv("SKIP_MODEL_LOAD", "").lower() in ("1", "true", "yes")
    should_load = not skip and (_is_production() or _has_trained_models())

    try:
        orch = ModelOrchestrator()
        if should_load:
            orch.load_all_models()
            print(f"✅ Orchestrator initialized: {orch.num_models_ready()} models ready")
        else:
            print("ℹ️  Model loading deferred — no trained PKLs found (run training first)")
        return orch
    except Exception as e:
        print(f"❌ Orchestrator init failed: {e}")
        import traceback
        traceback.print_exc()
        return None


@lru_cache(maxsize=1)
def get_data_loader() -> Optional[DataLoader]:
    """Lazy-load DataLoader singleton"""
    try:
        football_api_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
        odds_api_key = os.getenv("ODDS_API_KEY", "")

        loader = DataLoader(
            api_key=football_api_key,
            odds_api_key=odds_api_key,
            enable_scraping=os.getenv("ENABLE_SCRAPING", "false").lower() == "true",
            enable_odds=os.getenv("ENABLE_ODDS", "true").lower() == "true"
        )
        print(f"✅ DataLoader initialized (scraping={loader.enable_scraping}, odds={loader.enable_odds})")
        return loader
    except Exception as e:
        print(f"❌ DataLoader init failed: {e}")
        import traceback
        traceback.print_exc()
        return None


@lru_cache(maxsize=1)
def get_telegram_alerts() -> TelegramAlert:
    """Lazy-load TelegramAlert singleton"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if bot_token and chat_id:
        return TelegramAlert(bot_token, chat_id, enabled=True)
    return TelegramAlert("", "", enabled=False)


async def get_orchestrator_dep() -> ModelOrchestrator:
    """FastAPI dependency for orchestrator"""
    orch = get_orchestrator()
    if orch is None:
        raise HTTPException(status_code=503, detail="ML service not available")
    return orch


async def get_data_loader_dep() -> DataLoader:
    """FastAPI dependency for data loader"""
    loader = get_data_loader()
    if loader is None:
        raise HTTPException(status_code=503, detail="Data loader not available")
    return loader


async def get_telegram_dep() -> TelegramAlert:
    """FastAPI dependency for Telegram alerts"""
    return get_telegram_alerts()
