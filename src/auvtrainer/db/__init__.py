"""
Backend package entry.

Expose the FastAPI app factory for ASGI servers (uvicorn/gunicorn).
"""

from .run import app, create_app

__all__ = ["app", "create_app"]
