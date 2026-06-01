import os
class FeatureFlags:
    @staticmethod
    def is_enabled(flag: str) -> bool:
        return os.getenv(flag, "false").lower() == "true"
    @staticmethod
    def reset(): pass

def is_feature_enabled(flag: str) -> bool:
    return FeatureFlags.is_enabled(flag)
