# app/api/routes/__init__.py
"""API Routes Package"""

from app.api.routes import predict
from app.api.routes import result
from app.api.routes import history
from app.api.routes import admin
from app.api.routes import ai_feed

__all__ = [
    "predict",
    "result",
    "history",
    "admin",
    "ai_feed",
]