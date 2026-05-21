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
        try:
            # First attempt: import app from main
            from main import app
            return app
        except (ImportError, AttributeError):
            # Fallback for complex circular situations: find the existing main module
            if 'main' in sys.modules:
                main_mod = sys.modules['main']
                if hasattr(main_mod, 'app'):
                    return main_mod.app
            # If all fails, raise an informative error
            raise AttributeError(f"Could not load 'app' from main. Ensure FastAPI instance is defined in main.py")
    if name == "__version__":
        from app.config import APP_VERSION
        return APP_VERSION
    raise AttributeError(f"module {__name__} has no attribute {name}")

# PEP 562 (Python 3.7+) supports __getattr__ on modules.

__author__      = "VIT Sports Intelligence"
__description__ = "13-Model Ensemble for Football Prediction with CLV Tracking"
