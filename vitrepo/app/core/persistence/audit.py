import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, JSON, DateTime, Text, Index
from app.db.database import Base

logger = logging.getLogger(__name__)

class AuditLog(Base):
    """Authoritative audit log for all data modifications."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_entity_action", "entity", "action"),
        Index("idx_audit_timestamp", "timestamp"),
        {"extend_existing": True}
    )

    id = Column(Integer, primary_key=True, index=True)
    module = Column(String(50), nullable=False, index=True)
    entity = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(100), nullable=False, index=True)
    action = Column(String(20), nullable=False) # CREATE, UPDATE, DELETE, RESTORE

    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)

    user_id = Column(Integer, nullable=True, index=True)
    correlation_id = Column(String(100), nullable=True, index=True)
    request_id = Column(String(100), nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=datetime.now(timezone.utc).isoformat())

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
