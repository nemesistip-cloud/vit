import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from app.core.observability.models import SubsystemHealth, HealthStatus

class HealthManager:
    def __init__(self):
        self._subsystems: Dict[str, SubsystemHealth] = {}

    def update_status(self, name: str, status: HealthStatus, message: str = None, details: Dict[str, Any] = None):
        self._subsystems[name] = SubsystemHealth(
            name=name,
            status=status,
            last_check=datetime.now(timezone.utc),
            message=message,
            details=details or {}
        )

    def get_subsystem_status(self, name: str) -> Optional[SubsystemHealth]:
        return self._subsystems.get(name)

    def get_all_statuses(self) -> List[SubsystemHealth]:
        return list(self._subsystems.values())

    def get_overall_status(self) -> HealthStatus:
        if not self._subsystems:
            return HealthStatus.UNKNOWN

        statuses = [s.status for s in self._subsystems.values()]
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN
