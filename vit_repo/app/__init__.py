"""VIT Sports Intelligence Network - Main Application Package"""
import sys
import os

# Ensure the root directory is in sys.path so we can import main
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Lazy attribute loading for 'app' to ensure Gunicorn finds it
# while avoiding circular dependencies during testing and module initialization.
def __getattr__(name):
    if name == "app":
        from main import app
        return app
    if name == "__version__":
        from app.config import APP_VERSION
        return APP_VERSION
    raise AttributeError(f"module {__name__} has no attribute {name}")

# This ensures that 'from app import app' or 'import app; app.app' works.
# PEP 562 (Python 3.7+) supports __getattr__ on modules.

__author__      = "VIT Sports Intelligence"
__description__ = "13-Model Ensemble for Football Prediction with CLV Tracking"
