"""app/core/rate_limit.py
In-memory login rate limiter and per-user prediction rate limiter.
"""

import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Optional, Tuple

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


def check_login_allowed(email: str | None, ip: str | None = None):
    if email and _store.is_locked(email.lower()):
        raise ValueError(
            f"Too many failed login attempts. Account temporarily locked for "
            f"{LOCKOUT_SECONDS // 60} minutes."
        )
    if ip and _store.is_locked(ip):
        raise ValueError(
            f"Too many failed login attempts from this IP. "
            f"Try again in {LOCKOUT_SECONDS // 60} minutes."
        )


def record_login_failure(email: str | None, ip: str | None = None):
    if email:
        _store.record_failure(email.lower())
    if ip:
        _store.record_failure(ip)


def clear_login_failures(email: str | None):
    if email:
        _store.clear(email.lower())


# ── Per-user prediction rate limiter ─────────────────────────────────────────

from datetime import date as _date, datetime, timezone, timedelta
import threading

_pred_lock = threading.Lock()
_pred_counts: dict[int, dict] = {}


def _pred_today() -> str:
    return _date.today().isoformat()


def get_limit_for_tier(tier: str) -> int:
    """Return the daily prediction limit based on user tier."""
    from app.config import MAX_PREDICTIONS_PER_DAY

    tier = (tier or "free").lower()
    if tier in ("pro", "analyst"):
        return 100
    if tier == "elite":
        return 500
    return MAX_PREDICTIONS_PER_DAY


def check_prediction_limit(user_id: int, tier: str = "free") -> tuple[bool, int, int, str]:
    """
    Returns (allowed, current_count, limit, resets_at_utc_iso).
    """
    if user_id is None:
        return True, 0, 9999, ""

    limit = get_limit_for_tier(tier)
    today = _pred_today()
    tomorrow = (_date.today() + timedelta(days=1)).isoformat() + "T00:00:00Z"

    with _pred_lock:
        rec = _pred_counts.get(user_id)
        if rec is None or rec["date"] != today:
            _pred_counts[user_id] = {"date": today, "count": 0}
            rec = _pred_counts[user_id]
        return rec["count"] < limit, rec["count"], limit, tomorrow


def record_prediction(user_id: int) -> int:
    """Increment and return the new daily count for user_id."""
    if user_id is None:
        return 0
    today = _pred_today()
    with _pred_lock:
        rec = _pred_counts.get(user_id)
        if rec is None or rec["date"] != today:
            _pred_counts[user_id] = {"date": today, "count": 0}
        _pred_counts[user_id]["count"] += 1
        return _pred_counts[user_id]["count"]
