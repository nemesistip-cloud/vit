import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from app.db.models import AuditLog

logger = logging.getLogger(__name__)


class AuditRepository:
    """Data access layer for audit logs.

    Wraps the canonical AuditLog model from app.db.models.
    Schema: action, actor, resource, resource_id, details, ip_address, status, timestamp.
    """

    def __init__(self, session):
        self.session = session

    async def log_change(
        self,
        module: str,
        entity: str,
        entity_id: Any,
        action: str,
        previous: Optional[Dict[str, Any]] = None,
        new: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
    ):
        """Record a data change in the audit log.

        Maps the legacy (module, entity, previous/new) interface to the
        canonical AuditLog model (resource, resource_id, details).
        """
        details_payload: Dict[str, Any] = {}
        if module:
            details_payload["module"] = module
        if previous is not None:
            details_payload["previous"] = previous
        if new is not None:
            details_payload["new"] = new
        if correlation_id:
            details_payload["correlation_id"] = correlation_id

        log_entry = AuditLog(
            action=action,
            actor=str(user_id) if user_id is not None else "system",
            resource=entity,
            resource_id=str(entity_id),
            details=details_payload or None,
            status="success",
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(log_entry)
        await self.session.flush()
        logger.debug("[audit] %s on %s:%s logged.", action, entity, entity_id)
