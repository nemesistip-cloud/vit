import time
from datetime import datetime, timezone
from typing import Dict, Any, TYPE_CHECKING
from app.core.observability.models import SystemDiagnostics, HealthStatus

if TYPE_CHECKING:
    from app.core.observability.manager import ObservabilityManager

class DiagnosticsEngine:
    def __init__(self, manager: 'ObservabilityManager'):
        self.manager = manager

    def generate_report(self) -> SystemDiagnostics:
        from app.core.kernel import kernel

        k_status = kernel.get_status()
        health_summary = self.manager.health.get_overall_status()

        return SystemDiagnostics(
            timestamp=datetime.now(timezone.utc),
            kernel_state=k_status.get("kernel_state", "UNKNOWN"),
            uptime_seconds=k_status.get("uptime_seconds", 0.0),
            health_summary=health_summary,
            subsystems=self.manager.health.get_all_statuses(),
            metrics_snapshot=self.manager.metrics.get_snapshot()[-20:] # Last 20 metrics
        )
