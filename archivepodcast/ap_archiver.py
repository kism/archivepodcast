"""Module to handle the ArchivePodcast object."""

import contextlib
import os
import threading
import time
from typing import TYPE_CHECKING

import boto3
import magic
import markdown
from jinja2 import Environment, FileSystemLoader
from lxml import etree

from .ap_downloader import PodcastDownloader
from .ap_health import PodcastArchiverHealth
from .ap_webpages import Webpages
from .helpers import list_all_s3_objects
from .logger import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client  # pragma: no cover
else:
    S3Client = object

logger = get_logger(__name__)


class PodcastArchiver:
    """ArchivePodcast object."""

    def __init__(self, app_config: dict, podcast_list: list, instance_path: str, root_path: str) -> None:
        """Initialise the ArchivePodcast object."""
        # Health object
        self.health = PodcastArchiverHealth()
        self.health.update_core_status(currently_loading_config=True)

        # Set the paths, TODO: There are too many
        self.root_path = root_path
        self.instance_path = instance_path
        self.web_root = os.path.join(instance_path, "web")  # This gets used so often, it's worth the variable
        self.app_directory = os.path.join("archivepodcast")
        self.static_directory = os.path.join("archivepodcast", "static")
        self.template_directory = os.path.join("archivepodcast", "templates")

        # Set the config and podcast list
        self.app_config: dict = {}
        self.podcast_list: list = []
        self.podcast_rss: dict[str, str] = {}
        self.webpages: Webpages = Webpages()
        self.s3: S3Client | None = None
        self.about_page_exists = False
        self.load_config(app_config, podcast_list)

        # Done, update health
        self.health.update_core_status(currently_loading_config=False)

    def load_config(self, app_config: dict, podcast_list: list) -> None:
        """Load the config from the config file."""
        self.app_config = app_config
        self.podcast_list = podcast_list
        self.load_s3()
        self.podcast_downloader = PodcastDownloader(app_config=app_config, s3=self.s3, web_root=self.web_root)
        self.make_folder_structure()
        self.render_files()

    def get_rss_feed(self, feed: str) -> str:
        """Return the rss file for a given feed."""
        return self.podcast_rss[feed]

    def load_about_page(self) -> None:
        """Create about page if needed."""
        about_page_md_filename = "about.md"
        about_page_md_expected_path = os.path.join(self.instance_path, about_page_md_filename)
        about_page_filename = "about.html"

        if os.path.exists(about_page_md_expected_path):  # Check if about.html exists, affects index.html so it's first.
            with open(about_page_md_expected_path, encoding="utf-8") as about_page:
                about_page_md_rendered = markdown.markdown(about_page.read(), extensions=["tables"])

            env = Environment(loader=FileSystemLoader(self.template_directory), autoescape=True)

            template_filename = "about.html.j2"
            output_filename = template_filename.replace(".j2", "")

            template = env.get_template(template_filename)

            current_time = int(time.time())

            self.webpages.add(output_filename, mime="text/html", content="generating...")

            about_page_str = template.render(
                app_config=self.app_config,
                podcasts=self.podcast_list,
                last_generated_date=current_time,
                header=self.webpages.generate_header(output_filename),
                about_content=about_page_md_rendered,
            )

            self.webpages.add(output_filename, mime="text/html", content=about_page_str)
            self.about_page_exists = True
            self.health.update_core_status(about_page_exists=True)
            logger.info("💾 About page exists!")
            self.write_webpages([self.webpages.get_webpage(about_page_filename)])
        else:
            self.health.update_core_status(about_page_exists=False)
            logger.debug("About page doesn't exist")

    def make_folder_structure(self) -> None:
        """Ensure that web_root folder structure exists."""
        logger.debug("Checking folder structure")

        folders = []

        folders.append(self.instance_path)
        folders.append(self.web_root)
        folders.append(os.path.join(self.web_root, "rss"))
        folders.append(os.path.join(self.web_root, "content"))

        folders.extend(os.path.join(self.web_root, "content", entry["name_one_word"]) for entry in self.podcast_list)

        for folder in folders:
            try:
                os.mkdir(folder)
            except FileExistsError:
                pass
            except PermissionError as exc:
                err = (
                    f"❌ You do not have permission to create folder: {folder}"
                    "Run this this script as a different user probably, or check permissions of the web_root."
                )
                logger.exception(err)
                raise PermissionError(err) from exc

    def load_s3(self) -> None:
        """Function to get a s3 credential if one is needed."""
        if self.app_config["storage_backend"] == "s3":
            # This is specifically for pytest, as moto doesn't support the endpoint_url
            api_url = None
            if self.app_config["s3"]["api_url"] != "":
                api_url = self.app_config["s3"]["api_url"]

            self.s3 = boto3.client(
                "s3",
                endpoint_url=api_url,
                aws_access_key_id=self.app_config["s3"]["access_key_id"],
                aws_secret_access_key=self.app_config["s3"]["secret_access_key"],
            )
            logger.info(f"⛅ Authenticated s3, using bucket: {self.app_config['s3']['bucket']}")
            self.health.update_core_status(s3_enabled=True)
            self.check_s3_files()
        else:
            logger.info("⛅ Not using s3")
            self.health.update_core_status(s3_enabled=False)

    def check_s3_files(self) -> None:
        """Function to list files in s3 bucket."""
        logger.info("⛅ Checking state of s3 bucket")
        if not self.s3:
            logger.debug("⛅ No s3 client to list files")
            return

        contents_list = list_all_s3_objects(self.s3, self.app_config["s3"]["bucket"])

        contents_str = ""
        if len(contents_list) > 0:
            for obj in contents_list:
                contents_str += obj["Key"] + "\n"
                if obj["Size"] == 0:  # This is for application/x-directory files, but no files should be empty
                    logger.warning("⛅ S3 Object is empty: %s DELETING", obj["Key"])
                    self.s3.delete_object(Bucket=self.app_config["s3"]["bucket"], Key=obj["Key"])
                if obj["Key"].startswith("/"):
                    logger.warning("⛅ S3 Path starts with a /, this is not expected: %s DELETING", obj["Key"])
                    self.s3.delete_object(Bucket=self.app_config["s3"]["bucket"], Key=obj["Key"])
                if "//" in obj["Key"]:
                    logger.warning("⛅ S3 Path contains a //, this is not expected: %s DELETING", obj["Key"])
                    self.s3.delete_object(Bucket=self.app_config["s3"]["bucket"], Key=obj["Key"])
            logger.debug("⛅ S3 Bucket Contents >>>\n%s", contents_str.strip())
        else:
            logger.info("⛅ No objects found in the bucket.")

    def grab_podcasts(self) -> None:
        """Loop through defined podcasts, download and store the rss."""
        current_datetime = int(time.time())
        self.health.update_core_status(last_run=current_datetime)

        for podcast in self.podcast_list:
            try:
                self._grab_podcast(podcast)
                self.health.update_podcast_status(podcast["name_one_word"], healthy=True)
                logger.debug("💾 Updating filelist.html")
            except Exception:
                logger.exception("❌ Error grabbing podcast: %s", podcast["name_one_word"])
                self.health.update_podcast_status(podcast["name_one_word"], healthy=False)

        try:
            self.render_filelist_html()
        except Exception:
            logger.exception("❌ Unhandled exception rendering filelist.html")

    def _load_rss_from_file(self, podcast: dict, rss_file_path: str) -> etree._ElementTree | None:
        """Load the rss from file."""
        tree = None
        if podcast["live"] is False:
            logger.info("📄 Loading rss from file: %s", rss_file_path)
        else:
            logger.warning("📄 Loading rss from file: %s", rss_file_path)
        if os.path.exists(rss_file_path):
            try:
                tree = etree.parse(rss_file_path)
            except etree.XMLSyntaxError:
                logger.exception("❌ Error parsing rss file: %s", rss_file_path)
        else:
            logger.error("❌ Cannot find rss feed file: %s", rss_file_path)

        return tree

    def _update_rss_feed(self, podcast: dict, tree: etree._ElementTree, previous_feed: str) -> None:
        """Update the rss feed, in memory and s3."""
        self.podcast_rss.update(
            {
                podcast["name_one_word"]: etree.tostring(
                    tree.getroot(),
                    encoding="utf-8",
                    method="xml",
                    xml_declaration=True,
                )
            }
        )
        logger.info(
            f"📄 Hosted: {self.app_config['inet_path']}rss/{ podcast['name_one_word'] }",
        )

        # Upload to s3 if we are in s3 mode
        if (
            self.s3
            and previous_feed
            != self.podcast_rss[
                podcast["name_one_word"]
            ]  # This doesn't work when feed has build dates times on it, patreon for one
        ):
            try:
                # Upload the file
                self.s3.put_object(
                    Body=self.podcast_rss[podcast["name_one_word"]],
                    Bucket=self.app_config["s3"]["bucket"],
                    Key="rss/" + podcast["name_one_word"],
                    ContentType="application/rss+xml",
                )
                logger.info('📄⛅ Uploaded feed "%s" to s3', podcast["name_one_word"])
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("⛅❌ Unhandled s3 error trying to upload the file: %s")
        self.health.update_podcast_status(podcast["name_one_word"], rss_available=True)

    def _download_podcast(self, podcast: dict, rss_file_path: str) -> etree._ElementTree | None:
        tree = self.podcast_downloader.download_podcast(podcast)
        if tree:
            # Write rss to disk
            tree.write(
                rss_file_path,
                encoding="utf-8",
                xml_declaration=True,
            )
            logger.debug("💾 Wrote rss to disk: %s", rss_file_path)

        else:
            logger.error("❌ Unable to download podcast, something is wrong, will try to load from file")

        return tree

    def _grab_podcast(self, podcast: dict) -> None:
        """Function to download a podcast and store the rss."""
        tree = None
        previous_feed = ""
        logger.info("📜 Processing podcast to archive: %s", podcast["new_name"])

        with contextlib.suppress(KeyError):  # Set the previous feed var if it exists
            previous_feed = self.podcast_rss[podcast["name_one_word"]]

        rss_file_path = os.path.join(self.web_root, "rss", podcast["name_one_word"])

        if podcast["live"] is True:  # download all the podcasts
            tree = self._download_podcast(podcast, rss_file_path)
            last_fetched = int(time.time())
            self.health.update_podcast_status(
                podcast["name_one_word"], rss_fetching_live=True, last_fetched=last_fetched
            )
        else:
            logger.info('📄 "live": false, in config so not fetching new episodes')
            self.health.update_podcast_status(podcast["name_one_word"], rss_fetching_live=False)

        if tree is None:  # Serving a podcast that we can't currently download?, load it from file
            tree = self._load_rss_from_file(podcast, rss_file_path)

        if tree is not None:
            self._update_rss_feed(podcast, tree, previous_feed)
            self.health.update_podcast_episode_info(podcast["name_one_word"], tree)

        else:
            logger.error(f"❌ Unable to host podcast: {podcast['name_one_word']}, something is wrong")
            self.health.update_podcast_status(podcast["name_one_word"], rss_available=False)

    def render_files(self) -> None:
        """Function to upload static to s3 and copy index.html."""
        logger.info("💾 Rendering static pages in thread")
        threading.Thread(target=self._render_files, daemon=True).start()

    def _render_files(self) -> None:
        """Actual function to upload static to s3 and copy index.html."""
        self.health.update_core_status(currently_rendering=True)

        self.load_about_page()  # Done first since it affects the header for everything

        # robots.txt
        robots_txt_content = "User-Agent: *\nDisallow: /\n"
        self.webpages.add(path="robots.txt", mime="text/plain", content=robots_txt_content)

        # Static items
        static_items_to_copy = [
            os.path.join(root, file) for root, __, files in os.walk(self.static_directory) for file in files
        ]

        for item in static_items_to_copy:
            item_relative_path = os.path.relpath(item, self.app_directory)
            item_mime = magic.from_file(item, mime=True)
            logger.debug("💾 Registering static item: %s, mime: %s", item, item_mime)

            if item_mime.startswith("text"):
                with open(item) as static_item:
                    self.webpages.add(path=item_relative_path, mime=item_mime, content=static_item.read())
            else:
                with open(item, "rb") as static_item:
                    self.webpages.add(path=item_relative_path, mime=item_mime, content=static_item.read())

        # Templates
        env = Environment(loader=FileSystemLoader(self.template_directory), autoescape=True)
        templates_to_render = ["guide.html.j2", "index.html.j2", "health.html.j2", "webplayer.html.j2"]

        logger.debug("💾 Templates to render: %s", templates_to_render)

        for template_path in templates_to_render:
            output_filename = os.path.basename(template_path).replace(".j2", "")
            output_path = os.path.join(self.web_root, output_filename)
            logger.debug("💾 Rendering template: %s to %s", template_path, output_path)

            template = env.get_template(template_path)
            current_time = int(time.time())
            rendered_output = template.render(
                app_config=self.app_config,
                podcasts=self.podcast_list,
                about_page=self.about_page_exists,
                last_generated_date=current_time,
                header=self.webpages.generate_header(output_filename),
            )

            self.webpages.add(output_filename, "text/html", rendered_output)
            self.health.update_template_status(output_filename, last_rendered=current_time)

        logger.debug("💾 Done rendering static pages")
        webpage_list = list({k: v for k, v in self.webpages.get_all().items() if k != "filelist.html"}.values())
        self.write_webpages(webpage_list)

        self.render_filelist_html()  # Separate, we need to adhoc call this one
        self.health.update_core_status(currently_rendering=False)

    def render_filelist_html(self) -> None:
        """Function to render filelist.html.

        This is separate from render_files() since it needs to be done after grabbing podcasts.
        """
        self.check_s3_files()
        base_url, file_list = self.podcast_downloader.get_file_list()

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
            last_generated_date=current_time,
            header=self.webpages.generate_header(output_filename),
        )

        self.webpages.add(path=output_filename, mime="text/html", content=rendered_output)
        self.health.update_template_status(output_filename, last_rendered=current_time)
        self.write_webpages([self.webpages.get_webpage(output_filename)])

    def write_webpages(self, webpages: list) -> None:
        """Write files to disk, and to s3 if needed."""
        str_webpages = f"{(len(webpages))} pages to files"
        if len(webpages) == 1:
            str_webpages = f"{webpages[0].path} to file"

        if self.s3:
            logger.info(f"⛅💾 Writing {str_webpages} locally and to s3")
        else:
            logger.info(f"💾 Writing {str_webpages} locally")
        for webpage in webpages:
            dirs_in_path = os.path.dirname(webpage.path)
            directories_list = dirs_in_path.split(os.sep)

            for i in range(1, len(directories_list) + 1):
                directory = os.path.join(self.web_root, *directories_list[:i])
                if not os.path.exists(directory):
                    logger.debug("💾 Creating directory: %s", directory)
                    os.mkdir(directory)

            page_path_local = os.path.join(self.web_root, webpage.path)
            logger.trace("💾 Writing page locally: %s", page_path_local)
            page_content_bytes = (
                webpage.content.encode("utf-8") if isinstance(webpage.content, str) else webpage.content
            )
            with open(page_path_local, "wb") as page:
                page.write(page_content_bytes)

            if self.s3:
                logger.trace("⛅💾 Writing page s3: %s", webpage.path)

                self.s3.put_object(
                    Body=page_content_bytes,
                    Bucket=self.app_config["s3"]["bucket"],
                    Key=webpage.path,
                    ContentType=webpage.mime,
                )

        logger.info(f"💾 Done writing {str_webpages}")
