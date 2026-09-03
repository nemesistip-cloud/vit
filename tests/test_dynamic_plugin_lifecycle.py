import pytest
import asyncio
from app.core.plugins.manager import plugin_manager
from app.core.lifecycle.manager import lifecycle_manager
from app.core.registry.models import ModuleStatus
from app.plugins.identity.plugin import IdentityPlugin

@pytest.mark.asyncio
async def test_dynamic_plugin_lifecycle_transitions(caplog):
    # Instantiate identity plugin
    plugin = IdentityPlugin()
    manifest = plugin.manifest

    # Load plugin dynamically
    loaded = await plugin_manager.load_plugin(manifest)
    assert loaded is True

    # Check state machine after load
    sm = lifecycle_manager._ensure_state_machine(manifest.plugin_id)
    assert sm.current_state == ModuleStatus.INITIALIZED

    # Activate all plugins
    await plugin_manager.activate_all()
    assert sm.current_state == ModuleStatus.READY

    # Verify start_modules skips re-triggering READY modules without errors
    await lifecycle_manager.start_modules()
    assert sm.current_state == ModuleStatus.READY

    # Check log for any invalid transition error
    for record in caplog.records:
        assert "Invalid transition" not in record.message

    # Test idempotency: call activate_all again
    await plugin_manager.activate_all()
    assert sm.current_state == ModuleStatus.READY
