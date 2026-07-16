"""Module to handle the ArchivePodcast object."""

import asyncio
import contextlib
import datetime
import time
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import aiohttp
from pydantic import BaseModel

from archivepodcast.constants import XML_ENCODING
from archivepodcast.downloader import PodcastsDownloader
from archivepodcast.downloader.constants import USER_AGENT
from archivepodcast.downloader.helpers import tree_no_episodes
from archivepodcast.instances.health import health
from archivepodcast.instances.path_cache import local_file_cache, s3_file_cache
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.instances.profiler import event_times
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.s3 import s3_get, s3_put

from .webpage_renderer import WebpageRenderer

if TYPE_CHECKING:
    from archivepodcast.config import AppConfig, PodcastConfig  # pragma: no cover
else:
    AppConfig = object
    PodcastConfig = object

logger = get_logger(__name__)


def _load_cached_feed(podcast: PodcastConfig, previous_feed: bytes) -> ET.ElementTree[ET.Element] | None:
    """Load feed from cache when live download is not available."""
    if previous_feed == b"":
        logger.warning(
            "[%s] Cannot find local rss feed file to serve unavailable podcast",
            podcast.name_one_word,
        )
        return None

    try:
        root = ET.fromstring(previous_feed)
        tree: ET.ElementTree[ET.Element] = ET.ElementTree(root)
    except ET.ParseError:
        logger.error("[%s] Syntax error in rss feed file", podcast.name_one_word)  # noqa: TRY400
        return None

    if tree_no_episodes(tree):
        logger.error("[%s] Local/cached rss feed has no episodes", podcast.name_one_word)
        return None
    logger.debug("[%s] Loaded rss from file", podcast.name_one_word)

    return tree


class APFileList(BaseModel):
    """Podcast file list response model."""

    base_url: str
    files: list[str]


_aiohttp_session: aiohttp.ClientSession | None = None


def _get_aiohttp_session() -> aiohttp.ClientSession:
    """Get or create the aiohttp ClientSession."""
    global _aiohttp_session  # noqa: PLW0603
    if _aiohttp_session is None or _aiohttp_session.closed:
        _aiohttp_session = aiohttp.ClientSession(
            # timeout, 5 minutes, why not
            timeout=aiohttp.ClientTimeout(),
            # tcp connector, 100 is default connection limit, force_close seems to fix some issues
            connector=aiohttp.TCPConnector(),
            raise_for_status=True,
            headers={"User-Agent": USER_AGENT},
        )
    return _aiohttp_session


async def _close_aiohttp_session() -> None:
    """Close the aiohttp ClientSession."""
    if _aiohttp_session is not None and not _aiohttp_session.closed:
        await _aiohttp_session.close()


class PodcastArchiver:
    """Main podcast archiving system that coordinates downloading, storage and serving of podcasts."""

    # region Init
    def __init__(
        self,
        app_config: AppConfig,
        podcast_list: list[PodcastConfig],
        *,
        debug: bool = False,
    ) -> None:
        """Initialise the ArchivePodcast object."""
        self.debug = debug

        # Health object
        health.update_core_status(currently_loading_config=True)
        health.set_host_info(app_config)

        self.s3: bool = app_config.storage_backend == "s3"
        self.renderer = WebpageRenderer(app_config=app_config, podcast_list=podcast_list, s3=self.s3, debug=debug)

        # Set the config and podcast list
        self._app_config: AppConfig = app_config
        self.podcast_list: list[PodcastConfig] = podcast_list
        self.podcast_rss: dict[str, bytes] = {}

        self.load_config(app_config, podcast_list)

        # Done, update health
        health.update_core_status(currently_loading_config=False)

    def load_config(self, app_config: AppConfig, podcast_list: list[PodcastConfig]) -> None:
        """Load the config from the config file."""
        self._app_config = app_config
        self.podcast_list = podcast_list
        self._make_folder_structure()

    # region Getters
    def get_rss_feed(self, feed: str) -> bytes:
        """Return the rss file for a given feed."""
        return self.podcast_rss[feed]

    # region Grab

    def grab_podcasts(self) -> None:
        """Download and process all configured podcasts, updating health metrics and file listings."""
        grab_podcasts_start_time = time.time()
        health.update_core_status(last_run=int(grab_podcasts_start_time))
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)

        # If you want to see whats going on in the event loop, uncomment this and indent until close()
        # When the program is running use the commands
        # $ python -m aiomonitor.cli
        # > ps
        # st <task id>

        # import aiomonitor  # noqa: ERA001
        # with aiomonitor.start_monitor(event_loop):
        # Part 1: Update the file cache to know what files we have already downloaded
        event_loop.run_until_complete(self.update_file_cache())
        event_times.set_event_time("grab_podcasts/Update file cache", time.time() - grab_podcasts_start_time)

        # Part 2: Download and process all podcasts
        # Event Loop
        podcast_start_time = time.time()

        # Create Task List
        podcast_tasks = []
        for podcast in self.podcast_list:
            task = self._grab_podcast_with_metrics(podcast)
            podcast_tasks.append(task)

        podcast_tasks.append(self.renderer.render_files())

        # Run Tasks
        event_loop.run_until_complete(asyncio.gather(*podcast_tasks))
        event_times.set_event_time("grab_podcasts/Scrape", time.time() - podcast_start_time)

        # Part 3: Render files and cleanup
        # Event Loop
        cleanup_start_time = time.time()

        ap_file_list = event_loop.run_until_complete(self.get_file_list())

        # Create Task List
        cleanup_tasks = [self.renderer.render_filelist_html(ap_file_list), _close_aiohttp_session()]

        # Run Tasks
        event_loop.run_until_complete(asyncio.gather(*cleanup_tasks))
        event_loop.close()
        event_times.set_event_time("grab_podcasts/Post Scrape", time.time() - cleanup_start_time)

        # Final timing
        total_duration = time.time() - grab_podcasts_start_time
        event_times.set_event_time("grab_podcasts", total_duration)

    async def _grab_podcast_with_metrics(self, podcast: PodcastConfig) -> None:
        """Wrapper to handle metrics and error handling for individual podcast processing."""
        logger.trace("Starting _grab_podcast_with_metrics for podcast: %s", podcast.name_one_word)
        podcast_grab_start_time = time.time()

        aiohttp_session = _get_aiohttp_session()

        try:
            await self._grab_podcast(podcast, aiohttp_session=aiohttp_session)
        except Exception:
            logger.exception("Error grabbing podcast: %s", podcast.name_one_word)
            health.update_podcast_status(podcast.name_one_word, healthy_feed=False)

        elapsed_time = time.time() - podcast_grab_start_time
        event_times.set_event_time(f"grab_podcasts/Scrape/{podcast.name_one_word}", elapsed_time)
        logger.trace("Exiting _grab_podcast_with_metrics for podcast: %s", podcast.name_one_word)

    async def _grab_podcast(self, podcast: PodcastConfig, aiohttp_session: aiohttp.ClientSession) -> None:
        """Function to download a podcast and store the rss."""
        if podcast.name_one_word == "":  # This is actually the place for this check
            logger.error("Podcast has no name_one_word set in config, cannot proceed")
            return

        logger.info("[%s] Processing podcast to archive: %s", podcast.name_one_word, podcast.new_name)

        previous_feed = await self._get_previous_feed(podcast)
        tree = await self._download_live_podcast(podcast, aiohttp_session) if podcast.live else None

        if not podcast.live:
            logger.info(
                '[%s] "live": false, in config, not fetching new episodes, will load feed from disk',
                podcast.name_one_word,
            )
            health.update_podcast_status(podcast.name_one_word, rss_fetching_live=False)

        # If we did download the feed, but it has no episodes, discard it
        if tree_no_episodes(tree):
            tree = None

        # Only compare a genuinely downloaded feed against what is currently being served
        if tree is not None and previous_feed:
            await self._backup_previous_feed(podcast, tree, previous_feed)

        # Load from cache if no tree available
        if tree is None:
            tree = _load_cached_feed(podcast, previous_feed)

        await self._process_podcast_tree(podcast, tree, previous_feed)
        logger.trace("Exiting _grab_podcast for %s", podcast.name_one_word)

    # region _grab helpers
    async def _get_previous_feed(self, podcast: PodcastConfig) -> bytes:
        """Get the previous feed from cache, file, or s3."""
        try:
            return self.podcast_rss[podcast.name_one_word]
        except KeyError:
            rss_file_path = get_app_paths().web_root / "rss" / podcast.name_one_word
            if rss_file_path.is_file():
                with contextlib.suppress(Exception):
                    return rss_file_path.read_bytes()
            if self.s3:  # Fresh container (lambda) won't have the feed on disk, but it will be in s3
                previous_feed = await s3_get(self._app_config.s3.bucket, "rss/" + podcast.name_one_word)
                if previous_feed:
                    logger.debug("[%s] Loaded previous feed from s3", podcast.name_one_word)
                return previous_feed
            return b""

    async def _backup_previous_feed(
        self, podcast: PodcastConfig, tree: ET.ElementTree[ET.Element], previous_feed: bytes
    ) -> None:
        """Back up the served feed if the freshly downloaded one has fewer episodes."""
        try:
            previous_count = len(ET.fromstring(previous_feed).findall(".//item"))
        except ET.ParseError:
            return
        new_count = len(tree.findall(".//item"))
        if new_count >= previous_count:
            return

        date = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d")
        backup_filename = f"{date}-rss-backup.xml"
        backup_path = get_app_paths().web_root / "content" / podcast.name_one_word / backup_filename
        logger.warning(
            "[%s] Downloaded feed has %s episodes, previously %s, backing up previous feed to %s",
            podcast.name_one_word,
            new_count,
            previous_count,
            backup_path,
        )
        if not backup_path.exists():  # keep the earliest (fullest) backup for the day
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_bytes(previous_feed)

        if self.s3:
            try:
                await s3_put(
                    self._app_config.s3.bucket,
                    f"content/{podcast.name_one_word}/{backup_filename}",
                    previous_feed,
                    "application/rss+xml",
                )
            except Exception:
                logger.exception("Unhandled s3 error trying to upload the file: %s", backup_filename)

    async def _download_live_podcast(
        self, podcast: PodcastConfig, aiohttp_session: aiohttp.ClientSession
    ) -> ET.ElementTree[ET.Element] | None:
        """Download live podcast and update health status."""
        podcasts_downloader = PodcastsDownloader(
            podcast=podcast,
            app_config=self._app_config,
            s3=self.s3,
            aiohttp_session=aiohttp_session,
        )

        tree = await podcasts_downloader.download_podcast()
        if tree:
            last_fetched = int(time.time())
            health.update_podcast_status(podcast.name_one_word, rss_fetching_live=True, last_fetched=last_fetched)
        else:
            logger.error("Unable to download podcast: %s", podcast.name_one_word)

        return tree

    async def _process_podcast_tree(
        self, podcast: PodcastConfig, tree: ET.ElementTree[ET.Element] | None, previous_feed: bytes
    ) -> None:
        """Process the podcast tree and update RSS feed or handle errors."""
        if tree is not None:
            await self._update_rss_feed(podcast, tree, previous_feed)
            health.update_podcast_episode_info(podcast.name_one_word, tree)
        else:
            logger.error("Unable to host podcast: %s, something is wrong", podcast.name_one_word)
            health.update_podcast_status(podcast.name_one_word, rss_available=False)

    # region RSS Feed Handling
    async def _update_rss_feed(
        self,
        podcast: PodcastConfig,
        tree: ET.ElementTree[ET.Element],
        previous_feed: bytes,
    ) -> None:
        """Update the rss feed, in memory and s3."""
        self.podcast_rss.update(
            {
                podcast.name_one_word: ET.tostring(
                    tree.getroot(),
                    encoding=XML_ENCODING,  # Keep this uppercase for the diff to work
                    method="xml",
                    xml_declaration=True,
                )
            }
        )

        # Check the length of the feed in s3
        local_changes_to_feed = self.podcast_rss[podcast.name_one_word] != previous_feed
        need_to_upload_to_s3 = False
        if self.s3:
            logger.trace("S3 Check upload")
            # So this only checks the size,
            # the generated time of rss feeds shouldn't affect the size due to how the time is formatted
            # see <pubDate> or <lastBuildDate> in an rss feed that has it
            if not s3_file_cache.check_file_exists(
                key="rss/" + podcast.name_one_word,
                size=len(self.podcast_rss[podcast.name_one_word]),
            ):
                need_to_upload_to_s3 = True

        # Upload to s3 if we are in s3 mode
        if need_to_upload_to_s3:
            try:
                logger.trace("Uploading feed %s to s3...", podcast.name_one_word)
                await s3_put(
                    self._app_config.s3.bucket,
                    "rss/" + podcast.name_one_word,
                    self.podcast_rss[podcast.name_one_word],
                    "application/rss+xml",
                )
                logger.debug("[%s] Uploaded feed to s3", podcast.name_one_word)
            except Exception:
                logger.exception("Unhandled s3 error trying to upload the file: %s", podcast.name_one_word)

        msg = "no feed changes"
        if not self.s3 and local_changes_to_feed:
            msg = "feed changed"
        elif self.s3 and need_to_upload_to_s3:
            msg = "feed uploaded to s3"

        logger.info(
            "[%s] (%s) Hosted feed: %srss/%s",
            podcast.name_one_word,
            msg,
            self._app_config.inet_path,
            podcast.name_one_word,
        )

        health.update_podcast_status(podcast.name_one_word, rss_available=True)
        logger.trace("Exiting _update_rss_feed")

    # region Housekeeping
    def _make_folder_structure(self) -> None:
        """Ensure that web_root folder structure exists."""
        logger.debug("Checking folder structure")

        app_paths = get_app_paths()

        folders = [
            app_paths.instance_path,
            app_paths.web_root,
            app_paths.web_root / "rss",
            app_paths.web_root / "content",
        ]

        folders.extend(app_paths.web_root / "content" / entry.name_one_word for entry in self.podcast_list)
        for folder in folders:
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except PermissionError as exc:
                err = (
                    f"You do not have permission to create folder: {folder}. "
                    "Run this script as a different user probably, or check permissions of the web_root."
                )
                logger.exception(err)
                raise PermissionError(err) from exc

    # endregion

    # Region File Cache and File List
    async def update_file_cache(self) -> None:
        """Update the file cache."""
        if self.s3:
            await s3_file_cache.get_all(self._app_config.s3.bucket)
        else:
            local_file_cache.refresh(get_app_paths().web_root)

    async def get_file_list(self) -> APFileList:
        """Gets the base url and the file cache."""
        await self.update_file_cache()

        base_url = self._app_config.s3.cdn_domain if self.s3 else self._app_config.inet_path

        file_list = (
            [s3_file["Key"] for s3_file in await s3_file_cache.get_all(self._app_config.s3.bucket)]
            if self.s3
            else [str(path) for path in local_file_cache.get_all()]
        )

        return APFileList(base_url=base_url.encoded_string(), files=file_list)

    # region Rendering

    async def write_health_s3(self) -> None:
        """Write the health api to s3."""
        health_api_response = health.get_health()
        await self.renderer.write_health_s3(health_api_response)

    # endregion
