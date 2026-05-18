# app/core/log_buffer.py
import logging
from collections import deque
from typing import List

class LogBufferHandler(logging.Handler):
    """A logging handler that keeps the last N log records in memory for AI diagnosis."""

    def __init__(self, capacity: int = 100):
        super().__init__()
        self.buffer = deque(maxlen=capacity)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append(msg)
        except Exception:
            self.handleError(record)

    def get_logs(self) -> List[str]:
        return list(self.buffer)

# Global buffer instance
log_buffer = LogBufferHandler()
