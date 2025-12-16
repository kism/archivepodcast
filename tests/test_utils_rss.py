from pathlib import Path

from archivepodcast.archiver.rss_models import RssFeed
from archivepodcast.utils.rss import feed_has_episodes
from tests.constants import DUMMY_RSS_STR


def test_feed_has_episodes_none() -> None:
    """Test feed_has_episodes with None input."""
    assert feed_has_episodes(None) is False


def test_feed_has_episodes_with_episodes() -> None:
    """Test feed_has_episodes with episodes present using RssFeed."""
    feed = RssFeed.from_bytes(DUMMY_RSS_STR.encode("utf-8"))
    assert feed_has_episodes(feed) is True


def test_feed_has_episodes_with_episodes_disk(tmp_path: Path) -> None:
    """Test feed_has_episodes with episodes present from disk using RssFeed."""
    rss_path = tmp_path / "test.rss"
    rss_path.write_text(DUMMY_RSS_STR)

    feed = RssFeed.from_bytes(rss_path.read_bytes())

    assert feed_has_episodes(feed) is True
