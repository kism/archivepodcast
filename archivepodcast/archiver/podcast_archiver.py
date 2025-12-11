"""Module to handle the ArchivePodcast object."""

import asyncio
import contextlib
import time
from typing import TYPE_CHECKING

import aiohttp
from aiobotocore.session import get_session
from lxml import etree
from pydantic import BaseModel

from archivepodcast.constants import XML_ENCODING
from archivepodcast.downloader import PodcastsDownloader
from archivepodcast.downloader.constants import USER_AGENT
from archivepodcast.instances.config import get_ap_config_s3_client
from archivepodcast.instances.health import health
from archivepodcast.instances.path_cache import local_file_cache, s3_file_cache
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.instances.profiler import event_times
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.rss import tree_no_episodes
from archivepodcast.utils.time import warn_if_too_long

from .webpage_renderer import WebpageRenderer

if TYPE_CHECKING:
    from archivepodcast.config import AppConfig, PodcastConfig  # pragma: no cover
else:
    AppConfig = object
    PodcastConfig = object

logger = get_logger(__name__)


class APFileList(BaseModel):
    """Podcast file list response model."""

    base_url: str
    files: list[str]


class AIOHttpClientSessionHelper:
    """Helper class to manage a single aiohttp ClientSession."""

    session: aiohttp.ClientSession | None = None

    def get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp ClientSession."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                # timeout, 5 minutes, why not
                timeout=aiohttp.ClientTimeout(),
                # tcp connector, 100 is default connection limit, force_close seems to fix some issues
                connector=aiohttp.TCPConnector(),
                raise_for_status=True,
                headers={"User-Agent": USER_AGENT},
            )
        return self.session

    async def close_session(self) -> None:
        """Close the aiohttp ClientSession."""
        if self.session is not None and not self.session.closed:
            await self.session.close()


aiohttp_client_helper = AIOHttpClientSessionHelper()


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

    # endregion

    def get_rss_feed(self, feed: str) -> bytes:
        """Return the rss file for a given feed."""
        return self.podcast_rss[feed]

    # region Archive

    def grab_podcasts(self) -> None:
        """Download and process all configured podcasts.

        Updates health metrics and regenerates file listings after processing.
        """
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
        ## Event Loop
        podcast_start_time = time.time()

        ## Create Task List
        podcast_tasks = []
        for podcast in self.podcast_list:
            task = self._grab_podcast_with_metrics(podcast)
            podcast_tasks.append(task)

        podcast_tasks.append(self.renderer.render_files())

        ## Run Tasks
        event_loop.run_until_complete(asyncio.gather(*podcast_tasks))
        event_times.set_event_time("grab_podcasts/Scrape", time.time() - podcast_start_time)

        # Part 3: Render files and cleanup
        ## Event Loop
        cleanup_start_time = time.time()

        ap_file_list = event_loop.run_until_complete(self.get_file_list())

        ## Create Task List
        cleanup_tasks = []
        cleanup_tasks.append(self.renderer.render_filelist_html(ap_file_list))
        cleanup_tasks.append(aiohttp_client_helper.close_session())

        ## Run Tasks
        event_loop.run_until_complete(asyncio.gather(*cleanup_tasks))
        event_loop.close()
        event_times.set_event_time("grab_podcasts/Post Scrape", time.time() - cleanup_start_time)

        # Final timing
        total_duration = time.time() - grab_podcasts_start_time
        event_times.set_event_time("grab_podcasts", total_duration)

    async def _grab_podcast_with_metrics(self, podcast: "PodcastConfig") -> None:
        """Wrapper to handle metrics and error handling for individual podcast processing."""
        logger.trace("Starting _grab_podcast_with_metrics for podcast: %s", podcast.name_one_word)
        podcast_grab_start_time = time.time()

        aiohttp_session = aiohttp_client_helper.get_session()

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

        rss_file_path = get_app_paths().web_root / "rss" / podcast.name_one_word

        tree = None
        previous_feed = b""

        podcasts_downloader = PodcastsDownloader(
            podcast=podcast,
            app_config=self._app_config,
            s3=self.s3,
            aiohttp_session=aiohttp_session,
        )
        logger.info("[%s] Processing podcast to archive: %s", podcast.name_one_word, podcast.new_name)

        try:
            previous_feed = self.podcast_rss[podcast.name_one_word]
        except KeyError:  # If nothing in cache, try load from file
            if rss_file_path.is_file():
                with contextlib.suppress(Exception):
                    previous_feed = rss_file_path.read_bytes()

        if podcast.live is True:  # download all the podcasts
            tree = await podcasts_downloader.download_podcast()
            if tree:
                last_fetched = int(time.time())
                health.update_podcast_status(podcast.name_one_word, rss_fetching_live=True, last_fetched=last_fetched)
            else:
                # There should be a previous error message too
                logger.error("Unable to download podcast: %s", podcast.name_one_word)

        else:
            logger.info('[%s] "live": false, in config so not fetching new episodes', podcast.name_one_word)
            health.update_podcast_status(podcast.name_one_word, rss_fetching_live=False)

        if tree is None:  # Serving a podcast that we can't currently download?, load it from file
            with contextlib.suppress(etree.XMLSyntaxError):
                tree = etree.ElementTree(etree.fromstring(previous_feed))

        if tree_no_episodes(tree):  # If there are no episodes, we can't host it
            tree = None

        if tree is not None:
            await self._update_rss_feed(podcast, tree, previous_feed)
            health.update_podcast_episode_info(podcast.name_one_word, tree)
        else:
            logger.error("Unable to host podcast: %s, something is wrong", podcast.name_one_word)
            health.update_podcast_status(podcast.name_one_word, rss_available=False)

        del tree

        logger.trace("Exiting _grab_podcast for %s", podcast.name_one_word)

    # region RSS Feed Handling
    async def _update_rss_feed(
        self,
        podcast: PodcastConfig,
        tree: etree._ElementTree,
        previous_feed: bytes,
    ) -> None:
        """Update the rss feed, in memory and s3."""
        self.podcast_rss.update(
            {
                podcast.name_one_word: etree.tostring(
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
            if not s3_file_cache.check_file_exists(
                key="rss/" + podcast.name_one_word,
                size=len(self.podcast_rss[podcast.name_one_word]),
            ):
                need_to_upload_to_s3 = True

        # Upload to s3 if we are in s3 mode
        if need_to_upload_to_s3:
            session = get_session()
            s3_config = get_ap_config_s3_client()

            async with session.create_client("s3", **s3_config.model_dump()) as s3_client:
                try:
                    # Upload the file
                    start_time = time.time()
                    logger.trace("Uploading feed %s to s3...", podcast.name_one_word)
                    await s3_client.put_object(
                        Body=self.podcast_rss[podcast.name_one_word],
                        Bucket=self._app_config.s3.bucket,
                        Key="rss/" + podcast.name_one_word,
                        ContentType="application/rss+xml",
                    )
                    warn_if_too_long(f"upload feed {podcast.name_one_word} to s3", time.time() - start_time)

                    logger.debug("[%s] Uploaded feed to s3", podcast.name_one_word)
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.exception("Unhandled s3 error trying to upload the file: %s")

        msg = "no feed changes"
        if need_to_upload_to_s3:
            msg = "uploaded to s3"
        elif local_changes_to_feed:
            msg = "feed changed"

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
                    f"You do not have permission to create folder: {folder}"
                    "Run this this script as a different user probably, or check permissions of the web_root."
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
            await s3_file_cache.get_all_list_str(self._app_config.s3.bucket)
            if self.s3
            else local_file_cache.get_all_str()
        )

        return APFileList(base_url=base_url.encoded_string(), files=file_list)

    # region Rendering

    async def write_health_s3(self) -> None:
        """Write the health api to s3."""
        health_api_response = health.get_health()
        await self.renderer.write_health_s3(health_api_response)

    # endregion
