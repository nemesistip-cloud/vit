import os
from typing import Dict


class FeatureFlags:
    _flags: Dict[str, bool] = {}

    @classmethod
    def is_enabled(cls, flag_name: str) -> bool:
        if flag_name not in cls._flags:
            cls._flags[flag_name] = os.getenv(flag_name, "false").lower() == "true"
        return cls._flags[flag_name]

    @classmethod
    def reset(cls) -> None:
        cls._flags = {}


async def is_feature_enabled(db, flag_name: str, default: bool = False) -> bool:
    try:
        from sqlalchemy import select
        from app.modules.wallet.models import PlatformConfig

        row = (await db.execute(
            select(PlatformConfig).where(PlatformConfig.key == "feature_flags")
        )).scalar_one_or_none()
        if not row or not isinstance(row.value, dict):
            return default

        raw = row.value.get(flag_name)
        if isinstance(raw, dict):
            return bool(raw.get("value", default))
        if raw is None:
            return default
        return bool(raw)
    except Exception:
        return default
