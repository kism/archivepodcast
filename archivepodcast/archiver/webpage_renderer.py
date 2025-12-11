"""Module to render static webpages for ArchivePodcast."""

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

import magic
import markdown
from aiobotocore.session import get_session
from jinja2 import Environment, FileSystemLoader

from archivepodcast.constants import JSON_INDENT
from archivepodcast.instances.config import get_ap_config_s3_client
from archivepodcast.instances.health import health
from archivepodcast.instances.path_cache import s3_file_cache
from archivepodcast.instances.path_helper import get_app_paths
from archivepodcast.instances.profiler import event_times
from archivepodcast.utils.health import PodcastArchiverHealthAPI
from archivepodcast.utils.logger import get_logger
from archivepodcast.utils.time import warn_if_too_long

from .webpages import Webpage, Webpages

if TYPE_CHECKING:
    from archivepodcast.archiver.podcast_archiver import APFileList  # pragma: no cover
    from archivepodcast.config import AppConfig, PodcastConfig  # pragma: no cover
else:
    AppConfig = object
    PodcastConfig = object
    APFileList = object
logger = get_logger(__name__)


class WebpageRenderer:
    """Class to render static webpages for ArchivePodcast."""

    def __init__(
        self,
        app_config: AppConfig,
        podcast_list: list[PodcastConfig],
        *,
        s3: bool,
        debug: bool,
        # podcast_downloader: PodcastsDownloader,
    ) -> None:
        """Initialise the WebpageRenderer object."""
        self.about_page_exists = False
        self._app_config = app_config
        self._s3 = s3

        self._podcast_list = podcast_list
        self.webpages = Webpages()
        self._debug = debug

        logger.debug("WebpageRenderer initialized with web_root: %s", get_app_paths().web_root)

    async def render_files(self) -> None:
        """Upload static files to s3 and copy index.html."""
        app_paths = get_app_paths()
        render_files_start_time = time.time()
        health.update_core_status(currently_rendering=True)

        await self._load_about_page()  # Done first since it affects the header for everything

        # robots.txt
        robots_txt_content = "User-Agent: *\nDisallow: /\n"
        self.webpages.add(path="robots.txt", mime="text/plain", content=robots_txt_content)

        # favicon.ico override, will be in static too
        favicon_path = app_paths.static_directory / "favicon.ico"
        if favicon_path.is_file():
            with favicon_path.open("rb") as favicon:
                self.webpages.add(path="favicon.ico", mime="image/x-icon", content=favicon.read())

        # Static items
        static_items_to_copy = [file for file in app_paths.static_directory.rglob("*") if file.is_file()]

        for item in static_items_to_copy:
            item_relative_path = str(item.relative_to(app_paths.static_directory))
            # Store static files with static/ prefix to match blueprint expectations
            static_path = f"static/{item_relative_path}"
            item_mime = magic.from_file(str(item), mime=True)
            logger.trace("Registering static item: %s, mime: %s", item, item_mime)

            if item_mime.startswith("text"):
                with item.open() as static_item:
                    self.webpages.add(path=static_path, mime=item_mime, content=static_item.read())
            else:
                with item.open("rb") as static_item:
                    self.webpages.add(path=static_path, mime=item_mime, content=static_item.read())

        # Templates
        env = Environment(loader=FileSystemLoader(str(app_paths.template_directory)), autoescape=True)
        templates_to_render = [
            "guide.html.j2",
            "index.html.j2",
            "health.html.j2",
            "webplayer.html.j2",
        ]

        logger.debug("Templates to render: %s", templates_to_render)

        for template_path in templates_to_render:
            output_filename = Path(template_path).name.replace(".j2", "")
            output_path = app_paths.web_root / output_filename
            logger.debug("Rendering template: %s to %s", template_path, output_path)

            template = env.get_template(template_path)
            current_time = int(time.time())
            rendered_output = template.render(
                app_config=self._app_config,
                podcasts=self._podcast_list,
                about_page=self.about_page_exists,
                header=self.webpages.generate_header(output_filename, debug=self._debug),
            )

            self.webpages.add(output_filename, "text/html", rendered_output)
            health.update_template_status(output_filename, last_rendered=current_time)

        logger.debug("Done rendering static pages")

        webpage_list = list({k: v for k, v in self.webpages.get_all_pages().items() if k != "filelist.html"}.values())
        await self._write_webpages(webpage_list)

        health.update_core_status(currently_rendering=False)
        event_times.set_event_time("grab_podcasts/Scrape/_render_files", time.time() - render_files_start_time)

    async def render_filelist_html(self, ap_file_list: APFileList) -> None:
        """Function to render filelist.html.

        This is separate from render_files() since it needs to be done after grabbing podcasts.
        """
        app_paths = get_app_paths()
        await self._check_s3_files()

        env = Environment(loader=FileSystemLoader(app_paths.template_directory), autoescape=True)

        template_filename = "filelist.html.j2"
        output_filename = template_filename.replace(".j2", "")

        template = env.get_template(template_filename)

        current_time = int(time.time())

        rendered_output = template.render(
            app_config=self._app_config,
            base_url=ap_file_list.base_url,
            file_list=ap_file_list.files,
            about_page=self.about_page_exists,
            header=self.webpages.generate_header(output_filename, debug=self._debug),
        )

        self.webpages.add(path=output_filename, mime="text/html", content=rendered_output)
        health.update_template_status(output_filename, last_rendered=current_time)
        await self._write_webpages([self.webpages.get_webpage(output_filename)])

    async def write_health_s3(self, health_api_response: PodcastArchiverHealthAPI) -> None:
        """Write health.json to s3."""
        if not self._s3:
            return

        start_time = time.time()

        health_json = health_api_response.model_dump()
        health_json_str = json.dumps(health_json, indent=JSON_INDENT)

        profile_json_str = event_times.model_dump_json(indent=JSON_INDENT)

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
        app_paths = get_app_paths()
        str_webpages = f"{(len(webpages))} pages to files"
        if len(webpages) == 1:
            str_webpages = f"{webpages[0].path} to file"

        s3_pages_uploaded = []
        s3_pages_skipped = []

        for webpage in webpages:
            webpage_path = Path(webpage.path)
            directory_path = app_paths.web_root / webpage_path.parent

            directory_path.mkdir(parents=True, exist_ok=True)

            page_path_local = app_paths.web_root / webpage.path
            logger.trace("Writing page locally: %s", page_path_local)
            page_content_bytes = (
                webpage.content.encode("utf-8") if isinstance(webpage.content, str) else webpage.content
            )

            with page_path_local.open("wb") as page:
                page.write(page_content_bytes)

            if self._s3:
                s3_key = webpage_path.as_posix()
                if not force_override and s3_file_cache.check_file_exists(s3_key, len(page_content_bytes)):
                    logger.trace("Skipping upload to S3 for %s as it already exists with the same size.", s3_key)
                    s3_pages_skipped.append(s3_key)
                    continue

                s3_pages_uploaded.append(s3_key)
                logger.trace("Writing page s3: %s", s3_key)

                session = get_session()
                s3_config = get_ap_config_s3_client()

                async with session.create_client("s3", **s3_config.model_dump()) as s3_client:
                    try:
                        start_time = time.time()
                        await s3_client.put_object(
                            Body=page_content_bytes,
                            Bucket=self._app_config.s3.bucket,
                            Key=s3_key,
                            ContentType=webpage.mime,
                        )
                        warn_if_too_long(f"upload page: {s3_key} to s3", time.time() - start_time)
                        logger.trace(f"Uploaded page to s3: {s3_key}")
                    except Exception:
                        logger.exception("Unhandled s3 error trying to upload the file: %s", s3_key)

        msg = f"Wrote {str_webpages}"
        if self._s3:
            if len(s3_pages_skipped) == 1:
                msg += ", skipped upload due to same size"
            elif len(s3_pages_skipped) > 1:
                msg += f", skipped {len(s3_pages_skipped)} s3 uploads due to matching size"
                logger.debug("Skipped s3 uploads: %s", s3_pages_skipped)
                logger.debug("Uploaded s3 pages: %s", s3_pages_uploaded)
            elif len(s3_pages_uploaded) == 1:
                msg += ", uploaded to s3"
            else:
                msg += ", all pages uploaded to s3"
        logger.info(msg)

    async def _load_about_page(self) -> None:
        """Create about page if needed."""
        app_paths = get_app_paths()
        about_page_md_filename = "about.md"
        about_page_md_expected_path: Path = app_paths.instance_path / about_page_md_filename
        about_page_filename = "about.html"

        if about_page_md_expected_path.exists():  # Check if about.html exists, affects index.html so it's first.
            with about_page_md_expected_path.open(encoding="utf-8") as about_page:
                about_page_md_rendered = markdown.markdown(about_page.read(), extensions=["tables"])

            env = Environment(loader=FileSystemLoader(app_paths.template_directory), autoescape=True)

            template_filename = "about.html.j2"
            output_filename = template_filename.replace(".j2", "")

            template = env.get_template(template_filename)

            self.webpages.add(output_filename, mime="text/html", content="generating...")

            about_page_str = template.render(
                app_config=self._app_config,
                podcasts=self._podcast_list,
                header=self.webpages.generate_header(output_filename, debug=self._debug),
                about_content=about_page_md_rendered,
            )

            self.webpages.add(output_filename, mime="text/html", content=about_page_str)
            self.about_page_exists = True
            health.update_core_status(about_page_exists=True)
            logger.info("About page exists, rendering and including")
            await self._write_webpages([self.webpages.get_webpage(about_page_filename)])
        else:
            health.update_core_status(about_page_exists=False)
            logger.debug("About page doesn't exist")

    async def _check_s3_files(self) -> None:
        """Function to list files in s3 bucket."""
        logger.debug("Checking state of s3 bucket")
        if not self._s3:
            logger.debug("No s3 client to list files")
            return

        contents_list = await s3_file_cache.get_all(self._app_config.s3.bucket)

        session = get_session()
        s3_config = get_ap_config_s3_client()

        cleanup_actions = 0

        def log_first_message() -> None:
            nonlocal cleanup_actions
            if cleanup_actions == 0:
                logger.warning("Starting cleanup of unexpected S3 objects")
            cleanup_actions += 1

        async with session.create_client("s3", **s3_config.model_dump()) as s3_client:
            contents_str = ""
            if len(contents_list) > 0:
                for obj in contents_list:
                    contents_str += obj["Key"] + "\n"
                    if obj["Size"] == 0:  # This is for application/x-directory files, but no files should be empty
                        log_first_message()
                        logger.warning("S3 Object is empty: %s DELETING", obj["Key"])
                        await s3_client.delete_object(Bucket=self._app_config.s3.bucket, Key=obj["Key"])
                    if obj["Key"].startswith("/"):
                        log_first_message()
                        logger.warning("S3 Path starts with a /, this is not expected: %s DELETING", obj["Key"])
                        await s3_client.delete_object(Bucket=self._app_config.s3.bucket, Key=obj["Key"])
                    if "//" in obj["Key"]:
                        log_first_message()
                        logger.warning("S3 Path contains a //, this is not expected: %s DELETING", obj["Key"])
                        await s3_client.delete_object(Bucket=self._app_config.s3.bucket, Key=obj["Key"])
                logger.trace("S3 Bucket Contents >>>\n%s", contents_str.strip())
            else:
                logger.info("No objects found in the bucket.")
