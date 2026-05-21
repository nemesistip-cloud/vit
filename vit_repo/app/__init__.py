"""VIT Sports Intelligence Network - Main Application Package"""
import sys
import os

# Ensure the root directory is in sys.path so we can import main
# This allows 'gunicorn app:app' to work when 'app' is this package.
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

def get_app():
    from main import app
    return app

# Gunicorn look for 'app' by default in the module/package
# We use a property-like trick or just delay the import
# Actually, gunicorn can call a factory, but Render's command is 'app:app'
# So we need an 'app' attribute.

class AppProxy:
    def __getattr__(self, name):
        from main import app
        return getattr(app, name)

    def __call__(self, *args, **kwargs):
        from main import app
        return app(*args, **kwargs)

app = AppProxy()

from app.config import APP_VERSION

__version__     = APP_VERSION
__author__      = "VIT Sports Intelligence"
__description__ = "13-Model Ensemble for Football Prediction with CLV Tracking"
