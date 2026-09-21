import logging
from typing import Dict, Set, Optional, List
from app.core.registry.models import ModuleStatus

logger = logging.getLogger(__name__)

class LifecycleStateMachine:
    """Deterministic state machine for VIT module lifecycles."""

    # Define valid transitions: previous_state -> {valid_next_states}
    TRANSITIONS: Dict[ModuleStatus, Set[ModuleStatus]] = {
        ModuleStatus.DISCOVERED: {ModuleStatus.REGISTERED, ModuleStatus.FAILED},
        ModuleStatus.REGISTERED: {ModuleStatus.VALIDATED, ModuleStatus.FAILED},
        ModuleStatus.VALIDATED: {ModuleStatus.INITIALIZING, ModuleStatus.FAILED},
        ModuleStatus.INITIALIZING: {ModuleStatus.INITIALIZED, ModuleStatus.FAILED},
        ModuleStatus.INITIALIZED: {ModuleStatus.STARTING, ModuleStatus.FAILED},
        ModuleStatus.STARTING: {ModuleStatus.RUNNING, ModuleStatus.READY, ModuleStatus.FAILED, ModuleStatus.DEGRADED},
        ModuleStatus.RUNNING: {ModuleStatus.READY, ModuleStatus.DEGRADED, ModuleStatus.PAUSED, ModuleStatus.STOPPING, ModuleStatus.FAILED},
        ModuleStatus.READY: {ModuleStatus.RUNNING, ModuleStatus.DEGRADED, ModuleStatus.PAUSED, ModuleStatus.STOPPING, ModuleStatus.FAILED},
        ModuleStatus.DEGRADED: {ModuleStatus.RUNNING, ModuleStatus.READY, ModuleStatus.RECOVERING, ModuleStatus.STOPPING, ModuleStatus.FAILED},
        ModuleStatus.PAUSED: {ModuleStatus.RUNNING, ModuleStatus.READY, ModuleStatus.STOPPING},
        ModuleStatus.STOPPING: {ModuleStatus.STOPPED, ModuleStatus.FAILED},
        ModuleStatus.STOPPED: {ModuleStatus.STARTING, ModuleStatus.SHUTDOWN},
        ModuleStatus.FAILED: {ModuleStatus.RECOVERING, ModuleStatus.STOPPING, ModuleStatus.SHUTDOWN},
        ModuleStatus.RECOVERING: {ModuleStatus.INITIALIZING, ModuleStatus.STARTING, ModuleStatus.RUNNING, ModuleStatus.FAILED},
        ModuleStatus.SHUTDOWN: set() # Terminal state
    }

    def __init__(self, module_id: str, initial_state: ModuleStatus = ModuleStatus.REGISTERED):
        self.module_id = module_id
        self.current_state = initial_state
        self._history: List[ModuleStatus] = [initial_state]

    def transition_to(self, next_state: ModuleStatus) -> bool:
        """Attempt to transition to a new state. Returns True if successful."""
        if next_state == self.current_state:
            return True

        valid_next = self.TRANSITIONS.get(self.current_state, set())

        if next_state not in valid_next:
            logger.error(
                f"[lifecycle] Invalid transition for {self.module_id}: "
                f"{self.current_state.value} -> {next_state.value}"
            )
            return False

        logger.info(
            f"[lifecycle] {self.module_id} transitioning: "
            f"{self.current_state.value} -> {next_state.value}"
        )
        self.current_state = next_state
        self._history.append(next_state)
        return True

    def can_transition_to(self, next_state: ModuleStatus) -> bool:
        """Check if a transition is valid without executing it."""
        if next_state == self.current_state:
            return True
        return next_state in self.TRANSITIONS.get(self.current_state, set())

    @property
    def history(self) -> List[ModuleStatus]:
        return self._history.copy()
