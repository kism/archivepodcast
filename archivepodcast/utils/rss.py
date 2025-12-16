"""Helper functions for rss processing."""

from archivepodcast.archiver.rss_models import RssFeed


def feed_has_episodes(feed: RssFeed | None) -> bool:
    """Check if the RSS feed has episodes using RssFeed model."""
    if isinstance(feed, RssFeed):
        return feed.has_episodes()
    return False
