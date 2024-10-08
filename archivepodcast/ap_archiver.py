"""Module to handle the ArchivePodcast object."""

import contextlib
import os
import xml.etree.ElementTree as ET

import boto3
from flask import current_app

from .logger import get_logger

logger = get_logger(__name__)


class PodcastArchiver:
    """ArchivePodcast object."""

    def __init__(self, app_settings: dict) -> None:
        """Initialise the ArchivePodcast object."""
        self.podcast_xml: dict[str, str] = {}
        self.load_settings(app_settings)
        self.get_s3_credential()

    def load_settings(self, app_settings: dict) -> None:
        """Load the settings from the settings file."""
        self.settings = app_settings

    def get_s3_credential(self) -> None:
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
            self.s3 = None
            logger.info("📦 Not using s3")

    def grab_podcasts(self) -> None:
        """Loop through defined podcasts, download and store the xml."""
        for podcast in self.settings["podcast"]:
            tree = None
            previous_feed = ""
            logger.info("📜 Processing settings entry: %s", podcast["new_name"])

            with contextlib.suppress(KeyError):  # Set the previous feed var if it exists
                previous_feed = self.podcast_xml[podcast["name_one_word"]]

            rss_file_path = os.path.join(current_app.instance_path, "rss", podcast["name_one_word"])

            if podcast["live"] is True:  # download all the podcasts
                try:
                    tree = download_podcasts(podcast, self.settings, self.s3)
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
