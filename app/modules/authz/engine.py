import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.authz.models import Policy, AuthzEffect, Role, Permission, user_roles
from app.modules.authz.evaluator import PolicyEvaluator

logger = logging.getLogger(__name__)

class PolicyEngine:
    """Orchestrates authorization decisions by evaluating RBAC and ABAC policies."""

    def __init__(self):
        self.evaluator = PolicyEvaluator()

    async def evaluate(self,
                       db: AsyncSession,
                       user_id: int,
                       action: str,
                       resource: str,
                       context: Dict[str, Any]) -> AuthzEffect:
        """
        Main evaluation entry point.
        Follows 'Default Deny' and 'Deny Overrides Allow' principles.
        """

        # 1. Evaluate ABAC Policies first (explicit Deny/Allow)
        policies = await self._fetch_matching_policies(db, action, resource)

        # Evaluate policies sorted by priority
        policies.sort(key=lambda p: p.priority, reverse=True)

        has_allow = False
        for policy in policies:
            if self.evaluator.evaluate_conditions(policy.conditions, context):
                if policy.effect == AuthzEffect.DENY:
                    logger.info(f"[authz] Explicit DENY by policy: {policy.name}")
                    return AuthzEffect.DENY
                if policy.effect == AuthzEffect.ALLOW:
                    has_allow = True

        if has_allow:
            return AuthzEffect.ALLOW

        # 2. Evaluate RBAC if no ABAC policy matched or yielded ALLOW
        if await self._check_rbac(db, user_id, action):
            return AuthzEffect.ALLOW

        return AuthzEffect.DENY

    async def _fetch_matching_policies(self, db: AsyncSession, action: str, resource: str) -> List[Policy]:
        """Fetch all active policies that match the action and resource patterns."""
        stmt = select(Policy).where(Policy.is_active == True)
        result = await db.execute(stmt)
        all_policies = result.scalars().all()

        return [
            p for p in all_policies
            if self.evaluator.match_pattern(p.action_pattern, action) and
               self.evaluator.match_pattern(p.resource_pattern, resource)
        ]

    async def _check_rbac(self, db: AsyncSession, user_id: int, permission_slug: str) -> bool:
        """Check if any of the user's roles grant the requested permission."""

        stmt = (
            select(Permission)
            .join(Permission.roles)
            .join(user_roles, Role.id == user_roles.c.role_id)
            .where(user_roles.c.user_id == user_id)
            .where(Permission.slug == permission_slug)
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None


class PolicyValidator:
    """Validates policy structure and patterns."""

    @staticmethod
    def validate_action(action: str) -> bool:
        # Simple validation: allow letters, numbers, dots, and asterisks
        import re
        return bool(re.match(r'^[a-z0-9\.\*]+$', action))

    @staticmethod
    def validate_conditions(conditions: Dict[str, Any]) -> bool:
        # Basic recursive check for required keys in ABAC conditions
        if not conditions:
            return True

        if "all_of" in conditions or "any_of" in conditions:
            nested = conditions.get("all_of") or conditions.get("any_of")
            if not isinstance(nested, list):
                return False
            return all(PolicyValidator.validate_conditions(c) for c in nested)

        return "attr" in conditions and "op" in conditions and "value" in conditions
