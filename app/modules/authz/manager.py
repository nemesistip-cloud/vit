import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.authz.engine import PolicyEngine
from app.modules.authz.models import AuthzEffect
from app.core.event_bus import event_bus
from app.core.observability.manager import obs_manager
from app.core.observability.models import TelemetryContext
from app.modules.authz import events

logger = logging.getLogger(__name__)

class AuthorizationManager:
    """
    Centralized authorization framework for the VIT ecosystem.
    Governs access to every subsystem, API, module, and resource.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AuthorizationManager, cls).__new__(cls)
            cls._instance.engine = PolicyEngine()
        return cls._instance

    async def check_permission(self,
                               db: AsyncSession,
                               user_id: int,
                               action: str,
                               resource: str = "*",
                               context: Dict[str, Any] = None) -> bool:
        """
        Evaluate if a user has permission to perform an action on a resource.
        """
        context = context or {}

        try:
            decision = await self.engine.evaluate(db, user_id, action, resource, context)

            is_allowed = decision == AuthzEffect.ALLOW

            # Record decision in Audit Log
            telemetry_ctx = TelemetryContext(
                user_id=str(user_id),
                request_id=context.get("request_id", "unknown")
            )

            obs_manager.audit.record(
                actor=f"user:{user_id}",
                action=action,
                resource=resource,
                status="GRANTED" if is_allowed else "DENIED",
                context=telemetry_ctx,
                details={"context": context}
            )

            # Publish event for denials or significant actions
            if not is_allowed:
                await event_bus.publish(
                    events.ACCESS_DENIED,
                    {"user_id": user_id, "action": action, "resource": resource},
                    sender="authz_manager"
                )
                logger.warning(f"[authz] Access denied for user {user_id} to {action} on {resource}")

            return is_allowed

        except Exception as e:
            logger.error(f"[authz] Authorization evaluation error: {e}")
            # Fail closed on error
            return False

# Global Instance
authz_manager = AuthorizationManager()
