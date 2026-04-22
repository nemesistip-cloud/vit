"""app/core/rate_limit.py
In-memory login rate limiter.

Tracks failed login attempts per email address and per IP.
After MAX_ATTEMPTS failures within WINDOW_SECONDS the account/IP
is locked for LOCKOUT_SECONDS.

For single-instance deployments this is sufficient.
Multi-instance deployments should replace the _store dict with a
Redis-backed implementation.
"""

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300   # 5-minute sliding window
LOCKOUT_SECONDS = 900  # 15-minute lockout


class _AttemptStore:
    def __init__(self):
        self._lock = Lock()
        self._timestamps: Dict[str, List[float]] = defaultdict(list)

    def _prune(self, key: str, now: float):
        cutoff = now - WINDOW_SECONDS
        self._timestamps[key] = [t for t in self._timestamps[key] if t > cutoff]

    def record_failure(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._timestamps[key].append(now)
            count = len(self._timestamps[key])
        if count >= MAX_ATTEMPTS:
            logger.warning("Login rate-limit triggered for key=%s (attempts=%d)", key, count)
        return count

    def is_locked(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            return len(self._timestamps[key]) >= MAX_ATTEMPTS

    def clear(self, key: str):
        with self._lock:
            self._timestamps.pop(key, None)


_store = _AttemptStore()


def check_login_allowed(email: str, ip: str | None = None):
    """Raise ValueError if either the email or IP is locked out."""
    if _store.is_locked(email.lower()):
        raise ValueError(
            f"Too many failed login attempts. Account temporarily locked for "
            f"{LOCKOUT_SECONDS // 60} minutes."
        )
    if ip and _store.is_locked(ip):
        raise ValueError(
            f"Too many failed login attempts from this IP. "
            f"Try again in {LOCKOUT_SECONDS // 60} minutes."
        )


def record_login_failure(email: str, ip: str | None = None):
    _store.record_failure(email.lower())
    if ip:
        _store.record_failure(ip)


def clear_login_failures(email: str):
    _store.clear(email.lower())
