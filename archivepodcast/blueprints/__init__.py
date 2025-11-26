"""Blueprints for ArchivePodcast."""

from .api import bp as bp_api
from .content import bp as bp_content
from .rss import bp as bp_rss
from .static import bp as bp_static
from .webpages import bp as bp_webpages

__all__ = [
    "bp_api",
    "bp_content",
    "bp_rss",
    "bp_static",
    "bp_webpages",
]
