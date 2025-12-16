"""Health monitoring for archivepodcast components."""

import datetime
from typing import TYPE_CHECKING, Self

from psutil import Process
from pydantic import BaseModel

from archivepodcast.archiver.rss_models import RssFeed
from archivepodcast.utils.logger import get_logger
from archivepodcast.version import __version__

if TYPE_CHECKING:
    from archivepodcast.archiver import PodcastArchiver  # pragma: no cover
    from archivepodcast.config import AppConfig  # pragma: no cover
else:
    PodcastArchiver = object
    AppConfig = object

logger = get_logger(__name__)

PODCAST_DATE_FORMATS = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"]


PROCESS = Process()


class EpisodeInfo(BaseModel):
    """Episode Info Model."""

    title: str = "Unknown"
    pubdate: int = 0


class PodcastHealth(BaseModel):
    """Health status for an individual podcast."""

    latest_episode: EpisodeInfo = EpisodeInfo()
    rss_available: bool = False
    rss_fetching_live: bool = False
    last_fetched: int = 0
    healthy_download: bool | None = None
    healthy_feed: bool = False
    episode_count: int = 0

    def update_episode_info(self, feed: RssFeed | None = None) -> None:
        """Update the latest episode info from RssFeed model."""
        logger.trace("Updating podcast episode info")
        new_latest_episode: EpisodeInfo = EpisodeInfo()
        new_episode_count: int = 0

        try:
            if feed is not None and isinstance(feed, RssFeed):
                if feed.rss and feed.rss.channel and feed.rss.channel.items:
                    items = feed.rss.channel.items
                    new_episode_count = len(items)

                    if new_episode_count > 0:
                        latest = items[0]
                        if latest.title:
                            new_latest_episode.title = latest.title
                        # Note: EpisodeInfo doesn't have description or pub_date attributes
                        # Only title and pubdate (int timestamp) are supported
                else:
                    logger.warning("RssFeed has no episodes")

        except Exception:  # pragma: no cover # Just to be safe
            logger.exception("Error parsing podcast episode info")  # pragma: no cover # Just to be safe

        self.latest_episode = new_latest_episode
        self.episode_count = new_episode_count


class WebpageHealth(BaseModel):
    """Health status for an individual webpage."""

    last_render: int = int(datetime.datetime.now(tz=datetime.UTC).timestamp())


class Host(BaseModel):
    """Info about a host config entry."""

    host_type: str = ""
    url: str = ""  # Don't use HttpUrl since we aren't validating


class HostingInfo(BaseModel):
    """Info about how the site is hosted."""

    backend: Host = Host()
    frontend: Host = Host()

    @classmethod
    def load_from_config(cls, app_config: AppConfig) -> Self:
        """Load HostType from AppConfig."""
        frontend_host_type = "Flask"
        if app_config.storage_backend == "s3" and app_config.inet_path == app_config.s3.cdn_domain:
            frontend_host_type = "s3"

        backend_host_type = "s3"
        if app_config.storage_backend == "local":
            backend_host_type = "Flask"

        backend = Host(
            host_type=backend_host_type,
            url=app_config.s3.cdn_domain.encoded_string(),
        )
        frontend = Host(
            host_type=frontend_host_type,
            url=app_config.inet_path.encoded_string(),
        )
        return cls(backend=backend, frontend=frontend)


class CoreHealth(BaseModel):
    """Core application health status."""

    alive: bool = True
    last_run: int = 0
    about_page_exists: bool = False
    last_startup: int = int(datetime.datetime.now(tz=datetime.UTC).timestamp())
    currently_rendering: bool = False
    currently_loading_config: bool = False
    memory_mb: float = -0.0
    debug: bool = False


class PodcastArchiverHealthAPI(BaseModel):
    """Podcast Archiver Health API Model."""

    core: CoreHealth
    podcasts: dict[str, PodcastHealth]
    templates: dict[str, WebpageHealth]
    version: str
    assets: dict[str, str]
    host_info: HostingInfo


class PodcastArchiverHealth:
    """Overall health monitoring for PodcastArchiver."""

    def __init__(self) -> None:
        """Initialise the Podcast Archiver Health object."""
        self._core: CoreHealth = CoreHealth()
        self._podcasts: dict[str, PodcastHealth] = {}
        self._templates: dict[str, WebpageHealth] = {}
        self._assets: dict[str, str] = {}
        self._version: str = __version__
        self._host_info: HostingInfo = HostingInfo()

    def get_health(self) -> PodcastArchiverHealthAPI:
        """Return the health."""
        if PROCESS is not None:
            self._core.memory_mb = PROCESS.memory_info().rss / (1024 * 1024)

        return PodcastArchiverHealthAPI(
            core=self._core,
            podcasts=self._podcasts,
            templates=self._templates,
            assets=self._assets,
            version=self._version,
            host_info=self._host_info,
        )

    def set_asset(self, path: str, mime: str) -> None:
        """Set an asset."""
        self._assets[path] = mime

    def update_template_status(self, webpage: str, **kwargs: bool | str | int | None) -> None:
        """Update the webpage."""
        if webpage not in self._templates:
            self._templates[webpage] = WebpageHealth()

        for key, value in kwargs.items():
            if value is not None and hasattr(self._templates[webpage], key):
                setattr(self._templates[webpage], key, value)

    def update_podcast_status(self, podcast: str, **kwargs: bool | str | int | None) -> None:
        """Update the podcast."""
        logger.trace("Updating podcast health for %s: %s", podcast, kwargs)
        if podcast not in self._podcasts:
            self._podcasts[podcast] = PodcastHealth()

        for key, value in kwargs.items():
            if value is not None and hasattr(self._podcasts[podcast], key):
                setattr(self._podcasts[podcast], key, value)

    def update_podcast_episode_info(self, podcast: str, feed: RssFeed | None = None) -> None:
        """Update the podcast episode info from RssFeed model."""
        logger.trace("Updating podcast episode info for %s", podcast)
        if podcast not in self._podcasts:
            self._podcasts[podcast] = PodcastHealth()

        self._podcasts[podcast].update_episode_info(feed)

    def update_core_status(self, **kwargs: bool | str | int | None) -> None:
        """Update the core."""
        valid_attrs = self._core.model_dump().keys()
        for key, value in kwargs.items():
            if value is not None and key in valid_attrs:
                setattr(self._core, key, value)

    def currently_rendering(
        self,
    ) -> bool:
        """Return the currently rendering status."""
        return self._core.currently_rendering

    def currently_loading_config(
        self,
    ) -> bool:
        """Return the currently loading config status."""
        return self._core.currently_loading_config

    def set_host_info(self, app_config: AppConfig) -> None:
        """Set the hosting info from AppConfig."""
        self._host_info = HostingInfo.load_from_config(app_config)
