import logging
from typing import Dict, Any, Optional
from app.core.observability.manager import obs_manager

logger = logging.getLogger(__name__)

class IdentityAuditService:
    """Specialized Audit Service for Identity Operations."""

    def __init__(self):
        pass

    async def log_auth_event(self, gid: str, action: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Record an authentication related audit event."""
        obs_manager.audit_event(
            actor=gid,
            action=action,
            resource="identity.auth",
            status=status,
            details=details
        )
        logger.info(f"[identity-audit] {action} for {gid}: {status}")

    async def log_identity_change(self, gid: str, action: str, details: Optional[Dict[str, Any]] = None):
        """Record an identity modification event."""
        obs_manager.audit_event(
            actor="system",
            action=action,
            resource=f"identity.{gid}",
            status="success",
            details=details
        )
