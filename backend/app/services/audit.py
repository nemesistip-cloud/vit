"""Admin audit logging service.

Writes structured audit entries to the existing AuditLog table.
Maps the canonical write_audit() signature onto the existing model fields:
  admin_id  → actor  (str representation)
  target_type → resource
  target_id   → resource_id
  before/after → details dict
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog

logger = logging.getLogger(__name__)


async def write_audit(
    db: AsyncSession,
    admin_id: int,
    action: str,
    target_type: str | None = None,
    target_id: Any = None,
    before: dict | None = None,
    after: dict | None = None,
    request: Any = None,
) -> None:
    """Write an audit log entry for any admin mutation.

    Args:
        db:          Active async database session.
        admin_id:    ID of the admin performing the action.
        action:      Short action slug, e.g. 'user.update', 'wallet.credit'.
        target_type: Type of the affected resource, e.g. 'user', 'match'.
        target_id:   PK / identifier of the affected resource.
        before:      State snapshot before the mutation.
        after:       State snapshot after the mutation.
        request:     FastAPI Request object (used to extract IP address).
    """
    try:
        ip = None
        if request is not None:
            client = getattr(request, "client", None)
            if client:
                ip = client.host

        details: dict = {}
        if before is not None:
            details["before"] = before
        if after is not None:
            details["after"] = after

        log = AuditLog(
            action=action,
            actor=str(admin_id),
            resource=target_type,
            resource_id=str(target_id) if target_id is not None else None,
            details=details if details else None,
            ip_address=ip,
            status="ok",
        )
        db.add(log)
        await db.commit()
    except Exception as exc:
        logger.error(f"Failed to write audit log: {exc}")
