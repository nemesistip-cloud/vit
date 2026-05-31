# app/core/logging_config.py
# Structured JSON logging for VIT Sports Intelligence Network
# Provides consistent, machine-parseable log output across all environments.

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from app.config import get_env


class StructuredFormatter(logging.Formatter):
    """Emits log records as single-line JSON for easy parsing by log aggregators."""

    APP_NAME = "vit-network"
    ENVIRONMENT = get_env("ENVIRONMENT", "development")

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "app": self.APP_NAME,
            "env": self.ENVIRONMENT,
        }

        # Include module / function / line for DEBUG
        if record.levelno <= logging.DEBUG:
            log_entry["loc"] = f"{record.module}:{record.funcName}:{record.lineno}"

        # Attach exception info
        if record.exc_info:
            log_entry["exc"] = self.formatException(record.exc_info)
            log_entry["traceback"] = traceback.format_exception(*record.exc_info)

        # Attach extra context fields set via logger.info(..., extra={"key": val})
        for key, val in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "taskName",
                "message",
            ):
                if not key.startswith("_"):
                    log_entry[key] = val

        try:
            return json.dumps(log_entry, default=str)
        except Exception:
            return json.dumps({"level": "ERROR", "msg": "Failed to serialize log entry", "original": str(record)})


class RequestContextFilter(logging.Filter):
    """Injects request_id into log records when available via contextvars."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    """
    Configure structured logging for the application.
    Call once at startup — safe to call multiple times (idempotent).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    environment = get_env("ENVIRONMENT", "development")

    # Use structured JSON in production, human-readable in development
    if environment in ("production", "staging"):
        formatter: logging.Formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    context_filter = RequestContextFilter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(context_filter)
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger("app.logging")
    logger.info(
        "Logging configured",
        extra={"log_level": level, "format": "structured" if environment == "production" else "plain"},
    )


def get_logger(name: str) -> logging.Logger:
    """Helper to get a named logger with the structured formatter applied."""
    return logging.getLogger(name)
