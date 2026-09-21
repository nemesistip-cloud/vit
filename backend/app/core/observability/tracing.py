import uuid
import contextvars
from typing import Optional
from app.core.observability.models import TelemetryContext

# Context variables for distributed tracing
_trace_id = contextvars.ContextVar("trace_id", default=None)
_span_id = contextvars.ContextVar("span_id", default=None)
_parent_span_id = contextvars.ContextVar("parent_span_id", default=None)
_correlation_id = contextvars.ContextVar("correlation_id", default=None)

class TraceManager:
    def get_current_context(self) -> TelemetryContext:
        return TelemetryContext(
            trace_id=_trace_id.get(),
            span_id=_span_id.get(),
            parent_span_id=_parent_span_id.get(),
            correlation_id=_correlation_id.get()
        )

    def start_trace(self, trace_id: str = None, correlation_id: str = None):
        t_id = trace_id or str(uuid.uuid4())
        c_id = correlation_id or t_id
        _trace_id.set(t_id)
        _correlation_id.set(c_id)
        return t_id, c_id

    def start_span(self, name: str, parent_span_id: str = None):
        s_id = str(uuid.uuid4())
        _parent_span_id.set(parent_span_id or _span_id.get())
        _span_id.set(s_id)
        return s_id

    def clear(self):
        _trace_id.set(None)
        _span_id.set(None)
        _parent_span_id.set(None)
        _correlation_id.set(None)
