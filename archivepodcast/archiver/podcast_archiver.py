"""Module to handle the ArchivePodcast object."""

import asyncio
import contextlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

import magic
import markdown
from aiobotocore.session import get_session
from jinja2 import Environment, FileSystemLoader
from lxml import etree

from archivepodcast.downloader import PodcastDownloader
from archivepodcast.instances.config import get_ap_config_s3_client
from archivepodcast.instances.health import health
from archivepodcast.instances.path_cache import s3_file_cache
from archivepodcast.instances.profiler import event_times
from archivepodcast.utils.logger import get_logger

from .helpers import tree_no_episodes
from .webpages import Webpage, Webpages

if TYPE_CHECKING:
    from archivepodcast.config import AppConfig, PodcastConfig  # pragma: no cover
else:
    AppConfig = object
    PodcastConfig = object

logger = get_logger(__name__)


class PodcastArchiver:
    """Main podcast archiving system that coordinates downloading, storage and serving of podcasts."""

    # region Init
    def __init__(
        self,
        app_config: AppConfig,
        podcast_list: list[PodcastConfig],
        instance_path: Path,
        root_path: Path,
        *,
        debug: bool = False,
    ) -> None:
        """Initialise the ArchivePodcast object."""
        self.debug = debug

        # Health object
        health.update_core_status(currently_loading_config=True)
        health.set_host_info(app_config)

        # There are so many, but I use them all
        self.root_path = Path(root_path)
        self.instance_path = Path(instance_path)
        self.web_root: Path = self.instance_path / "web"  # This gets used so often, it's worth the variable
        self.app_directory = Path("archivepodcast")
        self.static_directory = self.app_directory / "static"
        self.template_directory = self.app_directory / "templates"

        # Set the config and podcast list
        self.app_config: AppConfig = app_config
        self.podcast_list: list[PodcastConfig] = podcast_list
        self.podcast_rss: dict[str, bytes] = {}
        self.webpages: Webpages = Webpages()
        self.s3: bool = app_config.storage_backend == "s3"
        if self.s3:
            logger.info("⛅ Using s3 as storage backend, bucket: %s", app_config.s3.bucket)
        self.about_page_exists = False
        self.load_config(app_config, podcast_list)

        # Done, update health
        health.update_core_status(currently_loading_config=False)

    def load_config(self, app_config: AppConfig, podcast_list: list[PodcastConfig]) -> None:
        """Load the config from the config file."""
        self.app_config = app_config
        self.podcast_list = podcast_list
        self.podcast_downloader = PodcastDownloader(app_config=app_config, s3=self.s3, web_root=self.web_root)
        self._make_folder_structure()

    # endregion

    def get_rss_feed(self, feed: str) -> bytes:
        """Return the rss file for a given feed."""
        return self.podcast_rss[feed]

    async def _check_s3_files(self) -> None:
        """Function to list files in s3 bucket."""
        logger.info("⛅ Checking state of s3 bucket")
        if not self.s3:
            logger.debug("⛅ No s3 client to list files")
            return

        contents_list = await s3_file_cache.get_all(self.app_config.s3.bucket)

        session = get_session()
        s3_config = get_ap_config_s3_client()

        async with session.create_client("s3", **s3_config.__dict__) as s3_client:
            contents_str = ""
            if len(contents_list) > 0:
                for obj in contents_list:
                    contents_str += obj["Key"] + "\n"
                    if obj["Size"] == 0:  # This is for application/x-directory files, but no files should be empty
                        logger.warning("⛅ S3 Object is empty: %s DELETING", obj["Key"])
                        await s3_client.delete_object(Bucket=self.app_config.s3.bucket, Key=obj["Key"])
                    if obj["Key"].startswith("/"):
                        logger.warning("⛅ S3 Path starts with a /, this is not expected: %s DELETING", obj["Key"])
                        await s3_client.delete_object(Bucket=self.app_config.s3.bucket, Key=obj["Key"])
                    if "//" in obj["Key"]:
                        logger.warning("⛅ S3 Path contains a //, this is not expected: %s DELETING", obj["Key"])
                        await s3_client.delete_object(Bucket=self.app_config.s3.bucket, Key=obj["Key"])
                logger.trace("⛅ S3 Bucket Contents >>>\n%s", contents_str.strip())
            else:
                logger.info("⛅ No objects found in the bucket.")

    # endregion

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
        event_loop.run_until_complete(self.podcast_downloader.update_file_cache())
        event_times.set_event_time("grab_podcasts/Update file cache", time.time() - grab_podcasts_start_time)

        # Part 2: Download and process all podcasts
        ## Event Loop
        podcast_start_time = time.time()

        ## Create Task List
        podcast_tasks = []
        for podcast in self.podcast_list:
            task = self._grab_podcast_with_metrics(podcast)
            podcast_tasks.append(task)

        podcast_tasks.append(self._render_files())

        ## Run Tasks
        event_loop.run_until_complete(asyncio.gather(*podcast_tasks))
        event_times.set_event_time("grab_podcasts/Scrape", time.time() - podcast_start_time)

        # Part 3: Render files and cleanup
        ## Event Loop
        cleanup_start_time = time.time()

        ## Create Task List
        cleanup_tasks = []
        cleanup_tasks.append(self._render_filelist_html())
        cleanup_tasks.append(self.podcast_downloader.close_session())

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
        try:
            await self._grab_podcast(podcast)
            health.update_podcast_status(podcast.name_one_word, healthy_feed=True)
        except Exception:
            logger.exception("❌ Error grabbing podcast: %s", podcast.name_one_word)
            health.update_podcast_status(podcast.name_one_word, healthy_feed=False)

        elapsed_time = time.time() - podcast_grab_start_time
        event_times.set_event_time(f"grab_podcasts/Scrape/{podcast.name_one_word}", elapsed_time)
        logger.trace("Exiting _grab_podcast_with_metrics for podcast: %s", podcast.name_one_word)

    def _load_rss_from_file(self, podcast: PodcastConfig, rss_file_path: Path) -> etree._ElementTree | None:
        """Load the rss from file."""
        tree = None
        if podcast.live is False:
            logger.info("📄 Loading rss from file: %s", rss_file_path)
        else:
            logger.warning("📄 Loading rss from file: %s", rss_file_path)
        if rss_file_path.is_file():
            try:
                tree = etree.parse(rss_file_path)
            except etree.XMLSyntaxError:
                logger.exception("❌ Error parsing rss file: %s", rss_file_path)
        elif rss_file_path.is_dir():
            logger.error("❌ Calculated RSS feed path is a directory, not a file: %s", rss_file_path)
        else:
            logger.error("❌ Cannot find rss feed file: %s", rss_file_path)

        return tree

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
                    encoding="utf-8",
                    method="xml",
                    xml_declaration=True,
                )
            }
        )
        logger.info(
            "📄 Hosted feed: %srss/%s",
            self.app_config.inet_path,
            podcast.name_one_word,
        )

        # Upload to s3 if we are in s3 mode
        if (
            self.s3
            and previous_feed
            != self.podcast_rss[
                podcast.name_one_word
            ]  # This doesn't work when feed has build dates times on it, patreon for one
        ):
            session = get_session()
            s3_config = get_ap_config_s3_client()

            async with session.create_client("s3", **s3_config.__dict__) as s3_client:
                try:
                    # Upload the file
                    logger.trace("Uploading feed %s to s3...", podcast.name_one_word)
                    await s3_client.put_object(
                        Body=self.podcast_rss[podcast.name_one_word],
                        Bucket=self.app_config.s3.bucket,
                        Key="rss/" + podcast.name_one_word,
                        ContentType="application/rss+xml",
                    )
                    logger.info('📄⛅ Uploaded feed: "%s" to s3', podcast.name_one_word)
                except Exception:  # pylint: disable=broad-exception-caught
                    logger.exception("⛅❌ Unhandled s3 error trying to upload the file: %s")
        health.update_podcast_status(podcast.name_one_word, rss_available=True)
        logger.trace("Exiting _update_rss_feed")

    async def _download_podcast(self, podcast: PodcastConfig, rss_file_path: Path) -> etree._ElementTree | None:
        tree, download_healthy = await self.podcast_downloader.download_podcast(podcast)
        if tree:
            if tree_no_episodes(tree):
                logger.error("❌ Downloaded podcast rss %s has no episodes, not writing to disk", podcast.name_one_word)
                health.update_podcast_status(podcast.name_one_word, healthy_feed=False)
            else:
                # Write rss to disk
                tree.write(
                    str(rss_file_path),
                    encoding="utf-8",
                    xml_declaration=True,
                )
                logger.debug("💾 Wrote rss to disk: %s", rss_file_path)

        else:
            logger.error("❌ Unable to download podcast, something is wrong, will try to load from file")

        if download_healthy:
            health.update_podcast_status(podcast.name_one_word, healthy_download=True)
        else:
            health.update_podcast_status(podcast.name_one_word, healthy_download=False)

        return tree

    async def _grab_podcast(self, podcast: PodcastConfig) -> None:
        """Function to download a podcast and store the rss."""
        tree = None
        previous_feed = b""
        logger.info("📜 Processing podcast to archive: %s", podcast.new_name)

        with contextlib.suppress(KeyError):  # Set the previous feed var if it exists
            previous_feed = self.podcast_rss[podcast.name_one_word]

        rss_file_path = self.web_root / "rss" / podcast.name_one_word

        if podcast.name_one_word == "":
            logger.error("❌ Podcast has no name_one_word set in config, cannot proceed")
            return

        if podcast.live is True:  # download all the podcasts
            tree = await self._download_podcast(podcast, rss_file_path)
            if tree:
                last_fetched = int(time.time())
                health.update_podcast_status(podcast.name_one_word, rss_fetching_live=True, last_fetched=last_fetched)
            else:
                # There should be a previous error message too
                logger.error("❌ Unable to download podcast: %s", podcast.name_one_word)

        else:
            logger.info('📄 "live": false, in config so not fetching new episodes')
            health.update_podcast_status(podcast.name_one_word, rss_fetching_live=False)

        if tree_no_episodes(tree):  # If there are no episodes, we can't host it
            tree = None

        if tree is None:  # Serving a podcast that we can't currently download?, load it from file
            tree = self._load_rss_from_file(podcast, rss_file_path)

        if tree_no_episodes(tree):  # If there are still not episodes, we still can't host it
            tree = None

        if tree is not None:
            await self._update_rss_feed(podcast, tree, previous_feed)
            health.update_podcast_episode_info(podcast.name_one_word, tree)
        else:
            logger.error("❌ Unable to host podcast: %s, something is wrong", podcast.name_one_word)
            health.update_podcast_status(podcast.name_one_word, rss_available=False)

        del tree

        logger.trace("Exiting _grab_podcast for %s", podcast.name_one_word)

    async def _render_files(self) -> None:
        """Actual function to upload static to s3 and copy index.html."""
        render_files_start_time = time.time()
        health.update_core_status(currently_rendering=True)

        await self._load_about_page()  # Done first since it affects the header for everything

        # robots.txt
        robots_txt_content = "User-Agent: *\nDisallow: /\n"
        self.webpages.add(path="robots.txt", mime="text/plain", content=robots_txt_content)

        # favicon.ico
        favicon_path = self.static_directory / "favicon.ico"
        if favicon_path.is_file():
            with favicon_path.open("rb") as favicon:
                self.webpages.add(path="favicon.ico", mime="image/x-icon", content=favicon.read())

        # Static items
        static_items_to_copy = [file for file in self.static_directory.rglob("*") if file.is_file()]

        for item in static_items_to_copy:
            item_relative_path = str(item.relative_to(self.app_directory))
            item_mime = magic.from_file(str(item), mime=True)
            logger.trace("💾 Registering static item: %s, mime: %s", item, item_mime)

            if item_mime.startswith("text"):
                with item.open() as static_item:
                    self.webpages.add(path=item_relative_path, mime=item_mime, content=static_item.read())
            else:
                with item.open("rb") as static_item:
                    self.webpages.add(path=item_relative_path, mime=item_mime, content=static_item.read())

        # Templates
        env = Environment(loader=FileSystemLoader(str(self.template_directory)), autoescape=True)
        templates_to_render = [
            "guide.html.j2",
            "index.html.j2",
            "health.html.j2",
            "webplayer.html.j2",
        ]

        logger.debug("💾 Templates to render: %s", templates_to_render)

        for template_path in templates_to_render:
            output_filename = Path(template_path).name.replace(".j2", "")
            output_path = self.web_root / output_filename
            logger.debug("💾 Rendering template: %s to %s", template_path, output_path)

            template = env.get_template(template_path)
            current_time = int(time.time())
            rendered_output = template.render(
                app_config=self.app_config,
                podcasts=self.podcast_list,
                about_page=self.about_page_exists,
                header=self.webpages.generate_header(output_filename, debug=self.debug),
            )

            self.webpages.add(output_filename, "text/html", rendered_output)
            health.update_template_status(output_filename, last_rendered=current_time)

        logger.debug("💾 Done rendering static pages")

        webpage_list = list({k: v for k, v in self.webpages.get_all_pages().items() if k != "filelist.html"}.values())
        await self._write_webpages(webpage_list)

        health.update_core_status(currently_rendering=False)
        event_times.set_event_time("grab_podcasts/Scrape/_render_files", time.time() - render_files_start_time)

    # endregion

    # region Housekeeping

    def _make_folder_structure(self) -> None:
        """Ensure that web_root folder structure exists."""
        logger.debug("Checking folder structure")

        folders = [self.instance_path, self.web_root, self.web_root / "rss", self.web_root / "content"]

        folders.extend(self.web_root / "content" / entry.name_one_word for entry in self.podcast_list)

        for folder in folders:
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except PermissionError as exc:
                err = (
                    f"❌ You do not have permission to create folder: {folder}"
                    "Run this this script as a different user probably, or check permissions of the web_root."
                )
                logger.exception(err)
                raise PermissionError(err) from exc

    # endregion

    # region Other webpages

    async def _render_filelist_html(self) -> None:
        """Function to render filelist.html.

        This is separate from render_files() since it needs to be done after grabbing podcasts.
        """
        await self._check_s3_files()

        base_url, file_list = await self.podcast_downloader.get_file_list()

        env = Environment(loader=FileSystemLoader(self.template_directory), autoescape=True)

        template_filename = "filelist.html.j2"
        output_filename = template_filename.replace(".j2", "")

        template = env.get_template(template_filename)

        current_time = int(time.time())

        rendered_output = template.render(
            app_config=self.app_config,
            base_url=base_url,
            file_list=file_list,
            about_page=self.about_page_exists,
            header=self.webpages.generate_header(output_filename, debug=self.debug),
        )

        self.webpages.add(path=output_filename, mime="text/html", content=rendered_output)
        health.update_template_status(output_filename, last_rendered=current_time)
        await self._write_webpages([self.webpages.get_webpage(output_filename)])

    async def write_health_s3(self) -> None:
        """Write health.json to s3."""
        if not self.s3:
            return

        start_time = time.time()

        health_json = health.get_health(self).model_dump()
        health_json_str = json.dumps(health_json, indent=4)

        profile_json_str = event_times.model_dump_json(indent=4)

        self.webpages.add(path="api/health", mime="application/json", content=health_json_str)
        self.webpages.add(path="api/profile", mime="application/json", content=profile_json_str)

        await self._write_webpages(
            [
                self.webpages.get_webpage("api/health"),
                self.webpages.get_webpage("api/profile"),
            ],
            force_override=True,
        )

        event_times.set_event_time("grab_podcasts/Post Scrape/write_health_s3", time.time() - start_time)

    async def _write_webpages(self, webpages: list[Webpage], *, force_override: bool = False) -> None:
        """Write files to disk, and to s3 if needed."""
        str_webpages = f"{(len(webpages))} pages to files"
        if len(webpages) == 1:
            str_webpages = f"{webpages[0].path} to file"

        if self.s3:
            logger.info("⛅💾 Writing %s locally and to s3", str_webpages)
        else:
            logger.info("💾 Writing %s locally", str_webpages)
        for webpage in webpages:
            webpage_path = Path(webpage.path)
            directory_path = self.web_root / webpage_path.parent

            directory_path.mkdir(parents=True, exist_ok=True)

            page_path_local = self.web_root / webpage.path
            logger.trace("💾 Writing page locally: %s", page_path_local)
            page_content_bytes = (
                webpage.content.encode("utf-8") if isinstance(webpage.content, str) else webpage.content
            )

            with page_path_local.open("wb") as page:
                page.write(page_content_bytes)

            if self.s3:
                s3_key = webpage_path.as_posix()
                if not force_override and s3_file_cache.check_file_exists(s3_key, len(page_content_bytes)):
                    logger.trace("Skipping upload to S3 for %s as it already exists with the same size.", s3_key)
                    continue
                logger.trace("⛅💾 Writing page s3: %s", s3_key)

                session = get_session()
                s3_config = get_ap_config_s3_client()

                async with session.create_client("s3", **s3_config.__dict__) as s3_client:
                    try:
                        await s3_client.put_object(
                            Body=page_content_bytes,
                            Bucket=self.app_config.s3.bucket,
                            Key=s3_key,
                            ContentType=webpage.mime,
                        )
                        logger.trace(f"Uploaded page to s3: {s3_key}")
                    except Exception:
                        logger.exception("⛅❌ Unhandled s3 error trying to upload the file: %s", s3_key)

        logger.info("💾 Done writing %s", str_webpages)

    async def _load_about_page(self) -> None:
        """Create about page if needed."""
        about_page_md_filename = "about.md"
        about_page_md_expected_path: Path = self.instance_path / about_page_md_filename
        about_page_filename = "about.html"

        if about_page_md_expected_path.exists():  # Check if about.html exists, affects index.html so it's first.
            with about_page_md_expected_path.open(encoding="utf-8") as about_page:
                about_page_md_rendered = markdown.markdown(about_page.read(), extensions=["tables"])

            env = Environment(loader=FileSystemLoader(self.template_directory), autoescape=True)

            template_filename = "about.html.j2"
            output_filename = template_filename.replace(".j2", "")

            template = env.get_template(template_filename)

            self.webpages.add(output_filename, mime="text/html", content="generating...")

            about_page_str = template.render(
                app_config=self.app_config,
                podcasts=self.podcast_list,
                header=self.webpages.generate_header(output_filename, debug=self.debug),
                about_content=about_page_md_rendered,
            )

            self.webpages.add(output_filename, mime="text/html", content=about_page_str)
            self.about_page_exists = True
            health.update_core_status(about_page_exists=True)
            logger.info("💾 About page exists!")
            await self._write_webpages([self.webpages.get_webpage(about_page_filename)])
        else:
            health.update_core_status(about_page_exists=False)
            logger.debug("About page doesn't exist")

    # endregion
