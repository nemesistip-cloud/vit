import re
import logging
from typing import Dict, Any, List, Optional
from app.modules.authz.models import AuthzEffect

logger = logging.getLogger(__name__)

class PolicyEvaluator:
    """Logic for evaluating ABAC conditions and patterns."""

    def match_pattern(self, pattern: str, value: str) -> bool:
        """Match an action or resource pattern (supports '*' wildcard)."""
        if pattern == "*" or pattern == value:
            return True

        # Convert glob-like pattern to regex
        regex_pattern = "^" + pattern.replace(".", "\\.").replace("*", ".*") + "$"
        return re.match(regex_pattern, value) is not None

    def evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Evaluate JSON-based condition logic.
        Example conditions: {"attr": "user.tier", "op": "eq", "value": "elite"}
        """
        if not conditions:
            return True

        # Simplified implementation for the initial version
        # Supports "all_of" (AND) and "any_of" (OR) nesting

        if "all_of" in conditions:
            return all(self.evaluate_conditions(c, context) for c in conditions["all_of"])

        if "any_of" in conditions:
            return any(self.evaluate_conditions(c, context) for c in conditions["any_of"])

        # Base condition: {attr, op, value}
        attr_path = conditions.get("attr")
        op = conditions.get("op", "eq")
        expected = conditions.get("value")

        if not attr_path:
            return True

        actual = self._get_context_value(attr_path, context)

        if op == "eq":
            return actual == expected
        elif op == "neq":
            return actual != expected
        elif op == "in":
            return actual in expected
        elif op == "contains":
            return expected in actual
        elif op == "gt":
            return actual > expected
        elif op == "lt":
            return actual < expected

        return False

    def _get_context_value(self, path: str, context: Dict[str, Any]) -> Any:
        """Resolve a dotted path in the context dictionary."""
        parts = path.split(".")
        current = context
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)

            if current is None:
                return None
        return current
