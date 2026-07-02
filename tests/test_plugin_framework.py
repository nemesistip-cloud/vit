import pytest
import json
from app.core.plugins.models import PluginManifest
from app.core.plugins.resolver import DependencyResolver

def test_dependency_resolution():
    manifests = {
        "a": PluginManifest(plugin_id="a", name="A", version="1.0.0", platform_version="1.0.0", dependencies={"b": ">=1.0.0"}),
        "b": PluginManifest(plugin_id="b", name="B", version="1.0.0", platform_version="1.0.0", dependencies={})
    }
    resolver = DependencyResolver(manifests)
    order = resolver.resolve_order()
    assert order == ["b", "a"]

def test_circular_dependency():
    manifests = {
        "a": PluginManifest(plugin_id="a", name="A", version="1.0.0", platform_version="1.0.0", dependencies={"b": "1.0.0"}),
        "b": PluginManifest(plugin_id="b", name="B", version="1.0.0", platform_version="1.0.0", dependencies={"a": "1.0.0"})
    }
    resolver = DependencyResolver(manifests)
    with pytest.raises(ValueError, match="Circular plugin dependency detected"):
        resolver.resolve_order()
