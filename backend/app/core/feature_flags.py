import os

class FeatureFlags:
    _cache: dict[str, bool] = {}

    @staticmethod
    def is_enabled(flag: str) -> bool:
        if flag in FeatureFlags._cache:
            return FeatureFlags._cache[flag]
        result = os.getenv(flag, "false").lower() == "true"
        FeatureFlags._cache[flag] = result
        return result

    @staticmethod
    def reset() -> None:
        FeatureFlags._cache.clear()

def is_feature_enabled(flag: str) -> bool:
    return FeatureFlags.is_enabled(flag)
