"""Adhoc script to help build models."""

import logging
from pathlib import Path

from archivepodcast.archiver.rss_models import RssFeed

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


FEEDS = [
    Path(__file__).parent / "instance" / "rss" / "lemon",
    Path(__file__).parent / "instance" / "rss" / "silver",
    Path(__file__).parent / "instance" / "rss" / "stown",
]


def _main() -> None:
    for feed_path in FEEDS:
        with feed_path.open("rb") as f:
            content = f.read()
        rss_model = RssFeed.from_bytes(content)

        if rss_model.rss is None:
            logger.error("No RSS data found in the feed.")
            continue

        if rss_model.rss.channel is None:
            logger.error("No channel data found in the RSS feed.")
            continue

        logger.info("Podcast Title: %s, Episodes: %d", rss_model.rss.channel.title, len(rss_model.rss.channel.items))


if __name__ == "__main__":
    _main()
