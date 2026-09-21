import logging
from typing import List, Dict, Set, Optional
from app.core.registry.models import ModuleMetadata
from app.core.registry.contract import ModuleContract

logger = logging.getLogger(__name__)

class DependencyValidator:
    """Validates the ecosystem's module dependency graph."""

    def __init__(self, modules: Dict[str, ModuleContract]):
        self.modules = modules

    def validate_all(self):
        """Perform a full audit of the dependency graph."""
        errors = []

        # 1. Missing Dependencies
        for mid, module in self.modules.items():
            for dep in module.metadata.dependencies:
                if dep not in self.modules:
                    errors.append(f"Module '{mid}' requires missing dependency '{dep}'.")

        # 2. Circular Dependencies
        try:
            self._topological_sort()
        except ValueError as e:
            errors.append(str(e))

        if errors:
            raise ValueError(f"Dependency validation failed: {'; '.join(errors)}")

        logger.info("[registry] Dependency validation successful. Graph is clean.")

    def _topological_sort(self) -> List[str]:
        """Detect circular dependencies using a depth-first search."""
        visited = set()
        stack = []
        path = []

        def visit(mid):
            if mid in path:
                # Reconstruct circular path for better diagnostics
                cycle_start = path.index(mid)
                cycle_path = path[cycle_start:] + [mid]
                raise ValueError(f"Circular dependency detected: {' -> '.join(cycle_path)}")
            if mid in visited:
                return

            if mid not in self.modules:
                # Should be caught by missing dep check, but handle here for safety
                return

            path.append(mid)
            for dep in self.modules[mid].metadata.dependencies:
                visit(dep)
            path.pop()

            visited.add(mid)
            stack.append(mid)

        for mid in self.modules:
            visit(mid)
        return stack
