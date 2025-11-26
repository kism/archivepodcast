"""Health monitoring for archivepodcast components."""

import contextlib
import datetime
from typing import TYPE_CHECKING, Self

from lxml import etree
from psutil import Process
from pydantic import BaseModel, field_serializer

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

    def update_episode_info(self, tree: etree._ElementTree | etree._Element | None = None) -> None:
        """Update the latest episode info."""
        logger.trace("Updating podcast episode info")
        new_latest_episode: EpisodeInfo = EpisodeInfo()
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
                    new_latest_episode.title = latest_episode.xpath("title")[0].text

                # If we have the description, use it
                with contextlib.suppress(IndexError):
                    new_episode_count = len(tree.xpath("//item"))

                # If we have the pubDate, try to parse it
                if len(latest_episode.xpath("pubDate")) > 0 and latest_episode.xpath("pubDate")[0].text:
                    pod_pubdate = str(latest_episode.xpath("pubDate")[0].text) or "1970-01-01 00:00:00"
                    found_pubdate = False
                    for podcast_date_format in PODCAST_DATE_FORMATS:
                        try:
                            new_latest_episode.pubdate = int(
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


class WebpageHealth(BaseModel):
    """Health status for an individual webpage."""

    last_render: int = int(datetime.datetime.now(tz=datetime.UTC).timestamp())


class Host(BaseModel):
    """Info about a host config entry."""

    host_type: str = ""
    url: str = ""  # Don't use HttpUrl since we arent validating


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


class EventLastTime(BaseModel):
    """Event Last Time Model."""

    duration: datetime.timedelta

    @field_serializer("duration")
    def serialize_duration(self, value: datetime.timedelta) -> float:
        """Serialize duration to total seconds."""
        return value.total_seconds()


class PodcastArchiverHealthAPI(BaseModel):
    """Podcast Archiver Health API Model."""

    core: CoreHealth
    podcasts: dict[str, PodcastHealth]
    templates: dict[str, WebpageHealth]
    version: str
    event_times: dict[str, EventLastTime]
    assets: dict[str, str]
    host_info: HostingInfo


class PodcastArchiverHealth:
    """Overall health monitoring for PodcastArchiver."""

    def __init__(self) -> None:
        """Initialise the Podcast Archiver Health object."""
        self._core: CoreHealth = CoreHealth()
        self._podcasts: dict[str, PodcastHealth] = {}
        self._templates: dict[str, WebpageHealth] = {}
        self._event_times: dict[str, EventLastTime] = {}
        self._assets: dict[str, str] = {}
        self._version: str = __version__
        self._host_info: HostingInfo = HostingInfo()

    def get_health(self, ap: PodcastArchiver) -> PodcastArchiverHealthAPI:
        """Return the health."""
        if PROCESS is not None:
            self._core.memory_mb = PROCESS.memory_info().rss / (1024 * 1024)
        self._assets = ap.webpages.get_list()

        return PodcastArchiverHealthAPI(
            core=self._core,
            podcasts=self._podcasts,
            templates=self._templates,
            event_times=self._event_times,
            assets=self._assets,
            version=self._version,
            host_info=self._host_info,
        )

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

    def update_podcast_episode_info(self, podcast: str, tree: etree._ElementTree | etree._Element) -> None:
        """Update the podcast episode info."""
        logger.trace("Updating podcast episode info for %s", podcast)
        if podcast not in self._podcasts:
            self._podcasts[podcast] = PodcastHealth()

        self._podcasts[podcast].update_episode_info(tree)

    def update_core_status(self, **kwargs: bool | str | int | None) -> None:
        """Update the core."""
        valid_attrs = self._core.model_dump().keys()
        for key, value in kwargs.items():
            if value is not None and key in valid_attrs:
                setattr(self._core, key, value)

    def set_event_time(self, event: str, duration: datetime.timedelta | float) -> None:
        """Set the event last time."""
        if isinstance(duration, int):
            duration = 999999999.0  # Always use float for durations

        if isinstance(duration, float):
            duration = datetime.timedelta(seconds=duration)

        self._event_times[event] = EventLastTime(duration=duration)

    def currently_rendering(
        self,
    ) -> bool:
        """Set currently rendering status."""
        return self._core.currently_rendering

    def currently_loading_config(
        self,
    ) -> bool:
        """Set currently loading config status."""
        return self._core.currently_loading_config

    def set_host_info(self, app_config: AppConfig) -> None:
        """Set the hosting info from AppConfig."""
        self._host_info = HostingInfo.load_from_config(app_config)
