"""Helper functions for rss processing."""

from typing import Any

from archivepodcast.archiver.rss_models import RssFeed


def feed_has_episodes(feed: RssFeed | Any | None) -> bool:
    """Check if the RSS feed has episodes using RssFeed model."""
    if feed is None:
        return False
    if isinstance(feed, RssFeed):
        return feed.has_episodes()
    return False
