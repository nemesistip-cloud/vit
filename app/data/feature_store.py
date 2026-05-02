import json
from datetime import datetime
from typing import Dict, Any, Optional

class FeatureStore:
    """
    A centralized feature store to manage, version, and serve consistent features.
    Uses an in-memory dictionary for development; swap for a DB-backed store in production.
    """
    def __init__(self):
        self._features_cache: Dict[str, Dict[str, Any]] = {}
        print("FeatureStore initialized (in-memory mock).")

    def store_features(self, match_id: str, features: Dict[str, Any], version: str = "1.0") -> None:
        """
        Stores engineered features for a specific match.

        Args:
            match_id (str): The unique identifier of the match.
            features (Dict[str, Any]): The dictionary of engineered features.
            version (str): The version of the feature set.
        """
        key = f"{match_id}_{version}"
        self._features_cache[key] = {
            "match_id": match_id,
            "features": features,
            "version": version,
            "timestamp": datetime.now().isoformat()
        }
        print(f"Stored features for match_id {match_id}, version {version}.")

    def get_features_for_match(self, match_id: str, version: str = "1.0") -> Optional[Dict[str, Any]]:
        """
        Retrieves engineered features for a specific match and version.

        Args:
            match_id (str): The unique identifier of the match.
            version (str): The version of the feature set to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The features dictionary if found, otherwise None.
        """
        key = f"{match_id}_{version}"
        retrieved_data = self._features_cache.get(key)
        if retrieved_data:
            print(f"Retrieved features for match_id {match_id}, version {version}.")
            return retrieved_data['features']
        print(f"Features not found for match_id {match_id}, version {version}.")
        return None

    def get_all_features(self) -> Dict[str, Dict[str, Any]]:
        """Retrieves all stored features."""
        return self._features_cache
