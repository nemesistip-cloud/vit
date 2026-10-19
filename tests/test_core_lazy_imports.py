import os
import subprocess
import sys
from pathlib import Path


def test_app_core_import_does_not_eagerly_load_dependency_container():
    repository_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((
        str(repository_root / "backend"),
        str(repository_root),
        environment.get("PYTHONPATH", ""),
    ))
    script = """
import sys
import types
import app.core

assert "app.core.dependencies" not in sys.modules
dependencies = types.ModuleType("app.core.dependencies")
sentinel = object()
dependencies.get_orchestrator = sentinel
sys.modules["app.core.dependencies"] = dependencies
assert app.core.get_orchestrator is sentinel
assert app.core.get_orchestrator is sentinel
"""

    subprocess.run(
        [sys.executable, "-c", script],
        cwd=repository_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )