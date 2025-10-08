"""Health monitoring for archivepodcast components."""

import contextlib
import datetime
import json
from typing import TYPE_CHECKING

from lxml import etree

from .ap_constants import PODCAST_DATE_FORMATS, PROCESS
from .logger import get_logger
from .version import __version__

if TYPE_CHECKING:
    from .ap_archiver import PodcastArchiver  # pragma: no cover
else:
    PodcastArchiver = object

logger = get_logger(__name__)


class PodcastHealth:
    """Health status for an individual podcast."""

    @staticmethod
    def _get_latest_episode_default() -> dict[str, str]:
        return {"title": "Unknown", "pubdate": "Unknown"}

    def __init__(self) -> None:
        """Initialise the Podcast Health object."""
        self.rss_available: bool = False
        self.rss_fetching_live: bool = False
        self.last_fetched: int = 0
        self.healthy_download: bool | None = None
        self.healthy_feed: bool = False
        self.update_episode_info()

    def update_episode_info(self, tree: etree._ElementTree | None = None) -> None:
        """Update the latest episode info."""
        logger.trace("Updating podcast episode info")
        new_latest_episode: dict = self._get_latest_episode_default()
        new_episode_count: int = 0

        try:
            if tree is not None:
                if len(tree.xpath("//item")) == 0:
                    logger.warning("No episodes found in feed")
                    self.latest_episode = new_latest_episode
                    self.episode_count = new_episode_count
                    return

                latest_episode = tree.xpath("//item")[0]

                # If we have the title, use it
                with contextlib.suppress(IndexError):
                    new_latest_episode["title"] = latest_episode.xpath("title")[0].text

                # If we have the description, use it
                with contextlib.suppress(IndexError):
                    new_episode_count = len(tree.xpath("//item"))

                # If we have the pubDate, try to parse it
                if len(latest_episode.xpath("pubDate")) > 0 and latest_episode.xpath("pubDate")[0].text:
                    pod_pubdate = latest_episode.xpath("pubDate")[0].text
                    found_pubdate = False
                    for podcast_date_format in PODCAST_DATE_FORMATS:
                        try:
                            new_latest_episode["pubdate"] = int(
                                datetime.datetime.strptime(pod_pubdate, podcast_date_format)
                                .replace(tzinfo=datetime.UTC)
                                .timestamp()
                            )
                            found_pubdate = True
                            break
                        except ValueError:
                            pass
                    if not found_pubdate:
                        logger.error("Unable to parse pubDate: %s", pod_pubdate)
        except Exception:  # pragma: no cover # Just to be safe
            logger.exception("Error parsing podcast episode info")  # pragma: no cover # Just to be safe

        self.latest_episode = new_latest_episode
        self.episode_count = new_episode_count


class WebpageHealth:
    """Health status for an individual webpage."""

    def __init__(self) -> None:
        """Initialise the Webpage Health object."""
        self.last_rendered: int = 0


class CoreHealth:
    """Core application health status."""

    def __init__(self) -> None:
        """Initialise the Core Health object."""
        self.alive: bool = True
        self.last_run: int = 0
        self.about_page_exists: bool = False
        self.last_startup: int = int(datetime.datetime.now(tz=datetime.UTC).timestamp())
        self.currently_rendering: bool = False
        self.currently_loading_config: bool = False
        self.memory_mb: float = -0.0
        self.debug: bool = False


class PodcastArchiverHealth:
    """Overall health monitoring for PodcastArchiver."""

    def __init__(self) -> None:
        """Initialise the Podcast Archiver Health object."""
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
        logger.trace("Updating podcast health for %s: %s", podcast, kwargs)
        if podcast not in self.podcasts:
            self.podcasts[podcast] = PodcastHealth()

        for key, value in kwargs.items():
            if value is not None and hasattr(self.podcasts[podcast], key):
                setattr(self.podcasts[podcast], key, value)

    def update_podcast_episode_info(self, podcast: str, tree: etree._ElementTree) -> None:
        """Update the podcast episode info."""
        logger.trace("Updating podcast episode info for %s", podcast)
        if podcast not in self.podcasts:
            self.podcasts[podcast] = PodcastHealth()

        self.podcasts[podcast].update_episode_info(tree)

    def update_core_status(self, **kwargs: bool | str | int) -> None:
        """Update the core."""
        for key, value in kwargs.items():
            if value is not None and hasattr(self.core, key):
                setattr(self.core, key, value)
