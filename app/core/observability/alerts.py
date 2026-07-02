import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any
from app.core.observability.models import Alert, AlertSeverity, TelemetryContext

class AlertManager:
    def __init__(self):
        self._alerts: List[Alert] = []
        self._max_history = 100

    def trigger(self, severity: AlertSeverity, title: str, description: str, module_id: str, context: TelemetryContext, metadata: Dict[str, Any] = None):
        alert = Alert(
            id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            description=description,
            module_id=module_id,
            timestamp=datetime.now(timezone.utc),
            context=context,
            metadata=metadata or {}
        )
        self._alerts.append(alert)
        if len(self._alerts) > self._max_history:
            self._alerts.pop(0)

        # In a real system, this might push to PagerDuty/Slack/Email
        import logging
        logger = logging.getLogger("app.alerts")
        logger.error(f"[ALERT] {severity.value}: {title} - {description} (module: {module_id})")

    def get_active_alerts(self) -> List[Alert]:
        return list(self._alerts)
