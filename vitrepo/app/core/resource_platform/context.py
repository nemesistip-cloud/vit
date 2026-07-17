import asyncio
import uuid
from typing import Optional, Any, Dict
from dataclasses import dataclass, field
from app.core.observability.manager import obs_manager

@dataclass
class ExecutionContext:
    task_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: Optional[str] = None
    timeout: float = 300.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    _start_time: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    def __post_init__(self):
        if not self.trace_id:
            ctx = obs_manager.get_context()
            self.trace_id = ctx.trace_id or self.correlation_id

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def cancel(self):
        self._cancel_event.set()

    def get_remaining_time(self) -> float:
        elapsed = asyncio.get_event_loop().time() - self._start_time
        return max(0, self.timeout - elapsed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "timeout": self.timeout,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionContext':
        return cls(
            task_id=data["task_id"],
            correlation_id=data.get("correlation_id", str(uuid.uuid4())),
            trace_id=data.get("trace_id"),
            timeout=data.get("timeout", 300.0),
            metadata=data.get("metadata", {})
        )
