import logging
from graphlib import TopologicalSorter
from typing import Dict, List, Set, Any
from app.core.registry.contract import ModuleContract

logger = logging.getLogger(__name__)

class DependencyOrchestrator:
    """Orchestrates module execution based on dependency graph."""

    def __init__(self, modules: Dict[str, ModuleContract]):
        self.modules = modules
        self.ts = TopologicalSorter()
        self._build_graph()

    def _build_graph(self):
        """Construct the dependency graph for TopologicalSorter."""
        for mid, module in self.modules.items():
            # Mandatory dependencies
            deps = module.metadata.dependencies
            # Optional dependencies (if present in registry)
            opt_deps = [d for d in module.metadata.optional_dependencies if d in self.modules]

            all_deps = set(deps) | set(opt_deps)
            self.ts.add(mid, *all_deps)

    def get_execution_plan(self) -> List[Set[str]]:
        """
        Returns a list of sets where each set contains module IDs
        that can be initialized/started in parallel.
        """
        try:
            # Prepare returns an iterable of levels
            self.ts.prepare()
            plan = []
            while self.ts.is_active():
                ready = self.ts.get_ready()
                if not ready:
                    break
                plan.append(set(ready))
                # For planning purposes we mark them as done immediately
                # to get the full static plan.
                self.ts.done(*ready)
            return plan
        except Exception as e:
            logger.error(f"[orchestrator] Failed to generate execution plan: {e}")
            raise ValueError(f"Circular dependency or invalid graph detected: {e}")

    def get_sequential_order(self) -> List[str]:
        """Returns a flat list of module IDs in topological order."""
        plan = self.get_execution_plan()
        flat_order = []
        for level in plan:
            flat_order.extend(sorted(list(level)))
        return flat_order

    def get_dependents(self, module_id: str) -> Set[str]:
        """Find all modules that directly depend on the given module."""
        dependents = set()
        for mid, module in self.modules.items():
            if module_id in module.metadata.dependencies:
                dependents.add(mid)
        return dependents

    def validate_graph(self):
        """Perform a static validation of the graph."""
        try:
            # TopologicalSorter.prepare() will raise CycleError if circular
            sorter = TopologicalSorter()
            for mid, module in self.modules.items():
                sorter.add(mid, *module.metadata.dependencies)
            sorter.prepare()
            logger.info("[orchestrator] Dependency graph validated successfully.")
        except Exception as e:
            logger.error(f"[orchestrator] Graph validation failed: {e}")
            raise ValueError(f"Dependency graph validation failed: {e}")
