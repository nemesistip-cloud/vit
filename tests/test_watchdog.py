import pytest

from app.services.watchdog import Watchdog


def test_watchdog_requires_unhealthy_threshold_and_cooldown():
    watchdog = Watchdog(failure_threshold=2, recovery_cooldown_seconds=300)
    watchdog.register("test", "http://127.0.0.1:9")
    state = watchdog.states["test"]
    state.state = "DEGRADED"
    state.consecutive_failures = 1
    assert watchdog.recovery_allowed("test") is False
    state.state = "UNHEALTHY"
    state.consecutive_failures = 2
    assert watchdog.recovery_allowed("test") is True
    watchdog.mark_recovering("test")
    assert watchdog.recovery_allowed("test") is False


@pytest.mark.asyncio
async def test_watchdog_probe_marks_unreachable_service_unhealthy():
    watchdog = Watchdog(failure_threshold=1)
    watchdog.register("test", "http://127.0.0.1:9")
    state = await watchdog.probe("test")
    assert state.state == "UNHEALTHY"
    assert state.consecutive_failures == 1
    assert state.error