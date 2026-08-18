"""Routers for ArchivePodcast."""

from .api import router as api_router
from .content import router as content_router
from .rss import router as rss_router
from .static import router as static_router
from .webpages import router as webpages_router

__all__ = [
    "api_router",
    "content_router",
    "rss_router",
    "static_router",
    "webpages_router",
]
