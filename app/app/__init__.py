"""VIT Sports Analytics Network - Main Application Package"""

from app.config import APP_VERSION

__version__     = APP_VERSION
__author__      = "VIT Sports Analytics"
__description__ = "13-Model Ensemble for Football Prediction with CLV Tracking"

def __getattr__(name):
    """
    Lazy-export the 'app' instance from main.py to satisfy Gunicorn's 'app:app'
    pattern while avoiding circular imports during initialization.
    """
    if name == "app":
        from main import app
        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
