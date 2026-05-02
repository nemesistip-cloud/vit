"""app/agents/base.py — Base class for all autonomous background agents."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AgentStatus:
    IDLE       = "idle"
    RUNNING    = "running"
    OK         = "ok"
    ERROR      = "error"
    DISABLED   = "disabled"


class BaseAgent(ABC):
    """
    Autonomous asyncio agent that runs on a fixed interval.

    Subclasses implement `run_cycle()`. The base class handles:
    - interval sleeping with jitter-free initial delay
    - status/heartbeat tracking visible to the coordinator
    - error isolation (exceptions never kill the loop)
    - manual trigger via `trigger()` (sets an asyncio.Event)
    """

    def __init__(
        self,
        name: str,
        interval_seconds: int,
        initial_delay_seconds: int = 60,
        enabled: bool = True,
    ) -> None:
        self.name               = name
        self.interval_seconds   = interval_seconds
        self.initial_delay_s    = initial_delay_seconds
        self.enabled            = enabled

        self.status: str                 = AgentStatus.IDLE
        self.last_run_at: Optional[datetime]  = None
        self.next_run_at: Optional[datetime]  = None
        self.last_error: Optional[str]        = None
        self.run_count: int              = 0
        self.error_count: int            = 0
        self.last_result: Optional[Dict] = None

        self._trigger_event = asyncio.Event()

    def trigger(self) -> None:
        """Request an immediate out-of-schedule run."""
        self._trigger_event.set()
        logger.info("[agent:%s] manual trigger requested", self.name)

    @abstractmethod
    async def run_cycle(self) -> Dict[str, Any]:
        """Execute one work cycle. Return a result dict."""

    async def loop(self) -> None:
        """Main async loop — register with supervisor."""
        if not self.enabled:
            self.status = AgentStatus.DISABLED
            logger.info("[agent:%s] disabled — skipping", self.name)
            return

        logger.info(
            "[agent:%s] starting (interval=%ss delay=%ss)",
            self.name, self.interval_seconds, self.initial_delay_s,
        )
        await asyncio.sleep(self.initial_delay_s)

        while True:
            self.status = AgentStatus.RUNNING
            t0 = time.monotonic()
            try:
                result = await self.run_cycle()
                self.last_result  = result
                self.status       = AgentStatus.OK
                self.last_error   = None
                self.run_count   += 1
                self.last_run_at  = datetime.now(timezone.utc)
                elapsed = time.monotonic() - t0
                logger.info(
                    "[agent:%s] cycle complete in %.2fs run=%d",
                    self.name, elapsed, self.run_count,
                )
            except Exception as exc:
                self.status      = AgentStatus.ERROR
                self.last_error  = str(exc)
                self.error_count += 1
                logger.error("[agent:%s] cycle error: %s", self.name, exc, exc_info=True)

            next_run = datetime.now(timezone.utc).timestamp() + self.interval_seconds
            self.next_run_at = datetime.fromtimestamp(next_run, tz=timezone.utc)

            try:
                await asyncio.wait_for(
                    self._trigger_event.wait(),
                    timeout=self.interval_seconds,
                )
                self._trigger_event.clear()
                logger.info("[agent:%s] early trigger — running now", self.name)
            except asyncio.TimeoutError:
                pass

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable status snapshot."""
        return {
            "name":        self.name,
            "enabled":     self.enabled,
            "status":      self.status,
            "run_count":   self.run_count,
            "error_count": self.error_count,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_error":  self.last_error,
            "last_result": self.last_result,
            "interval_seconds": self.interval_seconds,
        }
