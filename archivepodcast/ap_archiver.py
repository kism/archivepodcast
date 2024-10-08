"""Module to handle the ArchivePodcast object."""

import contextlib
import os
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

import boto3
from flask import current_app
from jinja2 import Environment, FileSystemLoader

from .ap_downloader import PodcastDownloader
from .logger import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

logger = get_logger(__name__)


class PodcastArchiver:
    """ArchivePodcast object."""

    def __init__(self, app_settings: dict, podcasts: list) -> None:
        """Initialise the ArchivePodcast object."""
        self.podcast_xml: dict[str, str] = {}
        self.s3: S3Client | None = None
        self.about_page: str | None = None




    def load_settings(self, app_settings: dict, podcasts: list) -> None:
        """Load the settings from the settings file."""
        self.settings = app_settings
        self.podcasts = podcasts
        self.load_s3()
        self.podcast_downloader = PodcastDownloader(app_settings=app_settings, s3=self.s3)
        self.make_about_page()
        self.make_folder_structure()
        self.upload_static()

    def get_rss_xml(self, feed: str) -> str:
        """Return the rss xml for a given feed."""
        return self.podcast_xml[feed]

    def make_about_page(self) -> None:
        """Create about page if needed."""
        about_page_desired_path = os.path.join(current_app.instance_path, "about.html")

        if os.path.exists(about_page_desired_path):  # Check if about.html exists, affects index.html so it's first.
            with open(about_page_desired_path, encoding="utf-8") as about_page:
                self.about_page = about_page.read()

            logger.debug("About page exists!")

    def make_folder_structure(self) -> None:
        """Ensure that web_root folder structure exists."""
        logger.debug("Checking folder structure")

        folders = []

        folders.append(current_app.instance_path)
        folders.append(os.path.join(current_app.instance_path, "rss"))
        folders.append(os.path.join(current_app.instance_path, "content"))

        folders.extend(
            os.path.join(current_app.instance_path, "content", entry["name_one_word"])
            for entry in self.settings["podcast"]
        )

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
        if self.settings["storage_backend"] == "s3":
            self.s3 = boto3.client(
                "s3",
                endpoint_url=self.settings["s3"]["api_url"],
                aws_access_key_id=self.settings["s3"]["access_key_id"],
                aws_secret_access_key=self.settings["s3"]["secret_access_key"],
            )
            logger.info("⛅ Authenticated s3")
        else:
            logger.info("⛅ Not using s3")

    def grab_podcasts(self) -> None:
        """Loop through defined podcasts, download and store the xml."""
        for podcast in self.podcasts:
            tree = None
            previous_feed = ""
            logger.info("📜 Processing settings entry: %s", podcast["new_name"])

            with contextlib.suppress(KeyError):  # Set the previous feed var if it exists
                previous_feed = self.podcast_xml[podcast["name_one_word"]]

            rss_file_path = os.path.join(current_app.instance_path, "rss", podcast["name_one_word"])

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
                    tree = ET.parse(rss_file_path)
                except FileNotFoundError:
                    logger.exception("❌ Cannot find rss xml file: %s", rss_file_path)

            if tree is not None:
                self.podcast_xml.update(
                    {
                        podcast["name_one_word"]: ET.tostring(
                            tree.getroot(),
                            encoding="utf-8",
                            method="xml",
                            xml_declaration=True,
                        )
                    }
                )
                logger.info(
                    f"📄 Hosted: {self.settings['inet_path']}rss/{ podcast['name_one_word'] }",
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
                            Bucket=self.settings["s3"]["bucket"],
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
        if not self.s3:
            return

        # Render backup of html
        env = Environment(loader=FileSystemLoader("."), autoescape=True)
        template = env.get_template("templates/home.j2")
        rendered_output = template.render(settings=self.settings, about_page=self.about_page)

        with open(self.settings["web_root"] + os.sep + "index.html", "w", encoding="utf-8") as root_web_page:
            root_web_page.write(rendered_output)

        if self.settings["storage_backend"] == "s3":
            logger.info("⛅ Uploading static pages to s3 in the background")
            try:
                for item in [
                    "/clipboard.js",
                    "/favicon.ico",
                    "/podcasto.css",
                    "/fonts/fira-code-v12-latin-600.woff2",
                    "/fonts/fira-code-v12-latin-700.woff2",
                    "/fonts/noto-sans-display-v10-latin-500.woff2",
                ]:
                    self.s3.upload_file("static" + item, self.settings["s3"]["bucket"], "static" + item)

                if self.about_page:
                    self.s3.upload_file(
                        self.settings["web_root"] + os.sep + "about.html",
                        self.settings["s3"]["bucket"],
                        "about.html",
                    )

                self.s3.put_object(
                    Body=rendered_output,
                    Bucket=self.settings["s3"]["bucket"],
                    Key="index.html",
                    ContentType="text/html",
                )

                self.s3.put_object(
                    Body="User-Agent: *\nDisallow: /\n",
                    Bucket=self.settings["s3"]["bucket"],
                    Key="robots.txt",
                    ContentType="text/plain",
                )

                logger.info("⛅ Done uploading static pages to s3")
            except Exception:
                logger.exception("⛅❌ Unhandled s3 Error")
