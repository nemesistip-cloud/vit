import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class FeatureStore:
    """
    A centralized feature store to manage, version, and serve point-in-time consistent features.
    """
    def __init__(self):
        self._features_cache: Dict[str, List[Dict[str, Any]]] = {}
        logger.debug("FeatureStore initialized with point-in-time timestamp support.")

    def store_features(
        self,
        match_id: str,
        features: Dict[str, Any],
        version: str = "1.0",
        as_of_timestamp: Optional[str] = None
    ) -> None:
        key = f"{match_id}_{version}"
        if key not in self._features_cache:
            self._features_cache[key] = []

        ts = as_of_timestamp or datetime.now(timezone.utc).isoformat()
        record = {
            "match_id": str(match_id),
            "features": features,
            "version": version,
            "as_of_timestamp": ts
        }
        self._features_cache[key].append(record)
        self._features_cache[key].sort(key=lambda x: x["as_of_timestamp"])
        logger.debug("Stored features for match_id %s, version %s at as_of_timestamp %s.", match_id, version, ts)

    def get_features_for_match(
        self,
        match_id: str,
        version: str = "1.0",
        as_of_timestamp: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        key = f"{match_id}_{version}"
        records = self._features_cache.get(key, [])
        if not records:
            logger.debug("Features not found for match_id %s, version %s.", match_id, version)
            return None

        if as_of_timestamp is None:
            return records[-1]["features"]

        valid_records = [r for r in records if r["as_of_timestamp"] <= as_of_timestamp]
        if valid_records:
            return valid_records[-1]["features"]

        logger.debug("No features found for match_id %s on or before %s.", match_id, as_of_timestamp)
        return None

    def get_all_features(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._features_cache
