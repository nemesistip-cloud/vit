import logging
import time
from typing import Dict, Any, Optional, List
from app.core.observability.models import (
    TelemetryContext, MetricEntry, MetricType, LogLevel,
    AlertSeverity, HealthStatus, SystemDiagnostics
)

logger = logging.getLogger(__name__)

class ObservabilityManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ObservabilityManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.start_time = time.time()

        # Managers will be initialized here
        from app.core.observability.metrics import MetricsManager
        from app.core.observability.health import HealthManager
        from app.core.observability.tracing import TraceManager
        from app.core.observability.alerts import AlertManager
        from app.core.observability.audit import AuditManager
        from app.core.observability.diagnostics import DiagnosticsEngine

        self.metrics = MetricsManager()
        self.health = HealthManager()
        self.tracing = TraceManager()
        self.alerts = AlertManager()
        self.audit = AuditManager()
        self.diagnostics = DiagnosticsEngine(self)

    async def initialize(self, config: Dict[str, Any]):
        """Initialize all observability components."""
        logger.info("[obs] Initializing Observability Platform...")
        # Add component initialization logic if needed
        pass

    def get_context(self) -> TelemetryContext:
        """Get the current telemetry context from tracing manager."""
        return self.tracing.get_current_context()

    def record_metric(self, name: str, value: float, mtype: MetricType = MetricType.GAUGE, unit: str = "", labels: Dict[str, str] = None):
        self.metrics.record(name, value, mtype, unit, labels)

    def log(self, level: LogLevel, module: str, msg: str, extra: Dict[str, Any] = None):
        # This is usually handled by LoggerService/logging integration
        pass

    def emit_alert(self, severity: AlertSeverity, title: str, description: str, module_id: str, metadata: Dict[str, Any] = None):
        self.alerts.trigger(severity, title, description, module_id, self.get_context(), metadata)

    def audit_event(self, actor: str, action: str, resource: str, status: str = "success", details: Dict[str, Any] = None):
        self.audit.record(actor, action, resource, status, self.get_context(), details)

    def get_diagnostics(self) -> SystemDiagnostics:
        return self.diagnostics.generate_report()

obs_manager = ObservabilityManager()
