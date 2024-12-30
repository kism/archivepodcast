"""Archivepodcast health module."""

import contextlib
import datetime
import json
from typing import TYPE_CHECKING

import psutil
from lxml import etree

from .logger import get_logger

if TYPE_CHECKING:
    from .ap_archiver import PodcastArchiver # pragma: no cover
else:
    PodcastArchiver = object

logger = get_logger(__name__)

PODCAST_DATE_FORMATS = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"]

PROCESS = psutil.Process()


class PodcastHealth:
    """Podcast Health object."""

    def __init__(self) -> None:
        """Initialise the Podcast Health object."""
        self.rss_available: bool = False
        self.rss_fetching_live: bool = False
        self.last_fetched: int = 0
        self.healthy: bool = False
        self.update_episode_info()

    def update_episode_info(self, tree: etree._ElementTree | None = None) -> None:
        """Update the latest episode info."""
        self.latest_episode: dict = {"title": "Unknown", "pubdate": "Unknown"}
        self.episode_count: int = 0

        try:
            if tree is not None:
                latest_episode = tree.xpath("//item")[0]

                with contextlib.suppress(IndexError):
                    self.latest_episode["title"] = latest_episode.xpath("title")[0].text

                with contextlib.suppress(IndexError):
                    self.episode_count = len(tree.xpath("//item"))

                pod_pubdate = latest_episode.xpath("pubDate")[0].text
                found_pubdate = False
                for podcast_date_format in PODCAST_DATE_FORMATS:
                    try:
                        self.latest_episode["pubdate"] = int(
                            datetime.datetime.strptime(pod_pubdate, podcast_date_format).timestamp()
                        )
                        found_pubdate = True
                        break
                    except ValueError:
                        pass
                if not found_pubdate:
                    logger.error("Unable to parse pubDate: %s", pod_pubdate)
        except Exception:
            logger.exception("Error parsing podcast episode info")


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
        self.currently_rendering: bool = False
        self.currently_loading_config: bool = False
        self.memory_mb: float = -0.0
        self.debug: bool = False


class PodcastArchiverHealth:
    """Podcast Archiver Health object."""

    def __init__(self) -> None:
        """Initialise the Podcast Archiver Health object."""
        from archivepodcast import __version__

        self.core: CoreHealth = CoreHealth()
        self.podcasts: dict[str, PodcastHealth] = {}
        self.templates: dict[str, WebpageHealth] = {}
        self.version: str = __version__
        self.assets: dict[str, str] = {}

    def get_health(self, ap: PodcastArchiver) -> str:
        """Return the health."""
        self.core.memory_mb = PROCESS.memory_info().rss / (1024 * 1024)
        self.assets = ap.webpages.get_list()
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

        self.podcasts[podcast].update_episode_info(tree)

    def update_core_status(self, **kwargs: bool | str | int) -> None:
        """Update the core."""
        for key, value in kwargs.items():
            if value is not None and hasattr(self.core, key):
                setattr(self.core, key, value)
