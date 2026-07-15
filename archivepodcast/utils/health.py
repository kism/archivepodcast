"""Health monitoring for archivepodcast components."""

import contextlib
import datetime
import os
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel

from archivepodcast.constants import PROGRAM_VERSION
from archivepodcast.utils.logger import get_logger

if TYPE_CHECKING:
    import xml.etree.ElementTree as ET

    from archivepodcast.archiver import PodcastArchiver  # pragma: no cover
    from archivepodcast.config import AppConfig  # pragma: no cover
else:
    PodcastArchiver = object
    AppConfig = object

logger = get_logger(__name__)


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

    def update_episode_info(self, tree: ET.ElementTree[ET.Element] | ET.Element | None = None) -> None:
        """Update the latest episode info."""
        logger.trace("Updating podcast episode info")
        new_latest_episode: EpisodeInfo = EpisodeInfo()
        new_episode_count: int = 0

        try:
            new_latest_episode, new_episode_count = self._parse_episode_info(tree)
        except Exception:  # pragma: no cover # Just to be safe
            logger.exception("Error parsing podcast episode info")  # pragma: no cover # Just to be safe

        self.latest_episode = new_latest_episode
        self.episode_count = new_episode_count

    @staticmethod
    def _parse_episode_info(tree: ET.ElementTree[ET.Element] | ET.Element | None) -> tuple[EpisodeInfo, int]:
        """Parse the latest episode info and episode count from a feed tree."""
        new_latest_episode: EpisodeInfo = EpisodeInfo()
        new_episode_count: int = 0

        if tree is None:
            return new_latest_episode, new_episode_count

        items = tree.findall(".//item")
        if len(items) == 0:
            logger.warning("No episodes found in feed")
            return new_latest_episode, new_episode_count

        latest_episode = items[0]
        new_episode_count = len(items)

        # If we have the title, use it
        title = latest_episode.findtext("title")
        if title is not None:
            new_latest_episode.title = title

        # If we have the pubDate, try to parse it
        if latest_episode.findtext("pubDate"):
            pod_pubdate = str(latest_episode.findtext("pubDate"))
            try:
                parsed_pubdate = parsedate_to_datetime(pod_pubdate)
                if parsed_pubdate.tzinfo is None:
                    parsed_pubdate = parsed_pubdate.replace(tzinfo=datetime.UTC)
                new_latest_episode.pubdate = int(parsed_pubdate.timestamp())
            except ValueError:
                logger.error("Unable to parse pubDate: %s", pod_pubdate)  # noqa: TRY400 # No need for a traceback

        return new_latest_episode, new_episode_count


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
        frontend_host_type = "FastAPI"
        if app_config.storage_backend == "s3" and app_config.inet_path == app_config.s3.cdn_domain:
            frontend_host_type = "s3"

        backend_host_type = "s3"
        if app_config.storage_backend == "local":
            backend_host_type = "FastAPI"

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
        self._version: str = PROGRAM_VERSION
        self._host_info: HostingInfo = HostingInfo()

    def get_health(self) -> PodcastArchiverHealthAPI:
        """Return the health."""
        # ponytail: linux-only /proc read, bring back psutil if this ever needs windows/macos
        with contextlib.suppress(OSError):
            resident_pages = int(Path("/proc/self/statm").read_text(encoding="utf-8").split()[1])
            self._core.memory_mb = resident_pages * os.sysconf("SC_PAGESIZE") / (1024 * 1024)

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

    def update_podcast_episode_info(self, podcast: str, tree: ET.ElementTree[ET.Element] | ET.Element) -> None:
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

    def set_host_info(self, app_config: AppConfig) -> None:
        """Set the hosting info from AppConfig."""
        self._host_info = HostingInfo.load_from_config(app_config)
