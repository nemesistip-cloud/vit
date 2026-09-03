import pytest
import os
import asyncio
from app.core.swarm_orchestrator import init_swarm, get_swarm, set_swarm, SwarmOrchestrator
from app.agents.coordinator import AgentCoordinator

@pytest.mark.asyncio
async def test_swarm_orchestrator_initialization_and_scheduling(monkeypatch):
    # Set ENABLED_AGENTS to a specific subset
    monkeypatch.setenv("ENABLED_AGENTS", "performance-monitor,network-guardian")

    # Reset global swarm state for test
    import app.core.swarm_orchestrator as swarm_mod
    swarm_mod._SWARM = None

    coordinator = AgentCoordinator()

    # Disabled agents shouldn't be in coordinator._agents
    assert "performance-monitor" in coordinator._agents
    assert "network-guardian" in coordinator._agents
    assert "academic-tutor" not in coordinator._agents

    swarm = init_swarm(coordinator)
    assert get_swarm() == swarm

    # Check registered agents count
    assert len(swarm._agents) == 2
    assert "performance-monitor" in swarm._agents
    assert "network-guardian" in swarm._agents

    # Start scheduler
    swarm.start_scheduler()
    assert swarm._scheduler is not None
    assert swarm._scheduler.running is True

    # Test idempotency of start_scheduler
    swarm.start_scheduler()
    assert swarm._scheduler.running is True

    # Test clean shutdown
    swarm.stop_scheduler()
    assert swarm._scheduler is None
