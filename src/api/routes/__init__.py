"""API route handlers."""

from .bugs import router as bugs_router
from .crawl import router as crawl_router
from .health import router as health_router

__all__ = ["crawl_router", "bugs_router", "health_router"]
