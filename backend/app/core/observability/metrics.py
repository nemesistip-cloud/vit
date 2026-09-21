import time
from typing import Dict, List, Any, Optional
from threading import Lock
from app.core.observability.models import MetricEntry, MetricType

class MetricsManager:
    def __init__(self):
        self._metrics: List[MetricEntry] = []
        self._lock = Lock()
        self._max_history = 1000

    def record(self, name: str, value: float, mtype: MetricType = MetricType.GAUGE, unit: str = "", labels: Dict[str, str] = None):
        entry = MetricEntry(
            name=name,
            value=value,
            type=mtype,
            unit=unit,
            labels=labels or {}
        )
        with self._lock:
            self._metrics.append(entry)
            if len(self._metrics) > self._max_history:
                self._metrics.pop(0)

    def get_snapshot(self) -> List[MetricEntry]:
        with self._lock:
            return list(self._metrics)

    def clear(self):
        with self._lock:
            self._metrics.clear()
