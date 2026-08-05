import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from app.db.models import AuditLog

logger = logging.getLogger(__name__)

class AuditRepository:
    """Data access layer for audit logs."""

    def __init__(self, session):
        self.session = session

    async def log_change(self, module: str, entity: str, entity_id: Any,
                         action: str, previous: Optional[Dict[str, Any]] = None,
                         new: Optional[Dict[str, Any]] = None,
                         user_id: Optional[int] = None,
                         correlation_id: Optional[str] = None):
        """Record a data change in the audit log."""
        log_entry = AuditLog(
            module=module,
            entity=entity,
            entity_id=str(entity_id),
            action=action,
            previous_state=previous,
            new_state=new,
            user_id=user_id,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc)
        )
        self.session.add(log_entry)
        await self.session.flush()
        logger.debug(f"[audit] {action} on {entity}:{entity_id} logged.")
