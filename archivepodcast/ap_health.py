"""Archivepodcast health module."""

import datetime
import json

from lxml import etree

from .logger import get_logger

logger = get_logger(__name__)

PODCAST_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S %z"

class LatestEpisodeInfo:
    """Episode Info object."""

    def __init__(self, tree: etree._ElementTree | None = None) -> None:
        """Initialise the Episode Info object."""
        self.title = "Unknown"
        self.pubdate = 0

        if tree:
            try:
                latest_episode = tree.xpath("//item")[0]
                self.title = latest_episode.xpath("title")[0].text
                pod_pubdate = latest_episode.xpath("pubDate")[0].text

                self.pubdate = int(datetime.datetime.strptime(pod_pubdate, PODCAST_DATE_FORMAT).timestamp())
            except Exception:
                logger.exception("Error parsing latest episode info")


class PodcastHealth:
    """Podcast Health object."""

    def __init__(self) -> None:
        """Initialise the Podcast Health object."""
        self.rss_available: bool = False
        self.rss_live: bool = False
        self.last_fetched: int = 0
        self.healthy: bool = False
        self.latest_episode_info: LatestEpisodeInfo = LatestEpisodeInfo()


class WebpageHealth:
    """Webpage Health object."""

    def __init__(self) -> None:
        """Initialise the Webpage Health object."""
        self.last_rendered: int = 0


class CoreHealth:
    """Core Health object."""

    def __init__(self) -> None:
        """Initialise the Core Health object."""
        self.alive: bool = True
        self.last_run: int = 0
        self.about_page_exists: bool = False
        self.last_startup: int = int(datetime.datetime.now().timestamp())


class PodcastArchiverHealth:
    """Podcast Archiver Health object."""

    def __init__(self) -> None:
        """Initialise the Podcast Archiver Health object."""
        from archivepodcast import __version__

        self.core: CoreHealth = CoreHealth()
        self.podcasts: dict[str, PodcastHealth] = {}
        self.templates: dict[str, WebpageHealth] = {}
        self.version: str = __version__

    def get_health(self) -> str:
        """Return the health."""
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def update_template_status(self, webpage: str, **kwargs: bool | str | int) -> None:
        """Update the webpage."""
        if webpage not in self.templates:
            self.templates[webpage] = WebpageHealth()

        for key, value in kwargs.items():
            if value is not None and hasattr(self.templates[webpage], key):
                setattr(self.templates[webpage], key, value)

    def update_podcast_status(self, podcast: str, **kwargs: bool | str | int) -> None:
        """Update the podcast."""
        if podcast not in self.podcasts:
            self.podcasts[podcast] = PodcastHealth()

        for key, value in kwargs.items():
            if value is not None and hasattr(self.podcasts[podcast], key):
                setattr(self.podcasts[podcast], key, value)

    def update_podcast_episode_info(self, podcast: str, tree: etree._ElementTree) -> None:
        """Update the podcast episode info."""
        if podcast not in self.podcasts:
            self.podcasts[podcast] = PodcastHealth()

        self.podcasts[podcast].latest_episode_info = LatestEpisodeInfo(tree)

    def update_core_status(self, **kwargs: bool | str | int) -> None:
        """Update the core."""
        for key, value in kwargs.items():
            if value is not None and hasattr(self.core, key):
                setattr(self.core, key, value)
