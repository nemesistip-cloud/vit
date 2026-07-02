import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from app.core.observability.models import AuditRecord, TelemetryContext

# Isolated audit logger
audit_logger = logging.getLogger("vit.audit")
audit_logger.propagate = False # Prevent audit logs from leaking into app logs

class AuditManager:
    def __init__(self):
        # In production, these should be written to an immutable store
        self._history: List[AuditRecord] = []
        self._max_history = 1000

    def record(self, actor: str, action: str, resource: str, status: str, context: TelemetryContext, details: Dict[str, Any] = None):
        record = AuditRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            action=action,
            resource=resource,
            status=status,
            context=context,
            details=details or {}
        )

        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Log to isolated audit logger
        audit_logger.info(record.json())

    def get_records(self, limit: int = 100) -> List[AuditRecord]:
        return self._history[-limit:]
