import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any
from app.config import get_env
from app.core.observability.tracing import _trace_id, _span_id, _correlation_id

class VITStructuredFormatter(logging.Formatter):
    """Refined structured JSON formatter for VIT Observability Platform."""

    APP_NAME = "vit-network"
    ENVIRONMENT = get_env("ENVIRONMENT", "development")
    VERSION = "1.1.0"

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "msg": record.getMessage(),
            "app": self.APP_NAME,
            "env": self.ENVIRONMENT,
            "ver": self.VERSION,
            "trace_id": getattr(record, "trace_id", _trace_id.get() or "-"),
            "span_id": getattr(record, "span_id", _span_id.get() or "-"),
            "correlation_id": getattr(record, "correlation_id", _correlation_id.get() or "-"),
            "request_id": getattr(record, "request_id", "-"),
        }

        # Attach exception info
        if record.exc_info:
            log_entry["exc"] = self.formatException(record.exc_info)
            log_entry["stack"] = traceback.format_exception(*record.exc_info)

        # Attach extra context fields
        for key, val in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "taskName",
                "message", "trace_id", "span_id", "correlation_id", "request_id"
            ):
                if not key.startswith("_"):
                    log_entry[key] = val

        return json.dumps(log_entry, default=str)

def setup_observability_logging(level: str = "INFO"):
    """Configure the centralized logging framework."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(VITStructuredFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    root_logger.addHandler(handler)

    # Configure specialized audit logger
    from app.core.observability.audit import audit_logger
    audit_handler = logging.StreamHandler()
    audit_handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)

    logging.getLogger("app.obs").info("VIT Observability Logging Initialized")

def get_obs_logger(name: str):
    return logging.getLogger(name)
