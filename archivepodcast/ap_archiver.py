"""Module to handle the ArchivePodcast object."""

import contextlib
import os
import threading
from typing import TYPE_CHECKING

import boto3
from jinja2 import Environment, FileSystemLoader
from lxml import etree

from .ap_downloader import PodcastDownloader
from .logger import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
else:
    S3Client = object

logger = get_logger(__name__)


class PodcastArchiver:
    """ArchivePodcast object."""

    def __init__(self, app_settings: dict, podcast_list: list, instance_path: str) -> None:
        """Initialise the ArchivePodcast object."""
        self.instance_path = instance_path
        self.web_root = os.path.join(instance_path, "web")  # This gets used so often, it's worth the variable
        self.app_settings: dict = {}
        self.podcast_xml: dict[str, str] = {}
        self.podcast_list: list = []
        self.s3: S3Client | None = None
        self.about_page: str | None = None
        self.load_settings(app_settings, podcast_list)

    def load_settings(self, app_settings: dict, podcast_list: list) -> None:
        """Load the settings from the settings file."""
        self.app_settings = app_settings
        self.podcast_list = podcast_list
        self.load_s3()
        self.podcast_downloader = PodcastDownloader(app_settings=app_settings, s3=self.s3, web_root=self.web_root)
        self.make_folder_structure()
        self.make_about_page()
        self.upload_static()

    def get_rss_xml(self, feed: str) -> str:
        """Return the rss xml for a given feed."""
        return self.podcast_xml[feed]

    def make_about_page(self) -> None:
        """Create about page if needed."""
        about_page_desired_path = os.path.join(self.web_root, "about.html")

        if os.path.exists(about_page_desired_path):  # Check if about.html exists, affects index.html so it's first.
            with open(about_page_desired_path, encoding="utf-8") as about_page:
                self.about_page = about_page.read()

            logger.info("About page exists!")
        else:
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
                emoji = "❌"
                err = emoji + " You do not have permission to create folder: " + folder
                logger.exception(
                    "%s Run this this script as a different user probably, or check permissions of the web_root.",
                    emoji,
                )
                raise PermissionError(err) from exc

    def load_s3(self) -> None:
        """Function to get a s3 credential if one is needed."""
        if self.app_settings["storage_backend"] == "s3":
            # This is specifically for pytest, as moto doesn't support the endpoint_url
            api_url = None
            if self.app_settings["s3"]["api_url"] != "":
                api_url = self.app_settings["s3"]["api_url"]

            self.s3 = boto3.client(
                "s3",
                endpoint_url=api_url,
                aws_access_key_id=self.app_settings["s3"]["access_key_id"],
                aws_secret_access_key=self.app_settings["s3"]["secret_access_key"],
            )
            logger.info(f"⛅ Authenticated s3, using bucket: {self.app_settings['s3']['bucket']}")
            self.check_s3_files()
        else:
            logger.info("⛅ Not using s3")

    def check_s3_files(self) -> None:
        """Function to list files in s3 bucket."""
        logger.info("⛅ Checking state of s3 bucket")
        if not self.s3:
            logger.warning("⛅ No s3 client to list files")
            return
        response = self.s3.list_objects_v2(Bucket=self.app_settings["s3"]["bucket"])

        contents_str = ""
        if "Contents" in response:
            for obj in response["Contents"]:
                contents_str += obj["Key"] + "\n"
                if obj["Key"].startswith("/"):
                    logger.warning("⛅ S3 Path starts with a /, this is not expected: %s DELETING", obj["Key"])
                    self.s3.delete_object(Bucket=self.app_settings["s3"]["bucket"], Key=obj["Key"])
                if "//" in obj["Key"]:
                    logger.warning("⛅ S3 Path contains a //, this is not expected: %s DELETING", obj["Key"])
                    self.s3.delete_object(Bucket=self.app_settings["s3"]["bucket"], Key=obj["Key"])
            logger.debug("⛅ S3 Bucket Contents >>>\n%s", contents_str.strip())
        else:
            logger.info("⛅ No objects found in the bucket.")

    def grab_podcasts(self) -> None:
        """Loop through defined podcasts, download and store the xml."""
        for podcast in self.podcast_list:
            tree = None
            previous_feed = ""
            logger.info("📜 Processing settings entry: %s", podcast["new_name"])

            with contextlib.suppress(KeyError):  # Set the previous feed var if it exists
                previous_feed = self.podcast_xml[podcast["name_one_word"]]

            rss_file_path = os.path.join(self.web_root, "rss", podcast["name_one_word"])

            if podcast["live"] is True:  # download all the podcasts
                tree = self.podcast_downloader.download_podcast(podcast)
                if tree:
                    try:
                        # Write xml to disk
                        tree.write(
                            rss_file_path,
                            encoding="utf-8",
                            xml_declaration=True,
                        )
                        logger.debug("Wrote rss to disk: %s", rss_file_path)

                    except Exception:  # pylint: disable=broad-exception-caught
                        emoji = "❌"  # un-upset black
                        logger.exception(
                            "%s RSS XML Download Failure, attempting to host cached version",
                            emoji,
                        )
                        tree = None
                else:
                    logger.error("❌ Unable to download podcast, something is wrong")
            else:
                logger.info('📄 "live": false, in settings so not fetching new episodes')

            # Serving a podcast that we can't currently download?, load it from file
            if tree is None:
                logger.info("📄 Loading rss from file: %s", rss_file_path)
                try:
                    tree = etree.parse(rss_file_path)
                except FileNotFoundError:
                    logger.exception("❌ Cannot find rss xml file: %s", rss_file_path)

            if tree is not None:
                self.podcast_xml.update(
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
                    f"📄 Hosted: {self.app_settings['inet_path']}rss/{ podcast['name_one_word'] }",
                )

                # Upload to s3 if we are in s3 mode
                if (
                    self.s3
                    and previous_feed
                    != self.podcast_xml[
                        podcast["name_one_word"]
                    ]  # This doesn't work when feed has build dates times on it, patreon for one
                ):
                    try:
                        # Upload the file
                        self.s3.put_object(
                            Body=self.podcast_xml[podcast["name_one_word"]],
                            Bucket=self.app_settings["s3"]["bucket"],
                            Key="rss/" + podcast["name_one_word"],
                            ContentType="application/rss+xml",
                        )
                        logger.info('📄⛅ Uploaded feed "%s" to s3', podcast["name_one_word"])
                    except Exception:  # pylint: disable=broad-exception-caught
                        logger.exception("⛅❌ Unhandled s3 error trying to upload the file: %s")

            else:
                logger.error("❌ Unable to host podcast, something is wrong")

    def upload_static(self) -> None:
        """Function to upload static to s3 and copy index.html."""
        threading.Thread(target=self._upload_static, daemon=True).start()

    def _upload_static(self) -> None:
        """Actual function to upload static to s3 and copy index.html."""
        if not self.s3:
            return

        logger = get_logger(__name__ + ".upload_static")

        # TODO: Use self.web_root
        instance_web_directory = os.path.join(self.instance_path, "web")
        static_directory = os.path.join("archivepodcast", "static")

        # Render backup of html
        env = Environment(loader=FileSystemLoader(os.path.join(os.getcwd())), autoescape=True)
        template_directory = os.path.join("archivepodcast", "templates")
        templates_to_render = [
            os.path.join(root, file) for root, __, files in os.walk(template_directory) for file in files
        ]

        for template_filename in templates_to_render:
            output_filename = os.path.basename(template_filename).replace(".j2", "")
            output_path = os.path.join(instance_web_directory, output_filename)
            logger.debug("Rendering template: %s to %s", template_filename, output_path)
            template = env.get_template(os.path.join(template_filename))
            rendered_output = template.render(
                settings=self.app_settings, podcasts=self.podcast_list, about_page=self.about_page
            )

            with open(output_path, "w", encoding="utf-8") as root_web_page:
                root_web_page.write(rendered_output)

        if self.app_settings["storage_backend"] == "s3":
            logger.info("⛅ Uploading static pages to s3 in the background")
            try:
                static_items_to_copy = [
                    os.path.join(root, file) for root, __, files in os.walk(static_directory) for file in files
                ]

                for item in static_items_to_copy:
                    static_item_s3_path = "static" + item.replace(os.sep, "/").replace(static_directory, "")
                    logger.debug("⛅ Uploading static item: %s to s3: %s", item, static_item_s3_path)
                    self.s3.upload_file(
                        item,
                        self.app_settings["s3"]["bucket"],
                        static_item_s3_path,
                    )

                rendered_templates_to_copy = [
                    os.path.join(instance_web_directory, file)
                    for file in os.listdir(instance_web_directory)
                    if file.endswith(".html")
                ]

                for item in rendered_templates_to_copy:
                    item_s3_path = os.path.basename(item)
                    logger.debug("⛅ Uploading rendered template: %s to s3: %s", item, item_s3_path)
                    self.s3.upload_file(
                        item,
                        self.app_settings["s3"]["bucket"],
                        item_s3_path,
                    )

                self.s3.put_object(
                    Body="User-Agent: *\nDisallow: /\n",
                    Bucket=self.app_settings["s3"]["bucket"],
                    Key="robots.txt",
                    ContentType="text/plain",
                )

                logger.info("⛅ Done uploading static pages to s3")
            except Exception:
                logger.exception("⛅❌ Unhandled s3 error when trying to upload static files")
